#!/usr/bin/python

from teryt2osm.osm_boundary import load_osm_boundary
from teryt2osm.utils import setup_locale

setup_locale()
boundary = load_osm_boundary("../data/boundary_poland.osm")
#boundary = load_osm_boundary("../data/boundary_simple.osm")
print repr(boundary)
#print repr(boundary.polygons)

class Location(object):
    def __init__(self, lat, lon):
        self.lat = float(lat)
        self.lon = float(lon)



for lat, lon in (0,0), (52.217, 21):
    loc = Location(lat, lon)
    print "(%f,%f) in %r: %r" % (lat,lon,boundary, loc in boundary)

