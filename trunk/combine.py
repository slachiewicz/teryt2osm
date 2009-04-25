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
import subprocess
import sys
import traceback
import codecs

from teryt2osm.utils import setup_locale, add_to_list_dict, count_elements
from teryt2osm.terc import Wojewodztwo, Powiat, Gmina, load_terc, write_wojewodztwa_wiki
from teryt2osm.simc import SIMC_Place, load_simc, write_wmrodz_wiki
from teryt2osm.osm_places import OSM_Place, load_osm
from teryt2osm.reporting import Reporting
from teryt2osm.grid import Grid
import xml.etree.cElementTree as ElementTree

def match_names(pass_no, places_to_match, grid = None):
    reporting = Reporting()
    places_count = len(places_to_match)
    if grid:
        reporting.progress_start(
                u"Dopasowywanie nazw %i miejsc, przebieg %i, z siatką %s"
                        % (places_count, pass_no, grid), places_count)
    else:
        reporting.progress_start(
                u"Dopasowywanie nazw %i miejsc, przebieg %i"
                        % (places_count, pass_no), places_count)
    osm_matched = set()
    simc_matched = set()
    places = [ (str(p), p) for p in places_to_match ]
    for name, osm_place in places:
        reporting.progress()
        if osm_place.name is None:
            reporting.output_msg("errors", u"%r: brak nazwy" % (osm_place,), osm_place)
            continue

        # Find matching entry in SIMC
        try:
            matching_simc_places = SIMC_Place.by_name(osm_place.name)
        except KeyError:
            reporting.output_msg("not_found", u"%s: nie znaleziono w TERYT" 
                                                    % (osm_place,), osm_place)
            places_to_match.remove(osm_place)
            continue
        simc_places = [place for place in matching_simc_places 
                                if place.type == osm_place.normalized_type
                                    and place.osm_place is None]
        if not simc_places:
            types_found = [ place.type for place in matching_simc_places ]
            reporting.output_msg("bad_type", u"%s: nie znalezionow w TERYT"
                        u" obiektu właściwego typu (%r, znaleziono: %r)" % (
                            osm_place, osm_place.type, types_found), osm_place)
            continue

        if grid:
            cell = grid.get_cell(osm_place)
            simc_places = [ p for p in simc_places if p.powiat in cell.powiaty ]
            if len(simc_places) > 1:
                simc_places = [ p for p in simc_places if p.gmina in cell.gminy ]
            if not simc_places:
                reporting.output_msg("not_found",
                        u"%s: nie znaleziono w TERYT miejsca"
                        u" pasującego do komórki %s" % (osm_place, cell),
                        osm_place)
                continue

        if len(simc_places) > 1:
            if grid:
                reporting.output_msg("ambigous%i" % (pass_no,), 
                        u"%s z OSM pasuje do wielu obiektów"
                        u" SIMC w komórce %s: %s" % (osm_place, cell,
                            u", ".join([str(p) for p in simc_places])), 
                                                                osm_place)
            else:
                reporting.output_msg("ambigous%i" % (pass_no,), 
                        u"%s z OSM pasuje do wielu obiektów w SIMC: %s" % (osm_place,
                            u", ".join([str(p) for p in simc_places])), osm_place)
            continue
        simc_place = simc_places[0]

        # now check if reverse assignment is not ambigous
        matching_osm_places = OSM_Place.by_name(simc_place.name)
        confl_osm_places = []
        for place in matching_osm_places:
            if place is osm_place:
                continue
            if grid:
                if grid.get_cell(place) is not cell:
                    continue
            if place.gmina and place.gmina != simc_place.gmina:
                continue
            if place.powiat and place.powiat != simc_place.powiat:
                continue
            if place.wojewodztwo and place.wojewodztwo != simc_place.wojewodztwo:
                continue
            confl_osm_places.append(place)

        if confl_osm_places:
            reporting.output_msg("ambigous%i" % (pass_no,), 
                        u"%s z SIMC pasuje do wielu obiektów w OMS: %s" % (simc_place,
                            ", ".join([str(p) for p in confl_osm_places])), osm_place)
            continue
        
        if simc_place.osm_place:
            reporting.output_msg("ambigous%i" % (pass_no,), 
                    u"%s z SIMC ma już przypisany obiekt OSM: %s" % (
                        simc_place, simc_place.osm_place), osm_place)

        # good match
        osm_place.assign_simc(simc_place)
        simc_place.assign_osm(osm_place)

        reporting.output_msg("match", u"%s w OSM to %s w SIMC" % (osm_place, simc_place), osm_place) 
        osm_matched.add(osm_place)
        simc_matched.add(simc_place)
        places_to_match.remove(osm_place)

    reporting.progress_stop()
    reporting.output_msg("stats", 
            u"Przebieg %i: znaleziono w SIMC %i z %i miejscowości OSM" % (
                                    pass_no, len(osm_matched), places_count))
    return osm_matched, simc_matched

