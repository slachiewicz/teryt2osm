#!/usr/bin/python
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
Reads data/raw_data.osm and retrieves ids of nodes witch may belong to Poland.
Current versions of these nodes are retrieved by the official API then
and writhundred to data/data.osm.
"""

__version__ = "$Revision$"

import subprocess
import sys
from teryt2osm.reporting import Reporting
from teryt2osm.utils import setup_locale, add_to_list_dict, count_elements
import xml.etree.cElementTree as ElementTree
from urllib import urlopen

setup_locale()
reporting = Reporting(logging = False)

# fast node count
node_count = count_elements("data/raw_data.osm", "node")
step = node_count / 100

reporting.output_msg("info", u"Ładuję data/raw_data.osm")
tree = ElementTree.parse("data/raw_data.osm")

reporting.progress_start(u"Filtruję...", node_count)
node_ids = []
root = tree.getroot()
i = 0
# use list instead of iterator, so there is not problem with removing items
for element in root:  
    if element.tag != 'node':
        print >>sys.stderr, "Removing %r element"  % (element.tag,)
    else:
        remove = False
        name = "unknown"
        id = element.attrib["id"]
        for tag in element:
            if tag.tag != 'tag':
                continue
            key = tag.attrib["k"]
            value = tag.attrib["v"]
            if key in ('is_in', 'is_in:country'):
                if "Poland" not in value and "Polska" not in value:
                    remove = True
                    print >>sys.stderr, "Poland not in %r" % (value,)
            elif key == 'is_in:country_code':
                if value.lower != 'pl':
                    remove = True
            elif key == "name":
                name = value
        if remove:
            print >>sys.stderr, "Removing:", name
        else:
            node_ids.append(str(id))
    reporting.progress()

reporting.progress_stop()

del root

node_ids.sort()

NODES_PER_REQUEST=256

reporting.progress_start(u"Pobieram aktualne wersje węzłów...", len(node_ids) / NODES_PER_REQUEST)
root = ElementTree.Element(u"osm", version = u"0.6", generator = u"teryt2osm/filter_osm.py")
tree = ElementTree.ElementTree(root)
for i in xrange(0, len(node_ids), NODES_PER_REQUEST):
    ids_set = node_ids[i:i+NODES_PER_REQUEST]
    try:
        data = urlopen('http://www.openstreetmap.org/api/0.6/nodes?nodes=' + ",".join(ids_set))
        response = ElementTree.parse(data)
        r_root = response.getroot()
        for element in r_root:
            root.append(element)
    except IOError, err:
        reporting.output_msg("info", u"Bulk download failed: %s" % (err,))
        for node_id in ids_set:
            try:
                data = urlopen('http://www.openstreetmap.org/api/0.6/node/' + node_id)
                response = ElementTree.parse(data)
                r_root = response.getroot()
                for element in r_root:
                    root.append(element)
            except IOError, err:
                reporting.output_msg("errors", u"Błąd I/O podczas pobierania węzła %s: %s" 
                                                    % (node_id, err))
    reporting.progress()
reporting.progress_stop()

tree.write("data/data.osm", "utf-8")
reporting.close()
