#   Copyright (C) 2013 Lunatixz
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os
import xbmcaddon, xbmc, xbmcgui, xbmcvfs
import Settings
import sys, re

from FileAccess import FileLock


def log(msg, level = xbmc.LOGDEBUG):
    try:
        xbmc.log(ADDON_ID + '-' + ascii(msg), level)
    except:
        pass


def uni(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode):
           string = unicode(string, encoding)

    return string


def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')

    return string

ADDON_ID = 'script.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_INFO = REAL_SETTINGS.getAddonInfo('path')
VERSION = "0.3.5"
TIMEOUT = 15 * 1000
TOTAL_FILL_CHANNELS = 20
PREP_CHANNEL_TIME = 60 * 60 * 24 * 5
ALLOW_CHANNEL_HISTORY_TIME = 60 * 60 * 24 * 1
NOTIFICATION_CHECK_TIME = 5
NOTIFICATION_TIME_BEFORE_END = 90
NOTIFICATION_DISPLAY_TIME = 8

MODE_RESUME = 1
MODE_ALWAYSPAUSE = 2
MODE_ORDERAIRDATE = 4
MODE_RANDOM = 8
MODE_REALTIME = 16
MODE_SERIAL = MODE_RESUME | MODE_ALWAYSPAUSE | MODE_ORDERAIRDATE
MODE_STARTMODES = MODE_RANDOM | MODE_REALTIME | MODE_RESUME
CHANNEL_SHARING = False

#LOCATIONS
SETTINGS_LOC = 'special://profile/addon_data/' + ADDON_ID
CHANNELS_LOC = os.path.join(SETTINGS_LOC, 'cache') + '/'
GEN_CHAN_LOC = os.path.join(CHANNELS_LOC, 'generated') + '/'
MADE_CHAN_LOC = os.path.join(CHANNELS_LOC, 'stored') + '/'
ART_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'artwork')) + '/'
BCT_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'bct')) + '/'
DEFAULT_IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'images')) + '/'

LOCK_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache' + '/'))
if REAL_SETTINGS.getSetting('ChannelSharing') == "true":
    CHANNEL_SHARING = True
    LOCK_LOC = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('SettingsFolder'), 'cache')) + '/'


    #SKIN SELECT
if int(REAL_SETTINGS.getSetting('SkinSelector')) == 0:
    Skin_Select = 'default'
    
if REAL_SETTINGS.getSetting("SkinLogos") == "true":
        REAL_SETTINGS.setSetting('ChannelLogoFolder', 'special://home/addons/script.pseudotv.live/resources/skins/default/images/')

elif int(REAL_SETTINGS.getSetting('SkinSelector')) == 1:
    Skin_Select = 'PTVL'

elif int(REAL_SETTINGS.getSetting('SkinSelector')) == 2:
    Skin_Select = 'Aurora'
    if REAL_SETTINGS.getSetting("SkinLogos") == "true":
        REAL_SETTINGS.setSetting('ChannelLogoFolder', 'special://home/addons/script.pseudotv.live/resources/skins/' +Skin_Select+ '/images/')

elif int(REAL_SETTINGS.getSetting('SkinSelector')) == 3:
    Skin_Select = 'ConCast'


#VERIFY PATHS
if os.path.exists(xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', Skin_Select, 'images'))):
    IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', Skin_Select, 'images')) + '/'
else:
    IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'images')) + '/'

if os.path.exists(xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', Skin_Select, 'media', 'epg-genres')) + '/'):
    EPGGENRE_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', Skin_Select, 'media', 'epg-genres')) + '/'
else:
    EPGGENRE_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media', 'epg-genres')) + '/'
       
if os.path.exists(xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', Skin_Select, 'media'))): 
    MEDIA_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', Skin_Select, 'media')) + '/'
else:
    MEDIA_LOC = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media')) + '/'
 
#SETTOP BOX
# if REAL_SETTINGS.getSetting('EnableSettop') == 'true':
    # REAL_SETTINGS.setSetting('Auto_Start', 'true')
    # REAL_SETTINGS.setSetting('timer_amount', '1')
    
SHORT_CLIP_ENUM = [15,30,60,90,120,180,240,300,360,420,460]
INFOBAR_TIMER = [3,5,10,15,20,25]
AT_Limit = [25,50,100,250,500,1000,0]

GlobalFileLock = FileLock()
ADDON_SETTINGS = Settings.Settings()
 
TIME_BAR = 'pstvlTimeBar.png'
BUTTON_FOCUS = 'pstvlButtonFocus.png'
BUTTON_NO_FOCUS = 'pstvlButtonNoFocus.png'

RULES_ACTION_START = 1
RULES_ACTION_JSON = 2
RULES_ACTION_LIST = 4
RULES_ACTION_BEFORE_CLEAR = 8
RULES_ACTION_BEFORE_TIME = 16
RULES_ACTION_FINAL_MADE = 32
RULES_ACTION_FINAL_LOADED = 64
RULES_ACTION_OVERLAY_SET_CHANNEL = 128
RULES_ACTION_OVERLAY_SET_CHANNEL_END = 256

# Maximum is 10 for this
RULES_PER_PAGE = 7

ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGEUP = 5
ACTION_PAGEDOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = (9, 10, 92, 216, 247, 257, 275, 61467, 61448,)
ACTION_SHOW_INFO = 11
ACTION_PAUSE = 12
ACTION_STOP = 13
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15
ACTION_STEP_FOWARD = 17
ACTION_STEP_BACK = 18
ACTION_BIG_STEP_FORWARD = 19
ACTION_BIG_STEP_BACK = 20
ACTION_OSD = 122
ACTION_NUMBER_0 = 58
ACTION_NUMBER_1 = 59
ACTION_NUMBER_2 = 60
ACTION_NUMBER_3 = 61
ACTION_NUMBER_4 = 62
ACTION_NUMBER_5 = 63
ACTION_NUMBER_6 = 64
ACTION_NUMBER_7 = 65
ACTION_NUMBER_8 = 66
ACTION_NUMBER_9 = 67
ACTION_PLAYER_FORWARD = 73
ACTION_PLAYER_REWIND = 74
ACTION_PLAYER_PLAY = 75
ACTION_PLAYER_PLAYPAUSE = 76
#ACTION_MENU = 117
ACTION_MENU = 7
ACTION_INVALID = 999
