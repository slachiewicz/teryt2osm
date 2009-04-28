#!/usr/bin/python -u
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
Wysyła gotowe pliki OSM.
"""

__version__ = "$Revision: 21 $"

import os
import subprocess
import sys
import traceback
import codecs
import locale

import httplib

from teryt2osm.utils import setup_locale
import xml.etree.cElementTree as ElementTree
import urlparse

class HTTPError(Exception):
    pass

class OSM_API(object):
    url = 'http://api.openstreetmap.org/'
    def __init__(self, username = None, password = None):
        if username and password:
            self.username = username
            self.password = password
        else:
            self.username = ""
            self.password = ""
        self.changeset = None

    def __del__(self):
        if self.changeset is not None:
            self.close_changeset()

    def _run_request(self, method, url, body = None, content_type = "text/xml"):
        url = urlparse.urljoin(self.url, url)
        purl = urlparse.urlparse(url)
        if purl.scheme != "http":
            raise ValueError, "Unsupported url scheme: %r" % (purl.scheme,)
        if ":" in purl.netloc:
            host, port = purl.netloc.split(":", 1)
            port = int(port)
        else:
            host = purl.netloc
            port = None
        conn = httplib.HTTPConnection(host, port)
#        conn.set_debuglevel(10)
        try:
            url = purl.path
            if purl.query:
                url += "?" + query
            headers = {}
            if body:
                headers["Content-Type"] = content_type
            conn.request(method, url, body, headers)
            response = conn.getresponse()
            if response.status == httplib.UNAUTHORIZED and self.username:
                conn.close()
                conn = httplib.HTTPConnection(host, port)
#                conn.set_debuglevel(10)
                creds = self.username + ":" + self.password
                headers["Authorization"] = "Basic " + creds.encode("base64").strip()
                conn.request(method, url, body, headers)
                response = conn.getresponse()
            if response.status == httplib.OK:
                response_body = response.read()
            else:
                raise HTTPError, "%02i: %s" % (response.status, response.reason)
        finally:
            conn.close()
        return response_body

    def create_changeset(self, created_by, comment):
        if self.changeset is not None:
            raise RuntimeError, "Changeset already opened"
        print >>sys.stderr, u"Tworzę changeset…",
        sys.stderr.flush()
        root = ElementTree.Element("osm")
        tree = ElementTree.ElementTree(root)
        element = ElementTree.SubElement(root, "changeset")
        ElementTree.SubElement(element, "tag", {"k": "created_by", "v": created_by})
        ElementTree.SubElement(element, "tag", {"k": "comment", "v": comment})
        body = ElementTree.tostring(root, "utf-8")
        reply = self._run_request("PUT", "/api/0.6/changeset/create", body)
        changeset = int(reply.strip())
        print >>sys.stderr, "zrobione. Id:", changeset
        self.changeset = changeset

    def upload(self, change):
        if self.changeset is None:
            raise RuntimeError, "Changeset not opened"
        print >>sys.stderr, u"Wysyłam zmiany…",
        sys.stderr.flush()
        for operation in change:
            if operation.tag not in ("create", "modify", "delete"):
                continue
            for element in operation:
                element.attrib["changeset"] = str(self.changeset)
        body = ElementTree.tostring(change, "utf-8")
        reply = self._run_request("POST", "/api/0.6/changeset/%i/upload" 
                                                % (self.changeset,), body)
        print >>sys.stderr, "zrobione."

    def close_changeset(self):
        if self.changeset is None:
            raise RuntimeError, "Changeset not opened"
        print >>sys.stderr, u"Zamykam…",
        sys.stderr.flush()
        reply = self._run_request("PUT", "/api/0.6/changeset/%i/close" 
                                                    % (self.changeset,))
        self.changeset = None
        print >>sys.stderr, "zrobione."

try:
    this_dir = os.path.dirname(__file__)
    version = subprocess.Popen(["svnversion", this_dir], stdout = subprocess.PIPE).communicate()[0].strip()
    setup_locale()
    if len(sys.argv) < 2:
        print >>sys.stderr, u"Sposób użycia:"
        print >>sys.stderr, u"    %s <nazwa_plku> [<nazwa_pliku/>...]"
        sys.exit(1)

    login = raw_input("OSM login: ")
    if not login:
        sys.exit(1)
    password = raw_input("OSM password: ")
    if not login:
        sys.exit(1)

    api = OSM_API(login, password)

    changes = []
    for filename in sys.argv[1:]:
        if not os.path.exists(filename):
            print >>sys.stderr, u"Plik %r nie istnieje!" % (filename,)
            sys.exit(1)
        tree = ElementTree.parse(filename)
        root = tree.getroot()
        if root.tag != "osmChange" or root.attrib.get("version") != "0.3":
            print >>sys.stderr, u"Plik %s to nie osmChange w wersji 0.3!" % (filename,)
            sys.exit(1)

        if filename.endswith(".osc"):
            comment_fn = filename[:-4] + ".comment"
        else:
            comment_fn = filename + ".comment"
        try:
            comment_file = codecs.open(comment_fn, "r", "utf-8")
            comment = comment_file.read().strip()
            comment_file.close()
        except IOError:
            comment = None
        if not comment:
            comment = raw_input("Komentarz do zmiany %r: " % (filename,))
            if not comment:
                sys.exit(1)
            comment = comment.decode(encoding = locale.getlocale()[1])
        print u" Zmiany z pliku: %r" % (filename,)
        print u"      Komentarz: %s" % (comment,)
        print u"Jesteś pewien, że chcesz wysłać te zmiany?",
        sure = raw_input()
        if sure.lower() not in ("t", "tak"):
            print u"Pomijam...\n"
            continue
        print
        api.create_changeset(u"teryt2osm upload.py v. %s" % (version,), comment)
        try:
            api.upload(root)
        except HTTPError, err:
            print >>sys.stderr, err
            sys.exit(1)
        finally:
            api.close_changeset()
except HTTPError, err:
    print >>sys.stderr, err
    sys.exit(1)
except Exception,err:
    print >>sys.stderr, repr(err)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

