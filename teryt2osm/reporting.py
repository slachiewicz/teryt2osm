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
Status and error reporting facilities.
"""

__version__ = "$Revision$"

import sys
import os
import codecs
import xml.etree.cElementTree as ElementTree

class Error(Exception):
    pass

class ProgressError(Error):
    pass

class ChannelError(Error):
    pass

class Channel(object):
    def __init__(self, name, location = None):
        """Create channel. `name` is base channel name, `location` 
        is a location data (list of one to three of [wojewodztwo, powiat,
        gmina])""" 
        self.name = name
        if location is None:
            location = []
        self.location = location
        self.level = len(location)
        if self.level > 3:
            raise ChannelError, "Channel too deep. Maximum depth level is 3"
        if self.level:
            if "." in location or ".." in location:
                raise ValueError, "Forbidden entries in channel location!"
            location = [ l.replace("/", "_").replace("\\", "_")  for l in location ]
            self.directory = os.path.join("reports", os.path.join(*location))
        else:
            self.directory = "reports"
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        if name in (".", ".."):
            raise ValueError, "Forbidden channel name!"
        name = name.replace("/", "_").replace("\\", "_")
        self.log_file = codecs.open( os.path.join(self.directory, name + ".txt"), "w", "utf-8" )
        self.counter = 0
        self.quiet = False
        self.split_level = 0
        self.subchannels = {}
        self.map_file = None

    def __del__(self):
        self.close()

    def close(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        if self.map_file:
            self.close_map_file()

    def close_map_file(self):
        self.map_file.write("</osm>\n")
        self.map_file.close()
        self.map_file = None

    def set_mapping(self, value):
        if not self.map_file:
            if value:
                self.map_file = file( os.path.join(self.directory, 
                                                    self.name + ".osm"), "w" )
                self.map_file.write('<osm generator="teryt2osm" version="0.5">\n')
        elif not value:
            self.close_map_file()
        for subch in self.subchannels.values():
            subch.mapping = value
    def get_mapping(self):
        if self.map_file:
            return True
        else:
            return False
    mapping = property(get_mapping, set_mapping)

    def emit(self, msg, location):
        self.log_file.write(u"%s\n" % (msg,))
        if self.map_file and isinstance(location, OSM_Place):
            self.map_file.write(
                    ElementTree.tostring(location.element, "utf-8"))
        if not self.split_level:
            return
        try:
            if self.level == 0:
                    loc_obj = location.wojewodztwo
            elif self.level == 1:
                    loc_obj = location.powiat
            elif self.level == 2:
                    loc_obj = location.gmina
        except AttributeError, KeyError:
            loc_obj = None
        if loc_obj:
            loc_name = loc_obj.name
            split_level = self.split_level - 1
        else:
            loc_name = u"_brak"
            split_level = 0
        if loc_name in self.subchannels:
            subchannel = self.subchannels[loc_name]
        else:
            subchannel = Channel(self.name, self.location + [loc_name])
            if self.mapping:
                subchannel.mapping = True
            self.subchannels[loc_name] = subchannel
        subchannel.split_level = split_level
        subchannel.emit(msg, location)
    def __repr__(self):
        return "<Channel %i %r quiet=%r>" % (id(self), self.name, self.quiet)

class Reporting(object):
    instance = None

    def _init(self, logging = True):
        global OSM_Place
        from teryt2osm.osm_places import OSM_Place
        self.logging = True
        self.progress_total = None
        self.progress_step = None
        self.progress_value = None
        self.need_eol = False
        self.channels = {}
        if not os.path.exists("reports"):
            os.mkdir("reports")
        self.log_file = codecs.open( os.path.join("reports",  "log.txt"), "w", "utf-8" )

    def __del__(self):
        self.close()

    def close(self):
        if self.need_eol:
            print >>sys.stderr
        if self.log_file:
            self.log_file.close()
        if Reporting.instance is self:
            Reporting.instance = None
        for channel in self.channels.values():
            channel.close()
        self.channels = {}
    
    def __new__(cls, logging = True):
        if cls.instance is None:
            cls.instance = object.__new__(cls)
            cls.instance._init(logging = logging)
        return cls.instance

    def get_channel(self, name):
        if name in self.channels:
            return self.channels[name]
        channel = Channel(name)
        self.channels[name] = channel
        return channel

    def config_channel(self, name, quiet = None, mapping = None, split_level = None):
        channel = self.get_channel(name)
        if quiet is not None:
            channel.quiet = quiet
        if mapping is not None:
            channel.mapping = mapping
        if split_level is not None:
            channel.split_level = split_level

    def log(self, msg):
        print >> self.log_file, msg

    def print_msg(self, msg):
        if self.need_eol:
            print >>sys.stderr, u"\n%s" % (msg,)
            self.need_eol = False
        else:
            print >>sys.stderr, msg

    def output_msg(self, channel_name, msg, location = None):
        """Output a single message via channel 'channel'."""
        channel = self.get_channel(channel_name)
        if not channel.quiet:
            self.print_msg(msg)
            if self.logging:
                self.log(msg)
        if self.logging:
            channel.emit(msg, location)

    def progress_start(self, msg, total, step = 1):
        """Start progrss reporting.

        :Parameters:
          - `total`: total number of progrss point
          - `step`: percentage step when progress counter should be updated
        """
        if self.progress_total:
            raise ProgressError, u"Progress reporting already started."
        self.progress_total = total
        self.progress_step = max(int(total * step / 100), 1)
        self.progress_value = 0
        self.progress_msg = msg
        if self.logging:
            self.log(u"%s… rozpoczęte" % (msg,))
        sys.stderr.write(u"\r%s…  " % (msg,))
        sys.stderr.flush()
        self.need_eol = True

    def progress(self, increment = None, value = None):
        if not self.progress_total:
            raise ProgressError, u"Progress reporting not started."
        if increment is not None:
            self.progress_value += increment
        elif value is not None:
            self.progress_value = value
        else:
            self.progress_value += 1
            if self.progress_value % self.progress_step:
                return
        sys.stderr.write(u"\r%s… %2i%%  " % (self.progress_msg,
                self.progress_value * 100 / self.progress_total))
        sys.stderr.flush()
        self.need_eol = True

    def progress_stop(self):
        if not self.progress_total:
            raise ProgressError, u"Progress reporting not started."
        print >>sys.stderr, "\r%s 100%%  " % (self.progress_msg,)
        self.progress_total = None
        self.progress_step = None
        self.progress_value = None
        self.need_eol = False
        if self.logging:
            self.log(u"%s… zakończone" % self.progress_msg)
