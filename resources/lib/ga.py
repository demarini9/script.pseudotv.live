"""""
Simple proof of concept code to push data to Google Analytics.
 
Related blog posts:
 * http://www.canb.net/2012/01/push-data-to-google-analytics-with.html
 * https://medium.com/python-programming-language/80eb9691d61f
"""

import Globals
import EPGWindow
import ChannelList
import sys, re

from random import randint
from urllib import urlencode
from urllib2 import urlopen
from urlparse import urlunparse
from hashlib import sha1
from os import environ
from Overlay import *
from Donor import Donor

# Set your proprty id via the environment or simply type it
# below
PROPERTY_ID = environ.get("GA_PROPERTY_ID", "UA-45979766-1")
 
# Generate the visitor identifier somehow. I get it from the
# environment, calculate the SHA1 sum of it, convert this from base 16
# to base 10 and get first 10 digits of this number.

bcts = ''
if Globals.REAL_SETTINGS.getSetting('bumpers') == '':
    bcts = 'B/'
if Globals.REAL_SETTINGS.getSetting('commercials') != '0':
    bcts = bcts + 'C/'
if Globals.REAL_SETTINGS.getSetting('trailers') != '0':
    bcts = bcts + 'T'

if Globals.REAL_SETTINGS.getSetting('Donor_Enabled') == 'true' and Globals.REAL_SETTINGS.getSetting('Donor_UP') != 'User:Password':
    donor = Globals.REAL_SETTINGS.getSetting('Donor_UP')
    donor = donor.split(':')[0]
else:
    donor = ''

if Globals.REAL_SETTINGS.getSetting('Visitor_GA') == '':
    from random import randint
    Globals.REAL_SETTINGS.setSetting('Visitor_GA', str(randint(0, 0x7fffffff)))

# VISITOR = environ.get("GA_VISITOR", "xxxxx")
# VISITOR = str(int("0x%s" % sha1(VISITOR).hexdigest(), 0))[:10]
VISITOR = str(Globals.REAL_SETTINGS.getSetting("Visitor_GA"))
# The path to visit
PATH = ("PTVL/[" + str(VISITOR) + '][' + str(donor) + '][' + str(VERSION) + '][' + str(Skin_Select) + '][' + bcts + ']')
## PATH = "PTVL/"+Vistor"/"+CHTYPE+"/"+SOURCE+"/"+SKIN"
##Chtype = Current Chtype being used
##Source = rtmp/http/pvr/hdhomerun/etc
##Skin = Skin being used
 
# Collect everything in a dictionary
DATA = {"utmwv": "5.2.2d",
        "utmn": str(randint(1, 9999999999)),
        "utmp": PATH,
        "utmac": PROPERTY_ID,
        "utmcc": "__utma=%s;" % ".".join(["1", VISITOR, "1", "1", "1", "1"])}
 
# Encode this data and generate the final URL
URL = urlunparse(("http",
                  "www.google-analytics.com",
                  "/__utm.gif",
                  "",
                  urlencode(DATA),
                  ""))
 
# Make the request
print "Requesting", URL
print urlopen(URL).info()