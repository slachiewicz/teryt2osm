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


__version__ = "$Revision$"

import os
import xml.etree.cElementTree as ElementTree
from teryt2osm.utils import add_to_list_dict, count_elements
from teryt2osm.terc import Wojewodztwo, Powiat, Gmina, load_terc
from teryt2osm.reporting import Reporting

simc2place_mapping = {
        u"wieś": "village",
        u"miasto": "city",
        u"dzielnica m.st. Warszawy": "suburb",
        u"część miasta": "suburb"
        }

place_aliases = {
        "hamlet": "village",
        "town": "city",
        }

wmrodz = {}
rm2place_mapping = {}

def load_wmrodz():
    reporting = Reporting()
    reporting.output_msg("info", u"Ładowanie data/WMRODZ.xml")
    tree = ElementTree.parse("data/WMRODZ.xml")
    root = tree.getroot()
    catalog = tree.find("catalog")
    for row in catalog:
        if row.tag != "row":
            continue
        rm = None
        nazwa = None
        for col in row:
            if col.tag != 'col':
                continue
            key = col.attrib["name"]
            if key == "RM":
                rm = col.text
            elif key == "NAZWA_RM":
                nazwa = col.text.strip()
        if rm and nazwa:
            wmrodz[rm] = nazwa
            if nazwa in simc2place_mapping:
                rm2place_mapping[rm] = simc2place_mapping[nazwa]

def write_wmrodz_wiki():
    import locale, codecs
    encoding = locale.getlocale()[1]
    if not encoding:
        encoding = "utf-8"
    if not os.path.exists("output"):
        os.mkdir("output")
    wiki_file = codecs.open("output/wmrodz.wiki", "w", encoding)
    keys = list(wmrodz.keys())
    keys.sort()
    print >> wiki_file, u'{| class="wikitable"'
    print >> wiki_file, u'! kod RM || nazwa TERYT || tag OSM || uwagi'
    for rm in keys:
        print >> wiki_file, u"|-"
        if rm in rm2place_mapping:
            print >> wiki_file, u"| %s || %s || {{Tag|place|%s}} ||" % (rm, wmrodz[rm], rm2place_mapping[rm])
        else:
            print >> wiki_file, u"| %s || %s || ||" % (rm, wmrodz[rm])
    print >> wiki_file, u"|}"
    wiki_file.close()

class SIMC_Place(object):
    _by_id = {}
    _by_type = {}
    _by_name = {}
    def __init__(self, rm, name, terc_id, place_id, parent_id, date):
        self.rm = rm
        place_type = rm2place_mapping[rm]
        self.type = place_type
        self.name = name
        self.terc_id = terc_id
        self.gmina = Gmina.by_code(terc_id)
        self.powiat = self.gmina.powiat
        self.wojewodztwo = self.powiat.wojewodztwo
        self.id = place_id
        self.parent = None
        if parent_id and parent_id != place_id:
            self.parent_id = parent_id
        else:
            self.parent_id = None
        self.date = date
        self._by_id[place_id] = self
        add_to_list_dict(self._by_type, place_type, self)
        add_to_list_dict(self._by_name, name.lower(), self)
        self.osm_place = None

    @classmethod
    def by_id(cls, place_id):
        """Return single place identified by a SIMC id."""
        return cls._by_id[place_id]

    @classmethod
    def by_name(cls, name):
        """Return all places matching a name."""
        return cls._by_name[name.lower()]

    @classmethod
    def by_type(cls, place_type):
        """Return all places of given type."""
        return cls._by_type[place_type]

    @classmethod
    def link_parents(cls):
        for place in cls._by_id.values():
            if place.parent_id:
                place.parent = cls._by_id.get(place.parent_id)

    @classmethod
    def count(cls):
        return len(cls._by_id.items())

    @classmethod
    def from_element(cls, element):
        for child in element:
            if child.tag != 'col':
                continue
            key = child.attrib["name"]
            if key == "WOJ":
                woj_code = child.text
            elif key == "POW":
                pow_code = child.text
            elif key == "GMI":
                gmi_code = child.text
            elif key == "RODZ_GMI":
                gmi_type = child.text
            elif key == "RM":
                rm = child.text
            elif key == "MZ":
                mz = child.text
            elif key == "NAZWA":
                name = child.text
            elif key == "SYM":
                place_id = child.text
            elif key == "SYMPOD":
                parent_id = child.text
            elif key == "STAN_NA":
                date = child.text
        if rm not in rm2place_mapping:
            return None
        code = woj_code + pow_code + gmi_code + gmi_type
        return cls(rm, name, code, place_id, parent_id, date)
    
    def assign_osm(self, osm_place):
        """Assigning a OSM place"""
        self.osm_place = osm_place

    def __repr__(self):
        return "<SIMC_Place #%s %r>" % (self.id, self.name)
    def __unicode__(self):
        powiat = self.gmina.powiat
        wojewodztwo = self.gmina.wojewodztwo
        return u"%s, %s, %s, %s" % (self.name, self.gmina.name, 
                                    powiat.full_name(), wojewodztwo.full_name())

def load_simc():
    load_wmrodz()
    reporting = Reporting()
    row_count = count_elements("data/SIMC.xml", "row")
    reporting.progress_start(u"Ładowanie data/SIMC.xml", row_count)
    for event, elem in ElementTree.iterparse("data/SIMC.xml"):
        if event == 'end' and elem.tag == 'row':
            SIMC_Place.from_element(elem)
            reporting.progress()
    reporting.progress_stop()
    reporting.output_msg("stats", u"Załadowano %i miejscowości" % (SIMC_Place.count(),))
    SIMC_Place.link_parents()

