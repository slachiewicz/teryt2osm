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

"""Utility functions for the teryt2osm project."""

__version__ = "$Revision$"

import subprocess
import sys

def setup_locale():
    """Set up locale and sys.stdout, sys.stderr streams so Unicode output will
    be handled correctly."""
    import locale,codecs
    locale.setlocale(locale.LC_ALL, "")
    encoding = locale.getlocale()[1]
    if not encoding:
        encoding = "us-ascii"
    sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
    sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")

def add_to_list_dict(dictionary, key, value):
    """Add a value to a dictionary keeping list of values for a key.
    Create the list if it doesn't exist yet."""
    if key in dictionary:
        dictionary[key].append(value)
    else:
        dictionary[key] = [value]

def count_elements(filename, tag):
    """Simple hack to quickly count elements in a XML file."""
    popen = subprocess.Popen(["grep", "-c", "<" + tag, filename],
                                                stdout=subprocess.PIPE)
    (stdout, stderr) = popen.communicate()
    tag_count = int(stdout.strip())
    return tag_count

