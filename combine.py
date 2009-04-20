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
Łączy dane z OSM z danymi z TERYT
"""

__version__ = "$Revision$"

import os
import sys
import traceback

from teryt2osm.utils import setup_locale, add_to_list_dict, count_elements
from teryt2osm.terc import Wojewodztwo, Powiat, Gmina, load_terc, write_wojewodztwa_wiki
from teryt2osm.simc import SIMC_Place, load_simc, write_wmrodz_wiki
from teryt2osm.osm_places import OSM_Place, load_osm
from teryt2osm.reporting import Reporting

def match_names():
    reporting = Reporting()
    reporting.progress_start("Dopasowywanie nazw", OSM_Place.count())
    found = []
    simc_matched = set()
    places = [(unicode(p), p) for p in OSM_Place.all()]
    places.sort()
    for name, osm_place in places:
        reporting.progress()
        if osm_place.name is None:
            reporting.output_msg("errors", u"%r: brak nazwy" % (osm_place,), osm_place)
            continue

        # Find matching entry in SIMC
        try:
            matching_simc_places = SIMC_Place.by_name(osm_place.name)
        except KeyError:
            reporting.output_msg("not_found", u"%s: nie znaleziono w TERYT" % (osm_place,), osm_place)
            continue
        simc_places = [place for place in matching_simc_places 
                                if place.type == osm_place.normalized_type ]
        if not simc_places:
            types_found = [ place.type for place in matching_simc_places ]
            reporting.output_msg("bad_type", u"%s: nie znalezionow w TERYT"
                        u" obiektu właściwego typu (%r, znaleziono: %r)" % (
                            osm_place, osm_place.type, types_found), osm_place)
            continue
        if len(simc_places) > 1:
            reporting.output_msg("ambigous", 
                    u"%s z OSM pasuje do wielu obiektów w SIMC: %s" % (osm_place,
                        ", ".join([str(p) for p in simc_places])), osm_place)
            continue
        simc_place = simc_places[0]

        # now check if reverse assignment is not ambigous
        matching_osm_places = OSM_Place.by_name(simc_place.name)
        confl_osm_places = []
        for place in matching_osm_places:
            if place is osm_place:
                continue
            if place.gmina and place.gmina != simc_place.gmina:
                continue
            if place.powiat and place.powiat != simc_place.powiat:
                continue
            if place.wojewodztwo and place.wojewodztwo != simc_place.wojewodztwo:
                continue
            confl_osm_places.append(place)
        if confl_osm_places:
            reporting.output_msg("ambigous", 
                        u"%s z SIMC pasuje do wielu obiektów w OMS: %s" % (simc_place,
                            ", ".join([str(p) for p in confl_osm_places])), osm_place)
            continue

        # good match
        osm_place.assign_simc(simc_place)
        reporting.output_msg("match", u"%s w OSM to %s w SIMC" % (osm_place, simc_place), osm_place) 
        found.append(osm_place)
        simc_matched.add(simc_place)

    reporting.progress_stop()
    reporting.output_msg("stats", u"%i z %i miejscowości z OSM znalezionych w SIMC" % (
                                                        len(found), OSM_Place.count()))
    reporting.output_msg("stats", u"%i z %i miejscowości z SIMC znalezionych w OSM" % (
                                                len(simc_matched), SIMC_Place.count()))

try:
    setup_locale()
    reporting = Reporting()
    reporting.config_channel("errors", split_level = 2, mapping = True)
    reporting.config_channel("bad_type", split_level = 2, mapping = True, quiet = True)
    reporting.config_channel("not_found", split_level = 2, quiet = True, mapping = True)
    reporting.config_channel("ambigous", split_level = 2, quiet = True, mapping = True)
    reporting.config_channel("match", split_level = 2, quiet = True, mapping = True)
    for filename in ("data.osm", "SIMC.xml", "TERC.xml", "WMRODZ.xml"):
        if not os.path.exists(os.path.join("data", filename)):
            reporting.output_msg("critical", u"Brakujący plik: %r" % (filename,))
            sys.exit(1)
    load_terc()
    write_wojewodztwa_wiki()
    load_simc()
    write_wmrodz_wiki()
    load_osm()
    match_names()
    reporting.close()
except Exception,err:
    print >>sys.stderr, repr(err)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
