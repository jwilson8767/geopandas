from __future__ import absolute_import

from shapely.geometry import Point, MultiPoint, LineString

from geopandas import GeoSeries
from geopandas.tools import collect
from geopandas.tools.crs import explicit_crs_from_epsg, epsg_from_crs

import pytest


class TestTools:
    def setup_method(self):
        self.p1 = Point(0, 0)
        self.p2 = Point(1, 1)
        self.p3 = Point(2, 2)
        self.mpc = MultiPoint([self.p1, self.p2, self.p3])

        self.mp1 = MultiPoint([self.p1, self.p2])
        self.line1 = LineString([(3, 3), (4, 4)])

    def test_collect_single(self):
        result = collect(self.p1)
        assert self.p1.equals(result)

    def test_collect_single_force_multi(self):
        result = collect(self.p1, multi=True)
        expected = MultiPoint([self.p1])
        assert expected.equals(result)

    def test_collect_multi(self):
        result = collect(self.mp1)
        assert self.mp1.equals(result)

    def test_collect_multi_force_multi(self):
        result = collect(self.mp1)
        assert self.mp1.equals(result)

    def test_collect_list(self):
        result = collect([self.p1, self.p2, self.p3])
        assert self.mpc.equals(result)

    def test_collect_GeoSeries(self):
        s = GeoSeries([self.p1, self.p2, self.p3])
        result = collect(s)
        assert self.mpc.equals(result)

    def test_collect_mixed_types(self):
        with pytest.raises(ValueError):
            collect([self.p1, self.line1])

    def test_collect_mixed_multi(self):
        with pytest.raises(ValueError):
            collect([self.mpc, self.mp1])

    def test_epsg_from_crs(self):
        assert epsg_from_crs({'init': 'epsg:4326'}) == 4326
        assert epsg_from_crs({'init': 'EPSG:4326'}) == 4326
        assert epsg_from_crs('+init=epsg:4326') == 4326
        assert epsg_from_crs('+proj=longlat') == 4326
        assert epsg_from_crs('+proj=longlat +datum=NAD83 +no_defs') == 4269
        assert epsg_from_crs('+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m') == 3395
        assert epsg_from_crs('+proj=merc +datum=WGS84') == 3395
        assert epsg_from_crs('+proj=merc') == 3857
        assert epsg_from_crs('+proj=longlat')
        # test a case that requires fuzzy matching
        assert epsg_from_crs('+datum=WGS84 +proj=merc +towgs84=0,0,0,0,0,0,0 +units=us-ft', exact_match=True) is None
        # Note that this is also an example of where fuzzy matching can be wrong as it will change units from ft to m.
        assert epsg_from_crs('+datum=WGS84 +proj=merc +towgs84=0,0,0,0,0,0,0 +units=us-ft', exact_match=False) == 3395


    def test_explicit_crs_from_epsg(self):
        expected = {'no_defs': True, 'proj': 'longlat', 'datum': 'WGS84', 'init': 'epsg:4326'}
        # test basic cases looking up a single code
        assert explicit_crs_from_epsg(epsg=4326) == expected
        assert explicit_crs_from_epsg(epsg='4326') == expected
        assert explicit_crs_from_epsg(crs={'init': 'epsg:4326'}) == expected
        assert explicit_crs_from_epsg(crs="+init=epsg:4326") == expected
        # test a case where we start with less than a complete CRS and get a good guess at a full crs.
        assert explicit_crs_from_epsg(crs="+proj=merc +datum=WGS84") == {'init': 'epsg:3395', 'proj': 'merc', 'lon_0': 0, 'k': 1, 'x_0': 0, 'y_0': 0, 'datum': 'WGS84', 'units': 'm', 'no_defs': True}


