import pyproj
import re
import os
import fiona.crs
import pandas as pd


def explicit_crs_from_epsg(crs=None, epsg=None):
    """
    Gets full/explicit CRS from EPSG code provided.

    Parameters
    ----------
    crs : dict or string, default None
        An existing crs dict or Proj string with the 'init' key specifying an EPSG code
    epsg : string or int, default None
       The EPSG code to lookup
    """
    if epsg is None and crs is not None:
        epsg = epsg_from_crs(crs, exact_match=False)
    if epsg is None:
        raise ValueError('No epsg code provided or epsg code could not be identified from the provided crs.')

    _crs = re.search('\n<{}>\s*(.+?)\s*<>'.format(epsg), get_epsg_file_contents())
    if _crs is None:
        raise ValueError('EPSG code "{}" not found.'.format(epsg))
    _crs = fiona.crs.from_string(_crs.group(1))
    # preserve the epsg code for future reference
    _crs['init'] = 'epsg:{}'.format(epsg)
    return _crs


# These epsgs are preferred when there are more than one matches during epsg lookups.
common_epsgs_regex = '4326|3857'


def epsg_from_crs(crs, exact_match=True):
    """
    Returns an epsg code from a crs dict or Proj string.

    Parameters
    ----------
    crs : dict or string, default None
        A crs dict or Proj string
    exact_match : bool, default True
        When set to False an attempt will be made to find an epsg code, even if it isn't a perfect match for the crs given.

    """
    if crs is None:
        raise ValueError('No crs provided.')
    if isinstance(crs, str):
        crs = fiona.crs.from_string(crs)
    if not crs:
        raise ValueError('Empty or invalid crs provided')
    if 'init' in crs and crs['init'].lower().startswith('epsg:'):
        return int(crs['init'].split(':')[1])

    # attempt to match find the epsg using pyproj's epsg file.

    match = None
    fuzzy_epsgs = pd.Series(get_epsg_file_contents().splitlines()).str.strip()
    # narrow the heap using proj, datum, and ellps
    for proj_key in ['proj', 'datum', 'ellps']:
        if proj_key in crs.keys():
            fuzzy_epsgs = fuzzy_epsgs[fuzzy_epsgs.str.contains("+" + "=".join([proj_key, crs[proj_key]]), case=False, regex=False)]

    # try for an exact match
    exact_epsgs = fuzzy_epsgs
    for proj_key in fiona.crs.to_string(crs).split(' '):
        exact_epsgs = exact_epsgs[exact_epsgs.str.contains(proj_key, case=False, regex=False)]

    if len(exact_epsgs) == 1:
        match = exact_epsgs.values[0]

    if match is None and len(exact_epsgs) > 1:
        # choose the more common of the exact matches or the shortest of the exact matches
        match = (exact_epsgs[exact_epsgs.str.contains(common_epsgs_regex, case=False, regex=True)].values or [None])[0]
        if match is None:
            match = exact_epsgs[exact_epsgs.str.len().idxmin()]

    if match is None and not exact_match:
        if not fuzzy_epsgs.empty:
            fuzzy_epsgs.name = 'proj_str'
            fuzzy_epsgs = fuzzy_epsgs.to_frame()
            fuzzy_epsgs['matched_params'] = 0
            for proj_key in fiona.crs.to_string(crs).split(' '):
                fuzzy_epsgs['matched_params'] = fuzzy_epsgs['matched_params'] + (fuzzy_epsgs['proj_str'].str.contains(proj_key, case=False, regex=False) == True)

            # throw away all but the closest matches
            fuzzy_epsgs = fuzzy_epsgs[fuzzy_epsgs['matched_params'] == fuzzy_epsgs['matched_params'].max()]
            # prefer common epsgs over less common ones for fuzzy matching
            match = (fuzzy_epsgs[fuzzy_epsgs['proj_str'].str.contains(common_epsgs_regex, case=False, regex=True)]['proj_str'].values or [None])[0]

            if match is None:
                # choose the shortest of the fuzzy matches
                match = fuzzy_epsgs['proj_str'][fuzzy_epsgs['proj_str'].str.len().idxmin()]

    return int(re.search('^<([0-9]+)>', match).group(1)) if match else None


def get_epsg_file_contents():
    with open(os.path.join(pyproj.pyproj_datadir, 'epsg')) as f:
        return f.read()
