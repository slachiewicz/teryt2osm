#!/usr/bin/python
# vi: encoding=utf-8

from teryt2osm.utils import setup_locale
from teryt2osm.reporting import Reporting
import time

class Location(object):
    def __init__(self, name):
        self.name = name

class LocatedObject(object):
    def __init__(self, woj_name, pow_name, gmi_name):
        if woj_name:
            self.wojewodztwo = Location(woj_name)
        else:
            self.wojewodztwo = None
        if pow_name:
            self.powiat = Location(pow_name)
        else:
            self.powiat = None
        if gmi_name:
            self.gmina = Location(gmi_name)
        else:
            self.gmina = None

setup_locale()
reporting = Reporting()
reporting.progress_start("progress", 10)
time.sleep(0.2)
reporting.progress()
time.sleep(0.2)
reporting.output_msg("debug", u"Cośtam cośtam")
time.sleep(0.2)
reporting2 = Reporting()
reporting.progress()
time.sleep(0.2)
reporting2.output_msg("debug", u"Cośtam cośtam")
time.sleep(0.2)
reporting2.output_msg("debug", u"Cośtam cośtam")
reporting.progress()
reporting.output_msg("debug", u"Cośtam cośtam")
reporting.output_msg("debug", u"Cośtam cośtam")
time.sleep(0.2)
reporting.progress_stop()

for level in range(0,4):
    channel = "test%i" % (level,)
    reporting.config_channel(channel, split_level = level)
    reporting.output_msg(channel, "loc1", LocatedObject(None, None, None))
    reporting.output_msg(channel, "loc2", LocatedObject("1", None, None))
    reporting.output_msg(channel, "loc3", LocatedObject("1", "1/1", None))
    reporting.output_msg(channel, "loc4", LocatedObject("1", "1/2", None))
    reporting.output_msg(channel, "loc5", LocatedObject("1", "1/1", "1/1/1"))
    reporting.output_msg(channel, "loc6", LocatedObject("1", "1/1", "1/1/2"))
    reporting.output_msg(channel, "loc7", LocatedObject("1", "1/2", "1/2/1"))
    reporting.output_msg(channel, "loc8", LocatedObject("2", None, None))
    reporting.output_msg(channel, "loc9", LocatedObject("2", "2/1", None))
    reporting.output_msg(channel, "loc10", LocatedObject("2", "2/2", None))
    reporting.output_msg(channel, "loc11", LocatedObject("2", "2/1", "2/1/1"))
    reporting.output_msg(channel, "loc12", LocatedObject("2", "2/1", "2/1/2"))
    reporting.output_msg(channel, "loc13", LocatedObject("2", "2/2", "2/2/1"))


reporting.close()