def refine(places, reference):
    """Refine places matches by removing those too far from their neighbours."""
    grid = Grid(reference, 23, 23)
    reporting.progress_start(
            u"Szukanie niepasujących powiązań, przebieg 1", len(places))
    bad_matches = []
    for place in places:
        cell = grid.get_cell(place)
        if place.simc_place.name == place.powiat.name:
            if cell.wojewodztwa.count(place.wojewodztwo) < 2:
                bad_matches.append(place)
                reporting.output_msg("bad_match", u"Prawdopodobnie źle dopasowany: %s" % (place,), place) 
        elif cell.powiaty.count(place.powiat) < 2:
            bad_matches.append(place)
            reporting.output_msg("bad_match", u"Prawdopodobnie źle dopasowany: %s" % (place,), place) 
        reporting.progress()
    reporting.progress_stop()
    reporting.output_msg("info", u"Znaleziono %i kandydatów do usunięcia" % (len(bad_matches),))

    grid = Grid(reference, 19, 19)
    reporting.progress_start(
            u"Szukanie niepasujących powiązań, przebieg 2", len(bad_matches))
    really_bad_matches = set()
    for place in bad_matches:
        cell = grid.get_cell(place)
        if place.simc_place.name == place.powiat.name:
            if cell.wojewodztwa.count(place.wojewodztwo) < 2:
                really_bad_matches.add(place)
                reporting.output_msg("really_bad_match", u"Prawdopodobnie źle dopasowany: %s" % (place,), place) 
        elif cell.powiaty.count(place.powiat) < 2:
            really_bad_matches.add(place)
            reporting.output_msg("really_bad_match", u"Źle dopasowany: %s" % (place,), place) 
        reporting.progress()
    reporting.progress_stop()
    reporting.output_msg("info", u"Znaleziono %i miejsc do usunięcia" % (len(really_bad_matches),))
    good_matches = set(places)
    good_matches -= really_bad_matches
    return good_matches

def match():
    preassigned =  set([p for p in OSM_Place.all() if p.simc_place])
    assigned = set(preassigned)
    reporting.output_msg("start", u"%i wstępnie (w danych OSM) przypisanych miejscowości" % (len(preassigned),))
    places_to_match = set([p for p in OSM_Place.all() if not p.simc_place])
    osm_matched1, simc_matched1 = match_names(1, places_to_match)
    assigned |=  osm_matched1
    grid = Grid(assigned, 31, 31)
    osm_matched2, simc_matched2 = match_names(2, places_to_match, grid)
    assigned |= osm_matched2
    grid = Grid(assigned, 43, 43)
    osm_matched3, simc_matched3 = match_names(3, places_to_match, grid)
    assigned |= osm_matched3
    matched = osm_matched1 | osm_matched2 | osm_matched3
    matched = refine(matched, assigned)
    assigned = set(preassigned).union(matched)
    return assigned

def update(places):
    updated = []
    for place in places:
        if place.update():
            updated.append(place)
    return updated

def write_changes(updated_places, created_by):
    reporting = Reporting()
    reporting.progress_start(u"Preparing osmChange files", len(updated_places))
    woj_trees = {}
    for place in updated_places:
        woj_name = place.wojewodztwo.name
        if not woj_name in woj_trees:
            root = ElementTree.Element(u"osmChange", version = u"0.3", generator = created_by)
            tree = ElementTree.ElementTree(root)
            modify = ElementTree.Element(u"modify", version = u"0.3", generator = created_by)
            root.append(modify)
            woj_trees[woj_name] = tree
        else:
            root = woj_trees[woj_name].getroot()
            modify = root[0]
        node = ElementTree.Element(u"node", id = place.id, lon = str(place.lon), lat = str(place.lat),
                    version = place.version, changeset = place.changeset)
        modify.append(node)
        for k, v in place.tags.items():
            if k == 'teryt:updated_by':
                continue
            tag = ElementTree.Element(u"tag", k = k, v = v)
            node.append(tag)
        tag = ElementTree.Element(u"tag", k = u"teryt:updated_by", v = created_by)
        node.append(tag)
        reporting.progress()
    reporting.progress_stop()

    reporting = Reporting()
    reporting.progress_start(u"Writting osmChange files", len(woj_trees))
    for woj_name, tree in woj_trees.items():
        basename = os.path.join("output", woj_name.encode("utf-8"))
        tree.write(basename + ".osc", "utf-8")
        comment_file = codecs.open(basename + ".comment", "w", "utf-8")
        print >> comment_file, u"TERYT import, województwo %s, prepared by %s" % (
                                                    woj_name, created_by)
        comment_file.close()
        reporting.progress()
    reporting.progress_stop()


try:
    this_dir = os.path.dirname(__file__)
    version = subprocess.Popen(["svnversion", this_dir], stdout = subprocess.PIPE).communicate()[0].strip()
    setup_locale()
    reporting = Reporting()
    reporting.output_msg("info", u"teryt2osm combine.py version: %s" % (version,))
    reporting.config_channel("errors", split_level = 2, mapping = True)
    reporting.config_channel("bad_type", split_level = 2, mapping = True, quiet = True)
    reporting.config_channel("not_found", split_level = 2, quiet = True, mapping = True)
    reporting.config_channel("ambigous1", split_level = 2, quiet = True, mapping = True)
    reporting.config_channel("ambigous2", split_level = 2, quiet = True, mapping = True)
    reporting.config_channel("ambigous3", split_level = 2, mapping = True)
    reporting.config_channel("match", split_level = 2, quiet = True, mapping = True)
    reporting.config_channel("bad_match", split_level = 1, quiet = True, mapping = True)
    reporting.config_channel("really_bad_match", split_level = 1, quiet = True, mapping = True)
    for filename in ("data.osm", "SIMC.xml", "TERC.xml", "WMRODZ.xml"):
        if not os.path.exists(os.path.join("data", filename)):
            reporting.output_msg("critical", u"Brakujący plik: %r" % (filename,))
            sys.exit(1)
    load_terc()
    write_wojewodztwa_wiki()
    load_simc()
    write_wmrodz_wiki()
    load_osm()
    assigned = match()
    updated = update(assigned)
    write_changes(updated, u"teryt2osm combine.py v. %s" % (version,))
    reporting.close()
except Exception,err:
    print >>sys.stderr, repr(err)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
