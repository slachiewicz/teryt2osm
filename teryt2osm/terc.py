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



"""Handling of the TERC catalog."""

__version__ = "$Revision$"

import os
import xml.etree.cElementTree as ElementTree
from teryt2osm.utils import add_to_list_dict, count_elements
from teryt2osm.reporting import Reporting

def parse_terc(value, level = "gmina"):
    """Parse TERC or TERC10 code. Level is the administrative unit level 'gmi',
    'pow' or 'woj'.
    Both input and output are strings.
    
    Return normalized TERC code."""
    # remove separators
    value = "".join([c for c in "11-22-33" if c.isdigit()])
    if level == "gmi":
        if len(value) == 10:
            # TERC10
            return value[1:3] + value[5:]
        elif len(value) == 7:
            return value
        else:
            raise ValueError, "Bad TERC code"
    elif level == "pow":
        if len(value) == 7:
            # TERC10
            return value[1:3] + value[5:]
        elif len(value) == 4:
            return value
        else:
            raise ValueError, "Bad TERC code"
    elif level == "woj":
        if len(value) == 7:
            # TERC10
            return value[1:3] + value[5:]
        elif len(value) == 4:
            return value
        else:
            raise ValueError, "Bad TERC code"
    else:
        raise ValueError, "Bad level value"

class TERCObject(object):
    _by_code = {}
    name = ""
    woj_code = ""
    pow_code = ""
    gmi_code = ""
    gmi_type = ""
    def register(self):
        self.__class__._by_code[self.code] = self
        TERCObject._by_code[self.code] = self
    @classmethod
    def all(cls):
        return cls._by_code.values()
    @classmethod
    def count(cls):
        return len(cls._by_code)
    @classmethod
    def by_code(cls, code):
        return cls._by_code[code]
    @classmethod
    def by_name(cls, name, try_hard = False, wojewodztwo = None, powiat = None):
        raise NotImplementedError, "Not implemented"
    @classmethod
    def try_by_name(cls, name, try_hard = False, wojewodztwo = None, powiat = None):
        try:
            if powiat:
                return cls.by_name(name, try_hard, wojewodztwo, powiat)
            elif wojewodztwo:
                return cls.by_name(name, try_hard, wojewodztwo)
            else:
                return cls.by_name(name, try_hard)
        except KeyError:
            return None
        except ValueError, err:
            Reporting().output_msg("errors", err)
            return None

class Wojewodztwo(TERCObject):
    _by_code = {}
    _by_name = {}
    def __init__(self, name, woj_code, date):
        self.name = name
        self.date = date
        self.woj_code = woj_code
        self.code = woj_code
        Wojewodztwo._by_name[name] = self
        self.register()

    def full_name(self):
        return u"województwo " + self.name

    @classmethod
    def by_name(cls, name, try_hard = False):
        name = name.lower()
        if name.startswith(u"woj. ") or name.startswith(u"województwo ") or name.startswith(u"wojewodztwo "):
            name = name.split(None, 1)[1]
        elif not try_hard:
            raise KeyError, name
        if name in cls._by_name:
            return cls._by_name[name]

class Powiat(TERCObject):
    _by_code = {}
    _by_name = {}
    def __init__(self, name, woj_code, pow_code, date):
        self.name = name
        self.date = date
        self.woj_code = woj_code
        self.pow_code = pow_code
        self.code = woj_code + pow_code
        self.register()
        add_to_list_dict(self._by_name, name.lower(), self)

    @property
    def wojewodztwo(self):
        woj = Wojewodztwo._by_code[self.woj_code]
        self.__dict__['wojewodztwo'] = woj
        return woj

    def full_name(self):
        if self.name[0].isupper():
            return u"powiat m. " + self.name
        else:
            return u"powiat " + self.name
        
    def is_city(self):
        return self.name[0].isupper()

    def __repr__(self):
        return "<Powiat %r>" % (self.full_name(),)

    @classmethod
    def by_name(cls, name, try_hard = False, wojewodztwo = None):
        name = name.lower()
        if name.startswith(u"pow. ") or name.startswith(u"powiat ") or name.startswith(u"p. "):
            name = name.split(None, 1)[1]
        elif not try_hard:
            raise KeyError, name
        all = cls._by_name[name]
        if len(all) == 1:
            return all[0]
        if wojewodztwo:
            for pow in all:
                if pow.wojewodztwo is wojewodztwo:
                    return pow
            raise KeyError, name
        raise ValueError, u"Niejednoznaczna nazwa powiatu: %r" % (name,)

class Gmina(TERCObject):
    _by_code = {}
    def __init__(self, name, woj_code, pow_code, gmi_code, gmi_type, date):
        self.name = name
        self.date = date
        self.woj_code = woj_code
        self.pow_code = pow_code
        self.gmi_code = gmi_code
        self.gmi_type = gmi_type
        self.code = woj_code + pow_code + gmi_code + gmi_type
        self.register()
    @property
    def wojewodztwo(self):
        woj = Wojewodztwo._by_code[self.woj_code]
        self.__dict__['wojewodztwo'] = woj
        return woj
    @property
    def powiat(self):
        pow = Powiat._by_code[self.woj_code + self.pow_code]
        self.__dict__['powiat'] = pow
        return pow

def load_terc_object(element):
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
        elif key == "RODZ":
            gmi_type = child.text
        elif key == "NAZWA":
            name = child.text
        elif key == "STAN_NA":
            date = child.text
    if gmi_type:
        return Gmina(name, woj_code, pow_code, gmi_code, gmi_type, date)
    elif pow_code:
        if name.lower().startswith(u"powiat m. "):
            name = name[10:]
        elif name.lower().startswith(u"powiat "):
            name = name[7:]
        return Powiat(name, woj_code, pow_code, date)
    else:
        name = name.lower()
        if name.startswith(u"woj. "):
            name = name[5:].lower()
        elif name.startswith(u"województwo "):
            name = name[12:].lower()
        return Wojewodztwo(name, woj_code, date)

def load_terc():
    reporting = Reporting()
    row_count = count_elements("data/TERC.xml", "row")
    reporting.progress_start(u"Ładowanie data/TERC.xml", row_count)
    for event, elem in ElementTree.iterparse("data/TERC.xml"):
        if event == 'end' and elem.tag == 'row':
            load_terc_object(elem)
            reporting.progress()
    reporting.progress_stop()
    reporting.output_msg("stats", u"Załadowano %i województw, %i powiatów i %i gmin" % (
            Wojewodztwo.count(), Powiat.count(), Gmina.count()))

def write_wojewodztwa_wiki():
    import locale, codecs
    encoding = locale.getlocale()[1]
    if not encoding:
        encoding = "utf-8"
    if not os.path.exists("output"):
        os.mkdir("output")
    wiki_file = codecs.open("output/wojewodztwa.wiki", "w", encoding)
    wojewodztwa = Wojewodztwo.all()
    wojewodztwa = [(w.code, w) for w in wojewodztwa]
    wojewodztwa.sort()
    print >> wiki_file, u'{| class="wikitable" border="1" cellspacing="0" cellpadding="4"'
    print >> wiki_file, u'! Kod TERYT\n! Nazwa\n! Kompletność\n! Relacja\n! Uwagi'''
    for code, woj in wojewodztwa:
        print >> wiki_file, u"|-"
        print >> wiki_file, u"|", code
        print >> wiki_file, u"|", woj.name 
        print >> wiki_file, u"| "
        print >> wiki_file, u"| "
        print >> wiki_file, u"| "
    print >> wiki_file, u"|}"
    wiki_file.close()
