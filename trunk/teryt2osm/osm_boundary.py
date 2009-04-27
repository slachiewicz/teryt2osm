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
Handle OSM boundary relations.
"""

__version__ = "$Revision: 11 $"

import sys
import xml.etree.cElementTree as ElementTree
from teryt2osm.utils import add_to_list_dict, count_elements
from teryt2osm.terc import Wojewodztwo, Powiat, Gmina, load_terc
from teryt2osm.simc import SIMC_Place, place_aliases
from teryt2osm.reporting import Reporting
from teryt2osm.osm import OSM_Node, OSM_Way
        
try:
    from shapely.geometry import Point, MultiPolygon
    HAVE_SHAPELY=True
except ImportError:
    HAVE_SHAPELY=False

class OSM_Boundary(object):
    def __init__(self, relation_element, way_elements, node_elements):
        self.polygons = []
        self.ways = {}
        self.relation = relation_element
        self.open = True
        reporting = Reporting()
        self.id = relation_element.attrib["id"]
        self.version = relation_element.attrib["version"]
        self.changeset = relation_element.attrib["changeset"]
        self.tags = {}

        nodes = {}
        for element in node_elements:
            node = OSM_Node(element)
            nodes[node.id] = node

        ways = {}
        for element in way_elements:
            way = OSM_Way(element)
            way.add_nodes(nodes)
            ways[way.id] = way

        for sub in relation_element:
            if sub.tag == 'tag':
                key = sub.attrib["k"]
                value = sub.attrib["v"]
                self.tags[key] = value
            elif sub.tag == 'member' and sub.attrib["type"] == 'way':
                role = sub.attrib.get("role", "")
                if role:
                    raise NotImplementedError, "Role %r for relation way members not supported" % (role,)
                way_id = sub.attrib["ref"]
                way = ways.get(way_id)
                if way:
                    if not way.complete:
                        raise ValueError, "Incomplete way: %r" % (way,)
                    self.ways[way_id] = way
                else:
                    raise ValueError, "Way not found: %r" % (way_id,)

        self.name = self.tags.get("name")
        if not self.ways:
            raise ValueError, "No ways"
        
        self.open = False
        ways_left = self.ways.values()
        while ways_left:
            segment_start = ways_left.pop(0)
            polygon = []
            for node in segment_start.nodes:
                polygon.append((node.lat, node.lon))
            last_end = segment_start.end_node
            while ways_left:
                if last_end is segment_start.start_node:
                    # cycle ended
                    break
                next = None
                for way in ways_left:
                    if way.start_node is last_end:
                        last_end = way.end_node
                        for node in way.nodes[1:]:
                            polygon.append((node.lat, node.lon))
                        next = way
                        break
                    elif way.end_node is last_end:
                        last_end = way.start_node
                        rnodes = list(way.nodes[1:])
                        rnodes.reverse()
                        for node in rnodes:
                            polygon.append((node.lat, node.lon))
                        next = way
                        break
                if next:
                    ways_left.remove(next)
                else:
                    # open segment ends
                    self.open = True
                    break
            self.polygons.append(polygon)
        if HAVE_SHAPELY:
            reporting.output_msg("info", 
                    "Using Shapely for 'point in polygon' checks")
            self.multi_polygon = MultiPolygon([(p, ()) for p in self.polygons])
            self. _contains_impl = self._contains_shapely_impl
        else:
            reporting.output_msg("info", 
                "Using Python function for the 'point in polygon' checks")
            self. _contains_impl = self._contains_python_impl

    def __repr__(self):
        if self.open:
            open_s = "open"
        else:
            open_s = "closed"
        return "<OSM_Boundary #%s %r %s %i ways %i polygons>" % (self.id, 
                self.name, open_s, len(self.ways), len(self.polygons))

    def _contains_python_impl(self, location):
        lat = location.lat
        lon = location.lon
        for pol in self.polygons:
            contains = False
            plen = len(pol)
            i = 0
            j = plen - 1
            while i < plen:
                if ( ((pol[i][0] > lat) != (pol[j][0] > lat)) and 
                        (lon < ((pol[j][1] - pol[i][1]) * (lat - pol[i][0]) / (pol[j][0] - pol[i][0]) + pol[i][1])) ):
                    contains = not contains
                j = i
                i += 1
            if contains:
                return True
        return False
    
    def _contains_shapely_impl(self, location):
        point = Point(location.lat, location.lon)
        return self.multi_polygon.contains(point)
   
    def __contains__(self, location):
        if self.open:
            return True
        return self._contains_impl(location)
    
def load_osm_boundary(filename):
    """Loads a boundary relation from an OSM file. The file must also
    contain all the nodes and way used by the boundary. Only the first boundary
    is read."""
    reporting = Reporting()
    elem_count = count_elements(filename, "node")
    elem_count += count_elements(filename, "way")
    elem_count += 1
    reporting.progress_start(u"Ładuję %s" % (filename,), elem_count)
    nodes = []
    ways = []
    relation = None
    for event, elem in ElementTree.iterparse(filename):
        if event != 'end':
            continue
        if elem.tag == 'node':
            nodes.append(elem)
        elif elem.tag == 'way':
            ways.append(elem)
        elif elem.tag == 'relation' and not relation:
            relation = elem
        else:
            continue
        reporting.progress()
    reporting.progress_stop()
    if not relation:
        reproting.output_msg("errors", u"Nie znaleziono relacji")
        raise ValueError, "Relation not found"
    reporting.output_msg("stats", u"Załadowano relację, %i dróg i %i węzłów." 
                    % (len(ways), len(nodes)))
    boundary = OSM_Boundary(relation, ways, nodes)
    return boundary
