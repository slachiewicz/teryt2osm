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
Czyta plik data/raw_data.osm i filtruje zapisując do data/data.osm tylko
węzły mogące leżeć w Polsce.
"""

__version__ = "$Revision$"

import subprocess
import sys

import locale,codecs
locale.setlocale(locale.LC_ALL, "")
encoding = locale.getlocale()[1]
if not encoding:
    encoding = "us-ascii"
sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")


import xml.etree.cElementTree as ElementTree

# fast node count
popen = subprocess.Popen(["grep", "-c", "<node", "data/raw_data.osm"],
                                            stdout=subprocess.PIPE)
(stdout, stderr) = popen.communicate()
node_count = int(stdout.strip())
step = node_count / 100

print >>sys.stderr, "Loading data/raw_data.osm"
tree = ElementTree.parse("data/raw_data.osm")

print >>sys.stderr, "Filtering..."
root = tree.getroot()
i = 0
# use list instead of iterator, so there is not problem with removing items
for element in list(root):  
    if element.tag != 'node':
        print >>sys.stderr, "Removing %r element"  % (element.tag,)
        root.remove(element)
    else:
        remove = False
        name = "unknown"
        id = element.attrib["id"]
        for tag in element:
            if tag.tag != 'tag':
                continue
            key = tag.attrib["k"]
            value = tag.attrib["v"]
            if id == "240033907":
                print >>sys.stderr, "Key: %r, Value: %r" % (key, value)
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
            root.remove(element)
    i += 1
    if i % step == 0:
        print >>sys.stderr, "%f%%" % (i * 100 / node_count)

tree.write("data/data.osm")
