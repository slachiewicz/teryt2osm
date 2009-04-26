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
Split large osmChange files.
"""

__version__ = "$Revision: 21 $"

import os
import sys
import traceback
import codecs
import locale
import subprocess

import httplib

from teryt2osm.utils import setup_locale
import xml.etree.cElementTree as ElementTree

try:
    this_dir = os.path.dirname(__file__)
    version = subprocess.Popen(["svnversion", this_dir], stdout = subprocess.PIPE).communicate()[0].strip()
    setup_locale()
    if len(sys.argv) not in (2, 3):
        print >>sys.stderr, u"Sposób użycia:"
        print >>sys.stderr, u"    %s <nazwa_plku> [<ilość części>...]"
        sys.exit(1)

    filename = sys.argv[1]
    if len(sys.argv) > 2:
        num_parts = int(sys.argv[2])
    else:
        num_parts = 2
    if not os.path.exists(filename):
        print >>sys.stderr, u"Plik %r nie istnieje!" % (filename,)
        sys.exit(1)
    if filename.endswith(".osc"):
        filename_base = filename[:-4]
    else:
        filename_base = filename

    tree = ElementTree.parse(filename)
    root = tree.getroot()
    if root.tag != "osmChange" or root.attrib.get("version") != "0.3":
        print >>sys.stderr, u"Plik %s to nie osmChange w wersji 0.3!" % (filename,)
        sys.exit(1)

    element_count = 0
    for operation in root:
        element_count += len(operation)

    print >>sys.stderr, u"Ilość elementów: %r" % (element_count,)
    part_size = (element_count + num_parts - 1) / num_parts

    part = 1
    operation_iter = iter(root)
    operation = operation_iter.next()
    elements = list(operation)
    while elements and operation:
        filename = "%s-part%i.osc" % (filename_base, part)
        part_root = ElementTree.Element(root.tag, root.attrib)
        part_tree = ElementTree.ElementTree(part_root)
        current_size = 0
        while operation and current_size < part_size:
            part_op = ElementTree.SubElement(part_root, operation.tag, operation.attrib)
            this_part_elements = elements[:(part_size-current_size)]
            elements = elements[(part_size-current_size):]
            for element in this_part_elements:
                part_op.append(element)
                current_size += 1
            if not elements:
                try:
                    operation = operation_iter.next()
                    elements = list(operation)
                except StopIteration:
                    operation = None
                    elements = []
        part_tree.write(filename, "utf-8")
        part += 1
    comment_fn = filename_base+ ".comment"
    if os.path.exists(comment_fn):
        comment_file = codecs.open(comment_fn, "r", "utf-8")
        comment = comment_file.read().strip()
        comment_file.close()
        for part in range(1, num_parts + 1):
            comment_fn = "%s-part%i.comment" % (filename_base, part)
            comment_file = codecs.open(comment_fn, "w", "utf-8")
            print >> comment_file, u"%s, part %i/%i" % (comment, part, num_parts)
            comment_file.close()
except Exception,err:
    print >>sys.stderr, repr(err)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

