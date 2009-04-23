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
Basic OSM objects.
"""

__version__ = "$Revision: 11 $"

class OSM_Node(object):
    def __init__(self, element):
        self.id = element.attrib["id"]
        self.version = element.attrib.get("version")
        self.changeset = element.attrib.get("changeset")
        self.lon = float(element.attrib["lon"])
        self.lat = float(element.attrib["lat"])
        self.tags = {}
        for sub in element:
            if sub.tag == 'tag':
                key = sub.attrib["k"]
                value = sub.attrib["v"]
                self.tags[key] = value
        self.name = self.tags.get("name")
       
class OSM_Way(object):
    def __init__(self, element):
        self.id = element.attrib["id"]
        self.version = element.attrib.get("version")
        self.changeset = element.attrib.get("changeset")
        self.tags = {}
        self.node_ids = []
        self.complete = False
        for sub in element:
            if sub.tag == 'tag':
                key = sub.attrib["k"]
                value = sub.attrib["v"]
                self.tags[key] = value
            if sub.tag == 'nd':
                node_id = sub.attrib["ref"]
                self.node_ids.append(node_id)
        self.nodes = [None] * len(self.node_ids)
        self.name = self.tags.get("name")

    def add_nodes(self, nodes):
        if not hasattr(nodes, "__getitem__"):
            nodes = dict( [(n.id, n) for n in nodes] )
        complete = True
        for i in range(0, len(self.node_ids)):
            node = nodes.get(self.node_ids[i])
            if node:
                self.nodes[i] = node
            elif not self.nodes[i]:
                complete = False
        self.complete = complete

    @property
    def start_node(self):
        return self.nodes[0]

    @property
    def end_node(self):
        return self.nodes[-1]

