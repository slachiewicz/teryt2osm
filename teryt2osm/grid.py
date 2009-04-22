# vi: encoding=utf-8

# teryt2osm - tool to merge TERYT data with OSM maps
# Copyright (C) 2009 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


"""
Grid for optimized place matching.
"""

from teryt2osm.reporting import Reporting

__version__ = "$Revision: 2 $"


class Cell(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.wojewodztwa = set()
        self.powiaty = set()
        self.gminy = set()
    def add_place(self, place):
        self.wojewodztwa.add(place.wojewodztwo)
        self.powiaty.add(place.powiat)
        self.gminy.add(place.gmina)
    def __unicode__(self):
        return u"%ix%i (%i województw, %i powiatów, %i gmin)" % (
                        self.x, self.y, len(self.wojewodztwa),
                                len(self.powiaty), len(self.gminy))

class Grid(object):
    def __init__(self, places, width, height):
        self.width = width
        self.height = height
        reporting = Reporting()
        reporting.progress_start("Creating grid %ix%i" % (width, height),
                                                            len(places) * 2)
        left, right, top, bottom = 180, -180, -90, 90
        for p in places:
            reporting.progress()
            left = min(left, p.lon)
            right = max(right, p.lon)
            top = max(top, p.lat)
            bottom = min(bottom, p.lat)
        reporting.output_msg("info", "Bounding box: (%r,%r,%r,%r)" % (
                                            left, bottom, right, top))
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.lon_ratio = (right - left) * 1.01 / width
        self.lat_ratio = (top - bottom) * 1.01 / height
        reporting.output_msg("info", "lon_ratio: %r, lat_ratio: %r" % (
                                            self.lon_ratio, self.lat_ratio))
        self.cells = {}
        for x in range(0, width):
            for y in range(0, height):
                self.cells[(x,y)] = Cell(x,y)
        for place in places:
            reporting.progress()
            cell = self.get_cell(place)
            cell.add_place(place)
        reporting.progress_stop()

    def get_cell(self, place):
        x = int((place.lon - self.left) / self.lon_ratio)
        y = int((place.lat - self.bottom) / self.lat_ratio)
        return self.cells[(x, y)]

    def __unicode__(self):
        return u"%ix%i (%f, %f, %f, %f)" % (
                        self.width, self.height,
                        self.left, self.bottom, self.right, self.top)


