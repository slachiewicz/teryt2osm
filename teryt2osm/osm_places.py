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
Handle OSM places.
"""

__version__ = "$Revision$"

import sys
import xml.etree.cElementTree as ElementTree
from teryt2osm.utils import add_to_list_dict, count_elements
from teryt2osm.terc import Wojewodztwo, Powiat, Gmina, load_terc, parse_terc
from teryt2osm.simc import SIMC_Place, place_aliases, parse_simc
from teryt2osm.reporting import Reporting
from teryt2osm.osm import OSM_Node

class OSM_Place(OSM_Node):
    _by_id = {}
    _by_simc_id = {}
    _by_name = {}
    _by_type = {}
    woj_matched = 0
    pow_matched = 0
    gmi_matched = 0
    def __init__(self, element):
        OSM_Node.__init__(self, element)
        reporting = Reporting()

        self.element = element
        self.wojewodztwo = None
        self.powiat = None
        self.gmina = None
        self.simc_id = None
        self.terc_id = None
        self.simc_place = None
        tags = self.tags

        if "place" in tags:
            self.type = tags["place"]
        else:
            self.type = None

        self.normalized_type = place_aliases.get(self.type, self.type)

        if "is_in" in tags:
            is_in_parts = [s.strip() for s in tags["is_in"].split(",")]
            self.is_in = ", ".join(is_in_parts)
        else:
            is_in_parts = []
            self.is_in = None

        if "is_in:province" in tags:
            woj = tags["is_in:province"]
            self.wojewodztwo = Wojewodztwo.try_by_name(woj, True)
            OSM_Place.woj_matched += 1
        elif is_in_parts:
            for part in is_in_parts:
                woj = Wojewodztwo.try_by_name(part, False)
                if woj:
                    self.wojewodztwo = woj
                    OSM_Place.woj_matched += 1
                    break

        if self.wojewodztwo:
            reporting.output_msg("woj_set", u"%s (%s) jest w %s" % (self.name, 
                        self.id, self.wojewodztwo.full_name()), self)

        if "is_in:county" in tags:
            pow = tags["is_in:county"]
            self.powiat = Powiat.try_by_name(pow, True, self.wojewodztwo)
            OSM_Place.pow_matched += 1
        elif is_in_parts:
            for part in is_in_parts:
                pow = Powiat.try_by_name(part, False, self.wojewodztwo)
                if pow:
                    self.powiat = pow
                    OSM_Place.pow_matched += 1
                    break

        if self.powiat:
            reporting.output_msg("pow_set", u"%s jest w %s" % (self.name,
                            self.powiat.full_name()), self)
            if self.wojewodztwo:
                if self.powiat.wojewodztwo != self.wojewodztwo:
                    reporting.output_msg("errors", u"%s: Powiat nie pasuje do województwa"
                                                        % (self,))
            else:
                self.wojewodztwo = self.powiat.wojewodztwo

        if "is_in:municipality" in tags:
            gmi = tags["is_in:municipality"]
            self.gmina = Gmina.try_by_name(gmi, True,
                                powiat = self.powiat, place_name = self.name)
            OSM_Place.gmi_matched += 1
        elif is_in_parts:
            for part in is_in_parts:
                gmi = Gmina.try_by_name(part, False, 
                                powiat = self.powiat, place_name = self.name)
                if gmi:
                    self.gmi = gmi 
                    OSM_Place.gmi_matched += 1
                    break

        if self.gmina:
            reporting.output_msg("gmi_set", u"%s jest w %s" % (self.name,
                            self.gmina.full_name()), self)
            if self.powiat:
                if self.gmina.powiat != self.powiat:
                    reporting.output_msg("errors", u"%s: Gmina nie pasuje do powiatu"
                                                        % (self,))
                    self.gmina = None
            else:
                self.powiat = self.gmina.powiat

        if "teryt:simc" in tags:
            try:
                self.simc_id = tags["teryt:simc"]
            except ValueError:
                reporting.output_msg("errors", 
                        u"Nieprawidłowa wartość teryt:simc: %r" % (
                                                    tags["teryt:simc"],))
        
        if self.simc_id:
            try:
                self.simc_place = SIMC_Place.by_id(self.simc_id)
            except KeyError:
                reporting.output_msg("errors", 
                        u"wartość teryt:simc nie istnieje w bazie SIMC")
            if self.simc_id in self._by_simc_id:
                reporting.output_msg("errors", 
                    u"Powtórzony kod SIMC w danych OSM: %r (%r and %r)" % (
                    self.simc_id, self, self._by_simc_id[self.simc_id]), self)
            else:
                self._by_simc_id[self.simc_id] = self
       
        if self.simc_place:
            gmina = self.simc_place.gmina 
            if (self.gmina and gmina != self.gmina
                    or self.powiat and gmina.powiat != self.powiat
                    or self.wojewodztwo 
                            and gmina.wojewodztwo != self.wojewodztwo):
                reporting.output_msg("errors", 
                        u"%s: teryt:simc nie zgadza się z położeniem wynikającym z innych tagów"
                        u" (%r != %r | %r != %r | %r != %r)" 
                        % (self, self.gmina, gmina, self.powiat, gmina.powiat,
                            self.wojewodztwo, gmina.wojewodztwo))
            else:    
                self.gmina = self.simc_place.gmina
                self.powiat = self.simc_place.powiat
                self.wojewodztwo = self.simc_place.wojewodztwo
            reporting.output_msg("preassigned", 
                    u"%r ma już przypisany rekord SIMC: %r" 
                                % (self, self.simc_place), self)
        

        if "teryt:terc" in tags:
            try:
                self.terc_id = tags["teryt:terc"]
            except:
                reporting.output_msg("errors", u"Błędny kod teryt:terc: %r"
                                                    % (tags["teryt:terc"],))

        if self.terc_id:
            self.terc_id = tags["teryt:terc"]
            if self.simc_place and self.terc_id != self.simc_place.terc_id:
                reporting.output_msg("errors", u"teryt:terc nie zgadza się z teryt:simc")
            else:
                try:
                    gmina = Gmina.by_code(self.terc_id)
                    if (self.gmina and gmina != self.gmina
                            or self.powiat and gmina.powiat != self.powiat
                            or self.wojewodztwo 
                                and gmina.wojewodztwo != self.wojewodztwo):
                        reporting.output_msg("errors", 
                                u"%s: teryt:terc nie zgadza się"
                                u" z położeniem wynikającym z innych tagów"
                                u" (%r != %r | %r != %r | %r != %r)" 
                                % (self, self.gmina, gmina, self.powiat, gmina.powiat,
                                    self.wojewodztwo, gmina.wojewodztwo))
                    if gmina and not self.gmina:
                        self.gmina = gmina
                        self.powiat = gmina.powiat
                        self.wojewodztwo = gmina.wojewodztwo
                except KeyError:
                    pass
        self._by_id[self.id] = self
        if self.name:
            add_to_list_dict(self._by_name, self.name.lower(), self)
        add_to_list_dict(self._by_type, self.type, self)

    def assign_simc(self, simc_place):
        """Assigning a SIMC place"""
        self.simc_place = simc_place
        self.simc_id = simc_place.id
        self.terc_id = simc_place.terc_id
        self.gmina = simc_place.gmina
        self.powiat = simc_place.powiat
        self.wojewodztwo = simc_place.wojewodztwo

    def update(self):
        if not self.simc_place:
            return False
        reporting = Reporting()
        updated = []
        tags = self.tags
        if "teryt:simc" not in tags or tags['teryt:simc'] != self.simc_place.id:
            updated.append("teryt:simc")
            tags["teryt:simc"] = self.simc_place.id
        if "teryt:terc" not in tags or tags['teryt:terc'] != self.gmina.code:
            updated.append("teryt:terc")
            tags["teryt:terc"] = self.gmina.code
        if "teryt:rm" not in tags or tags['teryt:rm'] != self.simc_place.rm:
            updated.append("teryt:rm")
            tags["teryt:rm"] = self.simc_place.rm
        if "teryt:date" in tags:
            updated.append("teryt:date")
            del tags["teryt:date"]
        if "teryt:stan_na" not in tags or tags['teryt:stan_na'] != self.simc_place.date:
            updated.append("teryt:stan_na")
            tags["teryt:stan_na"] = self.simc_place.date
        if self.simc_place.parent:
            if "teryt:sympod" not in tags or tags['teryt:sympod'] != self.simc_place.parent.id:
                updated.append("teryt:sympod")
                tags["teryt:sympod"] = self.simc_place.parent.id
        elif "teryt:sympod" in tags:
            updated.append("teryt:sympod")
            del tags["teryt:sympod"]
        
        is_in = []
        is_in_places = {}
        if self.powiat.is_capital and self.name != "Warszawa":
            is_in_places["city"] = "Warszawa"
        parent = self.simc_place.parent
        while parent:
            is_in.append(parent.name)
            parent_place = self._by_simc_id.get(parent.id)
            if parent_place:
                is_in_places[parent_place.type] = parent_place.name
            parent = parent.parent

        if self.simc_place.rm not in ("00", "99", "95") and not self.gmina.is_city(self.name):
            is_in.append(self.gmina.full_name())
        if not self.powiat.is_city:
            is_in.append(self.powiat.full_name())
        elif self.powiat.is_capital and self.name != self.powiat.name:
            is_in.append(self.powiat.full_name())
        is_in += [self.wojewodztwo.full_name(), u"Poland"]
        is_in_tags = set([unicode(tag).lower() for tag in is_in])
        is_in = u", ".join(is_in)

        if "is_in" in tags:
            orig_is_in = tags['is_in'].replace(u";", u",")
            orig_is_in_tags = orig_is_in.split(u",")
            orig_is_in_tags = [unicode(t).strip().lower() for t in orig_is_in_tags]
            orig_is_in_tags = set(orig_is_in_tags)
            if self.powiat.is_capital:
                orig_is_in_tags.discard("powiat st. warszawa")
        else:
            orig_is_in = None
            orig_is_in_tags = set()

        if not orig_is_in:
            updated.append("is_in")
            tags['is_in'] = is_in
        elif orig_is_in != is_in:
            if not (orig_is_in_tags - is_in_tags):
                # original is_in is a subset of new is_in
                updated.append("is_in")
                tags['is_in'] = is_in
            else:
                reporting.output_msg("warnings", u"Uwaga: nie zmienione"
                        u" is_in='%s' dla %r (nasze: %r, istniejące: %r, różnica: %r)" 
                        % (tags['is_in'], self, is_in_tags, orig_is_in_tags,
                                                (orig_is_in_tags - is_in_tags)))

        if "is_in:country" not in tags or tags['is_in:country'] != "Poland":
            updated.append("is_in:country")
            tags['is_in:country'] = "Poland"
        if "is_in:province" not in tags or tags['is_in:province'] != self.wojewodztwo.full_name():
            updated.append("is_in:province")
            tags['is_in:province'] = self.wojewodztwo.full_name()
        if "is_in:county" not in tags or tags["is_in:county"] != self.powiat.full_name():
            updated.append("is_in:county")
            tags['is_in:county'] = self.powiat.full_name()
        if "is_in:municipality" not in tags or tags["is_in:municipality"] != self.gmina.full_name():
            updated.append("is_in:municipality")
            tags['is_in:municipality'] = self.gmina.full_name()

        for parent_type in ("village", "suburb", "city", "town"):
            parent_name = is_in_places.get(parent_type)
            tag_name = "is_in:" + parent_type
            if not parent_name:
                if tag_name in tags:
                    updated.append("tag_name")
                    del tags[tag_name]
            elif tag_name not in tags or tags[tag_name] != parent_name:
                updated.append("tag_name")
                tags[tag_name] = parent_name

        if updated:
            reporting.output_msg("info", u"%s: zmieniono: %s" % (
                                    self, u", ".join(updated)))
        return len(updated) > 0

    @classmethod
    def by_id(cls, place_id):
        """Return single place identified by a OSM id."""
        return self._by_id[place_id]

    @classmethod
    def by_simc_id(cls, simc_id):
        """Return single place identified by a SIMC id."""
        return self._by_simc_id[simc_id]

    @classmethod
    def by_name(cls, name):
        """Return all places matching a name."""
        return cls._by_name[name.lower()]

    @classmethod
    def by_type(cls, place_type):
        """Return all places of given type."""
        return cls._by_type[place_type]

    @classmethod
    def count(cls):
        return len(cls._by_id.items())

    @classmethod
    def all(cls):
        return cls._by_id.values()

    def __repr__(self):
        return "<OSM_Place #%s %r>" % (self.id, self.name)
    
    def __unicode__(self):
        if self.name is None:
            return u"unknown"
        if self.is_in:
            return u"%s, %s" % (self.name, self.is_in)
        else:
            return self.name

def load_osm():
    reporting = Reporting()
    row_count = count_elements("data/data.osm", "node")
    reporting.progress_start(u"Ładuję data/data.osm", row_count)
    for event, elem in ElementTree.iterparse("data/data.osm"):
        if event == 'end' and elem.tag == 'node':
            osm_place = OSM_Place(elem)
            reporting.progress()
    reporting.progress_stop()
    reporting.output_msg("stats", u"Załadowano %i miejsc." 
                    u"Dopasowano %i województw, %i powiatów i %i gmin." % (
                    OSM_Place.count(), OSM_Place.woj_matched,
                                OSM_Place.pow_matched, OSM_Place.gmi_matched))
