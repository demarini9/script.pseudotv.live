#   Copyright (C) 2013 Lunatixz
#
#
# This file is part of PseudoTV Live.
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

import xbmc, xbmcgui, xbmcaddon
import subprocess, os, sys, re
import time, datetime, threading
import httplib, urllib, urllib2, feedparser
import base64, shutil, random
import Globals
import tvdb_api

# # Use json instead of simplejson when python v2.7 or greater
# if sys.version_info < (2, 7):
    # import simplejson
# else:
    # import json as simplejson
    
# try:
    # import StorageServer
# except:
   # import storageserverdummy as StorageServer

# # cache = StorageServer.StorageServer("script.pseudotv.live", 24) # (Your plugin name, Cache time in hours)

from urllib import unquote
from urllib import urlopen
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString
from subprocess import Popen, PIPE, STDOUT
from BeautifulSoup import BeautifulSoup
from Playlist import Playlist
from Globals import *
from Channel import Channel
from VideoParser import VideoParser
from FileAccess import FileLock, FileAccess
from sickbeard import *
from couchpotato import *
from tvdb import *
from tmdb import *

try:
    from Donor import *
except:
    pass

class ChannelList:
    def __init__(self):
        self.networkList = []
        self.studioList = []
        self.mixedGenreList = []
        self.showGenreList = []
        self.movieGenreList = []
        self.musicGenreList = []
        self.showList = []
        self.channels = []
        self.videoParser = VideoParser()
        self.httpJSON = True
        self.sleepTime = 0
        self.discoveredWebServer = False
        self.threadPaused = False
        self.runningActionChannel = 0
        self.runningActionId = 0
        self.enteredChannelCount = 0
        self.background = True
        random.seed()
        self.cached_json_detailed_TV = []
        self.cached_json_detailed_Movie = []
        self.cached_json_detailed_trailers = []
        
        try:
            self.Donor = Donor()
        except:
            pass

            
    def readConfig(self):
        self.channelResetSetting = int(REAL_SETTINGS.getSetting("ChannelResetSetting"))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(self.forceReset))
        self.updateDialog = xbmcgui.DialogProgress()
        self.startMode = int(REAL_SETTINGS.getSetting("StartMode"))
        self.log('Start Mode is ' + str(self.startMode))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.incIceLibrary = REAL_SETTINGS.getSetting('IncludeIceLib') == "true"
        self.log("IceLibrary is " + str(self.incIceLibrary))
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.findMaxChannels()

        if self.forceReset:
            REAL_SETTINGS.setSetting('ForceChannelReset', "False")
            self.forceReset = False

        try:
            self.lastResetTime = int(ADDON_SETTINGS.getSetting("LastResetTime"))
        except:
            self.lastResetTime = 0

        try:
            self.lastExitTime = int(ADDON_SETTINGS.getSetting("LastExitTime"))
        except:
            self.lastExitTime = int(time.time())


    def setupList(self):
        self.readConfig()
        self.updateDialog.create("PseudoTV Live", "Updating channel list")
        self.updateDialog.update(0, "Updating channel list")
        self.updateDialogProgress = 0
        foundvalid = False
        makenewlists = False
        self.background = False

        if self.backgroundUpdating > 0 and self.myOverlay.isMaster == True:
            makenewlists = True

        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.updateDialogProgress = i * 100 // self.enteredChannelCount
            self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(i + 1), "waiting for file lock")
            self.channels.append(Channel())

            # If the user pressed cancel, stop everything and exit
            if self.updateDialog.iscanceled():
                self.log('Update channels cancelled')
                self.updateDialog.close()
                return None

            self.setupChannel(i + 1, False, makenewlists, False)

            if self.channels[i].isValid:
                foundvalid = True

        if makenewlists == True:
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false')

        if foundvalid == False and makenewlists == False:
            for i in range(self.maxChannels):
                self.updateDialogProgress = i * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(i + 1), "waiting for file lock", '')
                self.setupChannel(i + 1, False, True, False)

                if self.channels[i].isValid:
                    foundvalid = True
                    break


        self.updateDialog.update(100, "Update complete")
        self.updateDialog.close()

        return self.channels


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)

    
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if REAL_SETTINGS.getSetting('enable_Debug') == "true":
            log('ChannelList: ' + msg, level)
                    
    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        self.maxChannels = 0
        self.enteredChannelCount = 0

        for i in range(999):
            chtype = 9999
            chsetting1 = ''
            chsetting2 = ''
            chsetting3 = ''
            chsetting4 = ''

            try:
                chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_type'))
                chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_1')
                chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_2')
                chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_3')
                chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_4')
            except:
                pass

            if chtype == 0:
                if FileAccess.exists(xbmc.translatePath(chsetting1)):
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
            elif chtype <= 13:
                if len(chsetting1) > 0:
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
                    
            if self.forceReset and (chtype != 9999):
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_changed', "True")

        self.log('findMaxChannels return ' + str(self.maxChannels))


    def determineWebServer(self):
        if self.discoveredWebServer:
            return

        self.discoveredWebServer = True
        self.webPort = 8080
        self.webUsername = ''
        self.webPassword = ''
        fle = xbmc.translatePath("special://profile/guisettings.xml")

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("determineWebServer Unable to open the settings file", xbmc.LOGERROR)
            self.httpJSON = False
            return

        try:
            dom = parse(xml)
        except:
            self.log('determineWebServer Unable to parse settings file', xbmc.LOGERROR)
            self.httpJSON = False
            return

        xml.close()

        try:
            plname = dom.getElementsByTagName('webserver')
            self.httpJSON = (plname[0].childNodes[0].nodeValue.lower() == 'true')
            self.log('determineWebServer is ' + str(self.httpJSON))

            if self.httpJSON == True:
                plname = dom.getElementsByTagName('webserverport')
                self.webPort = int(plname[0].childNodes[0].nodeValue)
                self.log('determineWebServer port ' + str(self.webPort))
                plname = dom.getElementsByTagName('webserverusername')
                self.webUsername = plname[0].childNodes[0].nodeValue
                self.log('determineWebServer username ' + self.webUsername)
                plname = dom.getElementsByTagName('webserverpassword')
                self.webPassword = plname[0].childNodes[0].nodeValue
                self.log('determineWebServer password is ' + self.webPassword)
        except:
            return


    # Code for sending JSON through http adapted from code by sffjunkie (forum.xbmc.org/showthread.php?t=92196)
    def sendJSON(self, command):
        self.log('sendJSON')
        data = ''
        usedhttp = False

        self.determineWebServer()

        if USING_EDEN:
            command = command.replace('fields', 'properties')

        self.log('sendJSON command: ' + command)

        # If there have been problems using the server, just skip the attempt and use executejsonrpc
        if self.httpJSON == True:
            try:
                payload = command.encode('utf-8')
            except:
                return data

            headers = {'Content-Type': 'application/json-rpc; charset=utf-8'}

            if self.webUsername != '':
                userpass = base64.encodestring('%s:%s' % (self.webUsername, self.webPassword))[:-1]
                headers['Authorization'] = 'Basic %s' % userpass

            try:
                conn = httplib.HTTPConnection('127.0.0.1', self.webPort)
                conn.request('POST', '/jsonrpc', payload, headers)
                response = conn.getresponse()

                if response.status == 200:
                    data = uni(response.read())
                    usedhttp = True

                conn.close()
            except:
                self.log("Exception when getting JSON data")

        if usedhttp == False:
            self.httpJSON = False
            
            try:
                data = xbmc.executeJSONRPC(uni(command))
            except UnicodeEncodeError:
                data = xbmc.executeJSONRPC(ascii(command))

        return uni(data)


    def setupChannel(self, channel, background = False, makenewlist = False, append = False):
        self.log('setupChannel ' + str(channel))
        returnval = False
        createlist = makenewlist
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''
        chsetting3 = ''
        chsetting4 = ''
        needsreset = False
        self.background = background
        self.settingChannel = channel

        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
            chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_3')
            chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_4')

        except:
            pass

        while len(self.channels) < channel:
            self.channels.append(Channel())

        if chtype == 9999:
            self.channels[channel - 1].isValid = False
            return False

        self.channels[channel - 1].type = chtype
        self.channels[channel - 1].isSetup = True
        self.channels[channel - 1].loadRules(channel)
        self.runActions(RULES_ACTION_START, channel, self.channels[channel - 1])

        try:
            needsreset = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_changed') == 'True'
            
            # force rebuild for livetv channels w/ TVDB and TMDB
            if chtype == 8 and REAL_SETTINGS.getSetting('EnhancedLiveTV') == 'false':
                self.log("Force LiveTV rebuild")
                needsreset = True
                makenewlist = True
            
            if needsreset:
                self.channels[channel - 1].isSetup = False
        except:
            pass

        # If possible, use an existing playlist
        # Don't do this if we're appending an existing channel
        # Don't load if we need to reset anyway
        if FileAccess.exists(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') and append == False and needsreset == False:
            try:
                self.channels[channel - 1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time', True))
                createlist = True

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(channel), "reading playlist", '')

                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    returnval = True

                    # If this channel has been watched for longer than it lasts, reset the channel
                    if self.channelResetSetting == 0 and self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                        createlist = False

                    if self.channelResetSetting > 0 and self.channelResetSetting < 4:
                        timedif = time.time() - self.lastResetTime

                        if self.channelResetSetting == 1 and timedif < (60 * 60 * 24):
                            createlist = False

                        if self.channelResetSetting == 2 and timedif < (60 * 60 * 24 * 7):
                            createlist = False

                        if self.channelResetSetting == 3 and timedif < (60 * 60 * 24 * 30):
                            createlist = False

                        if timedif < 0:
                            createlist = False

                    if self.channelResetSetting == 4:
                        createlist = False
            except:
                pass

        if createlist or needsreset:
            self.channels[channel - 1].isValid = False

            if makenewlist:
            
                try:#clean artwork folder
                    artworkLOC = (xbmc.translatePath(os.path.join(ART_LOC)))
                    self.logDebug("artworkLOC = " + str(artworkLOC))
                    shutil.rmtree(artworkLOC)
                    self.log("artwork cache folder cleaned")
                except:
                    pass

                try:#remove old playlist
                    os.remove(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')
                except:
                    pass

                append = False

                if createlist:
                    ADDON_SETTINGS.setSetting('LastResetTime', str(int(time.time())))

        if append == False:
            if chtype == 6 and chsetting2 == str(MODE_ORDERAIRDATE):
                self.channels[channel - 1].mode = MODE_ORDERAIRDATE

            # if there is no start mode in the channel mode flags, set it to the default
            if self.channels[channel - 1].mode & MODE_STARTMODES == 0:
                if self.startMode == 0:
                    self.channels[channel - 1].mode |= MODE_RESUME
                elif self.startMode == 1:
                    self.channels[channel - 1].mode |= MODE_REALTIME
                elif self.startMode == 2:
                    self.channels[channel - 1].mode |= MODE_RANDOM

        if ((createlist or needsreset) and makenewlist) or append:
            if self.background == False:
                self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding videos", '')

            if self.makeChannelList(channel, chtype, chsetting1, chsetting2, chsetting3, chsetting4, append) == True:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    returnval = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    self.channels[channel - 1].isValid = True

                    # Don't reset variables on an appending channel
                    if append == False:
                        self.channels[channel - 1].totalTimePlayed = 0
                        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', '0')

                        if needsreset:
                            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'False')
                            self.channels[channel - 1].isSetup = True

        self.runActions(RULES_ACTION_BEFORE_CLEAR, channel, self.channels[channel - 1])

        # Don't clear history when appending channels
        if self.background == False and append == False and self.myOverlay.isMaster:
            self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
            self.updateDialog.update(self.updateDialogProgress, "Loading channel " + str(channel), "clearing history", '')
            self.clearPlaylistHistory(channel)

        if append == False:
            self.runActions(RULES_ACTION_BEFORE_TIME, channel, self.channels[channel - 1])

            if self.channels[channel - 1].mode & MODE_ALWAYSPAUSE > 0:
                self.channels[channel - 1].isPaused = True

            if self.channels[channel - 1].mode & MODE_RANDOM > 0:
                self.channels[channel - 1].showTimeOffset = random.randint(0, self.channels[channel - 1].getTotalDuration())

            if self.channels[channel - 1].mode & MODE_REALTIME > 0:
                timedif = int(self.myOverlay.timeStarted) - self.lastExitTime
                self.channels[channel - 1].totalTimePlayed += timedif

            if self.channels[channel - 1].mode & MODE_RESUME > 0:
                self.channels[channel - 1].showTimeOffset = self.channels[channel - 1].totalTimePlayed
                self.channels[channel - 1].totalTimePlayed = 0

            while self.channels[channel - 1].showTimeOffset > self.channels[channel - 1].getCurrentDuration():
                self.channels[channel - 1].showTimeOffset -= self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)

        self.channels[channel - 1].name = self.getChannelName(chtype, chsetting1)

        if ((createlist or needsreset) and makenewlist) and returnval:
            self.runActions(RULES_ACTION_FINAL_MADE, channel, self.channels[channel - 1])
        else:
            self.runActions(RULES_ACTION_FINAL_LOADED, channel, self.channels[channel - 1])

        return returnval

        
    def clearPlaylistHistory(self, channel):
        self.log("clearPlaylistHistory")

        if self.channels[channel - 1].isValid == False:
            self.log("channel not valid, ignoring")
            return

        # if we actually need to clear anything
        if self.channels[channel - 1].totalTimePlayed > (60 * 60 * 24 * 2):
            try:
                fle = FileAccess.open(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', 'w')
            except:
                self.log("clearPlaylistHistory Unable to open the smart playlist", xbmc.LOGERROR)
                return

            flewrite = uni("#EXTM3U\n")
            tottime = 0
            timeremoved = 0

            for i in range(self.channels[channel - 1].Playlist.size()):
                tottime += self.channels[channel - 1].getItemDuration(i)

                if tottime > (self.channels[channel - 1].totalTimePlayed - (60 * 60 * 12)):
                    tmpstr = str(self.channels[channel - 1].getItemDuration(i)) + ','
                    tmpstr += self.channels[channel - 1].getItemTitle(i) + "//" + self.channels[channel - 1].getItemEpisodeTitle(i) + "//" + self.channels[channel - 1].getItemDescription(i) + "//" + self.channels[channel - 1].getItemgenre(i) + "//" + self.channels[channel - 1].getItemtimestamp(i) + "//" + self.channels[channel - 1].getItemLiveID(i)
                    tmpstr = uni(tmpstr)
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    tmpstr = uni(tmpstr) + uni('\n') + uni(self.channels[channel - 1].getItemFilename(i))
                    flewrite += uni("#EXTINF:") + uni(tmpstr) + uni("\n")
                else:
                    timeremoved = tottime

            fle.write(flewrite)
            fle.close()

            if timeremoved > 0:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == False:
                    self.channels[channel - 1].isValid = False
                else:
                    self.channels[channel - 1].totalTimePlayed -= timeremoved
                    # Write this now so anything sharing the playlists will get the proper info
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', str(self.channels[channel - 1].totalTimePlayed))


    def getChannelName(self, chtype, setting1):
        self.log('getChannelName ' + str(chtype))

        if len(setting1) == 0:
            return ''

        if chtype == 0:
            return self.getSmartPlaylistName(setting1)
        elif chtype == 1 or chtype == 2 or chtype == 5 or chtype == 6 or chtype == 12:
            return setting1
        elif chtype == 3:
            return setting1 + " TV"
        elif chtype == 4:
            return setting1 + " Movies"
        elif chtype == 7:
            if setting1[-1] == '/' or setting1[-1] == '\\':
                return os.path.split(setting1[:-1])[1]
            else:
                return os.path.split(setting1)[1]

        return ''


    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        #fle = xbmc.translatePath(fle)
        fle = fle

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("getSmartPlaylisyName Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return ''

        try:
            dom = parse(xml)
        except:
            self.log('getSmartPlaylistName Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log('getSmartPlaylistName return ' + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.log("Unable to get the playlist name.", xbmc.LOGERROR)
            return ''
    
    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel, chtype, setting1, setting2, setting3, setting4, append = False):
        self.log('makeChannelList, CHANNEL: ' + str(channel))
        israndom = False
        reverseOrder = False
        fileList = []

        if chtype == 7:
            fileList = self.createDirectoryPlaylist(setting1)
            israndom = True                    
     
        elif chtype == 8: # LiveTV
            self.log("Building LiveTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
            
            # HDhomerun #
            if setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "true":
                #If you're using a HDHomeRun Dual and want 1 Tuner assigned per instance of PseudoTV, 
                #this will ensure Master instance uses tuner0 and slave instance uses tuner1 *Thanks Blazin912*
                self.log("Building LiveTV using tuner0")
                setting2 = re.sub(r'\d/tuner\d',"0/tuner0",setting2)
            else:
                self.log("Building LiveTV using tuner1")
                setting2 = re.sub(r'\d/tuner\d',"1/tuner1",setting2)
            
            # Validate XMLTV Data #
            if setting3 != '':
                self.xmltv_ok(setting3)
            
            # Validate LiveTV Feed #
            if self.xmltvValid == True:
                #Override Check# 
                if REAL_SETTINGS.getSetting('Override_ok') == "true":
                    self.log("Overriding Stream Validation")
                    fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel) 
                else:
                
                    if setting2[0:4] == 'rtmp' or setting2[0:5] == 'rtmpe':#rtmp check
                        self.rtmpDump(setting2)  
                        if self.rtmpValid == True:   
                            fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel)    
                        else:
                            self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'RTMP invalid: ' + str(setting2))
                            return    
                    
                    elif setting2[0:4] == 'http':#http check     
                        self.url_ok(setting2) 
                        if self.urlValid == True: 
                            fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel)    
                        else:
                            self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'HTTP invalid: ' + str(setting2))
                            return    
                
                    elif setting2[0:6] == 'plugin':#plugin check    
                        self.plugin_ok(setting2)
                        if self.Pluginvalid == True:
                            fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel)    
                        else:
                            self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'PLUGIN invalid: ' + str(setting2))
                            return
                    
                    elif setting2[-4:] == 'strm':#strm check           
                        self.strm_ok(setting2)
                        if self.strmValid == True:
                            fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel) 
                            self.log('makeChannelList, Building STRM channel')
                
                    elif setting2[0:3] == 'pvr':#pvr check
                            fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel) 
                            self.log('makeChannelList, Building pvr channel')
                    
                    else:
                        fileList = self.buildLiveTVFileList(setting1, setting2, setting3, channel)   
            else:
                return
                
        elif chtype == 9: # InternetTV
            self.log("Building InternetTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
            
            #Override Check# 
            if REAL_SETTINGS.getSetting('Override_ok') == "true":
                self.log("Overriding Stream Validation")
                fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, channel)
            else:
            
                if setting2[0:4] == 'rtmp':#rtmp check
                    self.rtmpDump(setting2)
                    if self.rtmpValid == True:
                        fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, channel)
                    else:
                        self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'RTMP invalid: ' + str(setting2))
                        return
       
                elif setting2[0:4] == 'http':#http check                
                    self.url_ok(setting2)
                    if self.urlValid == True:
                        fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, channel)
                    else:
                        self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'HTTP invalid: ' + str(setting2))
                        return   
                
                elif setting2[0:6] == 'plugin':#plugin check                
                    self.plugin_ok(setting2)
                    if self.Pluginvalid == True:
                        fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, channel)
                    else:
                        self.log('makeChannelList, CHANNEL: ' + str(channel) + ', CHTYPE: ' + str(chtype), 'PLUGIN invalid: ' + str(setting2))
                        return
                
                elif setting2[-4:] == 'strm':#strm check           
                    self.strm_ok(setting2)
                    if self.strmValid == True:
                        fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, channel)
                        self.log('makeChannelList, Building STRM channel')
                
                elif setting2[0:3] == 'pvr':#pvr check
                    fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, channel)
                    self.log('makeChannelList, Building pvr channel')
                        
                        
        elif chtype == 10: # Youtube
            self.log("Building Youtube Channel " + setting1 + " using type " + setting2 + "...")
            fileList = self.createYoutubeFilelist(setting1, setting2, setting3, setting4, channel)                            
            
            if setting4 == '1':#RANDOM
                israndom = True  
            elif setting4 == '2':#REVERSE ORDER
                reverseOrder = True
            
        elif chtype == 11: # RSS/iTunes/feedburner/Podcast
            self.log("Building RSS Feed " + setting1 + " using type " + setting2 + "...")
            fileList = self.createRSSFileList(setting1, setting2, setting3, setting4, channel)                       
            
            if setting4 == '1':#RANDOM
                israndom = True  
            elif setting4 == '2':#REVERSE ORDER
                reverseOrder = True
        
        elif chtype == 13: # LastFM
            self.log("Last.FM " + setting1 + " using type " + setting2 + "...")
            fileList = self.lastFM(setting1, setting2, setting3, channel)   
            
        else:
            if chtype == 0:
                if FileAccess.copy(setting1, MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                    if FileAccess.exists(MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                        self.log("Unable to copy or find playlist " + setting1)
                        return False

                fle = MADE_CHAN_LOC + os.path.split(setting1)[1]
            else:
                fle = self.makeTypePlaylist(chtype, setting1, setting2)
            
            #fle = xbmc.translatePath(fle)
            fle = fle

            if len(fle) == 0:
                self.log('Unable to locate the playlist for channel ' + str(channel), xbmc.LOGERROR)
                return False

            try:
                xml = FileAccess.open(fle, "r")
            except:
                self.log("makeChannelList Unable to open the smart playlist " + fle, xbmc.LOGERROR)
                return False


            try:
                dom = parse(xml)
            except:
                self.log('makeChannelList Problem parsing playlist ' + fle, xbmc.LOGERROR)
                xml.close()
                return False

            xml.close()

            if self.getSmartPlaylistType(dom) == 'mixed':
                if REAL_SETTINGS.getSetting('commercials') != "0" or REAL_SETTINGS.getSetting('trailers') != "0":
                    self.log("makeChannelList, adding CTs to mixed...")
                    PrefileList = self.buildMixedFileList(dom, channel)
                    fileList = self.insertFiles(channel, PrefileList, 'mixed')
                else:
                    fileList = self.buildMixedFileList(dom, channel)

            elif self.getSmartPlaylistType(dom) == 'movies':
                if REAL_SETTINGS.getSetting('Movietrailers') == "true" and REAL_SETTINGS.getSetting('trailers') != "0":
                    self.log("makeChannelList, adding Trailers to movies...")
                    PrefileList = self.buildFileList(fle, channel)
                    fileList = self.insertFiles(channel, PrefileList, 'movies')
                else:
                    fileList = self.buildFileList(fle, channel)  
            
            elif self.getSmartPlaylistType(dom) == 'episodes':
                if REAL_SETTINGS.getSetting('bumpers') != "false" or REAL_SETTINGS.getSetting('commercials') != "0" or REAL_SETTINGS.getSetting('trailers') != "0":
                    self.log("makeChannelList, adding BCT's to episodes...")
                    PrefileList = self.buildFileList(fle, channel)
                    fileList = self.insertFiles(channel, PrefileList, 'episodes')
                else:
                    fileList = self.buildFileList(fle, channel)
            else:
                fileList = self.buildFileList(fle, channel)

            try:
                order = dom.getElementsByTagName('order')

                if order[0].childNodes[0].nodeValue.lower() == 'random':
                    israndom = True
            except:
                pass

        try:
            if append == True:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "r+")
                channelplaylist.seek(0, 2)
            else:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except:
            self.log('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
            return False

        if append == False:
            channelplaylist.write(uni("#EXTM3U\n"))

        if None == fileList or len(fileList) == 0:
            self.log("Unable to get information about channel " + str(channel), xbmc.LOGERROR)
            channelplaylist.close()
            return False

        if israndom:
            random.shuffle(fileList)
            
        if reverseOrder:
            fileList.reverse()

        if len(fileList) > 4096:
            fileList = fileList[:4096]

        fileList = self.runActions(RULES_ACTION_LIST, channel, fileList)
        self.channels[channel - 1].isRandom = israndom

        if append:
            if len(fileList) + self.channels[channel - 1].Playlist.size() > 4096:
                fileList = fileList[:(4096 - self.channels[channel - 1].Playlist.size())]
        else:
            if len(fileList) > 4096:
                fileList = fileList[:4096]

        # Write each entry into the new playlist
        for string in fileList:
            channelplaylist.write(uni("#EXTINF:") + uni(string) + uni("\n"))

        channelplaylist.close()
        self.log('makeChannelList return')
        return True

        
    def makeTypePlaylist(self, chtype, setting1, setting2):
        if chtype == 1:
            if len(self.networkList) == 0:
                self.fillTVInfo()
            return self.createNetworkPlaylist(setting1)
            
        elif chtype == 2:
            if len(self.studioList) == 0:
                self.fillMovieInfo()
            return self.createStudioPlaylist(setting1)
            
        elif chtype == 3:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            return self.createGenrePlaylist('episodes', chtype, setting1)
            
        elif chtype == 4:
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()
            return self.createGenrePlaylist('movies', chtype, setting1)
            
        elif chtype == 5:
            if len(self.mixedGenreList) == 0:
                if len(self.showGenreList) == 0:
                    self.fillTVInfo()

                if len(self.movieGenreList) == 0:
                    self.fillMovieInfo()

                self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
                self.mixedGenreList.sort(key=lambda x: x.lower())

            return self.createGenreMixedPlaylist(setting1)
            
        elif chtype == 6:
            if len(self.showList) == 0:
                self.fillTVInfo()
            return self.createShowPlaylist(setting1, setting2)    
            
        elif chtype == 12:
            if len(self.musicGenreList) == 0:
                self.fillMusicInfo()
            return self.createGenrePlaylist('songs', chtype, setting1)

            
    def createNetworkPlaylist(self, network):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Network_' + network + '.xsp')

        limit = AT_Limit[int(REAL_SETTINGS.getSetting('ATLimit'))]
        self.log('limit = ' + str(limit))
        
        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", self.getChannelName(1, network))
        network = network.lower()
        added = False

        for i in range(len(self.showList)):
            if self.threadPause() == False:
                fle.close()
                return ''

            if self.showList[i][1].lower() == network:
                theshow = self.cleanString(self.showList[i][0])
                fle.write('    <rule field="tvshow" operator="is">' + theshow + '</rule>\n')
                added = True

        self.writeXSPFooter(fle, limit, "random")
        fle.close()

        if added == False:
            return ''

        return flename


    def createShowPlaylist(self, show, setting2):
        order = 'random'

        limit = AT_Limit[int(REAL_SETTINGS.getSetting('ATLimit'))]
        self.log('limit = ' + str(limit))  
            
        try:
            setting = int(setting2)

            if setting & MODE_ORDERAIRDATE > 0:
                order = 'airdate'
        except:
            pass

        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Show_' + show + '_' + order + '.xsp')

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, 'episodes', self.getChannelName(6, show))
        show = self.cleanString(show)
        fle.write('    <rule field="tvshow" operator="is">' + show + '</rule>\n')
        self.writeXSPFooter(fle, limit, order)
        fle.close()
        return flename

    
    def fillMixedGenreInfo(self):
        if len(self.mixedGenreList) == 0:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()

            self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
            self.mixedGenreList.sort(key=lambda x: x.lower())

    
    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break

        return newlist
    
    
    def createGenreMixedPlaylist(self, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Mixed_' + genre + '.xsp')

        limit = AT_Limit[int(REAL_SETTINGS.getSetting('ATLimit'))]
        self.log('limit = ' + str(limit))

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        epname = os.path.basename(self.createGenrePlaylist('episodes', 3, genre))
        moname = os.path.basename(self.createGenrePlaylist('movies', 4, genre))
        self.writeXSPHeader(fle, 'mixed', self.getChannelName(5, genre))
        fle.write('    <rule field="playlist" operator="is">' + epname + '</rule>\n')
        fle.write('    <rule field="playlist" operator="is">' + moname + '</rule>\n')
        self.writeXSPFooter(fle, limit, "random")
        fle.close()
        return flename


    def createGenrePlaylist(self, pltype, chtype, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + pltype + '_' + genre + '.xsp')

        limit = AT_Limit[int(REAL_SETTINGS.getSetting('ATLimit'))]
        self.log('limit = ' + str(limit))

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, pltype, self.getChannelName(chtype, genre))
        genre = self.cleanString(genre)
        fle.write('    <rule field="genre" operator="is">' + genre + '</rule>\n')
        self.writeXSPFooter(fle, limit, "random")
        fle.close()
        return flename


    def createStudioPlaylist(self, studio):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Studio_' + studio + '.xsp')
 
        limit = AT_Limit[int(REAL_SETTINGS.getSetting('ATLimit'))]
        self.log('limit = ' + str(limit))

        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", self.getChannelName(2, studio))
        studio = self.cleanString(studio)
        fle.write('    <rule field="studio" operator="is">' + studio + '</rule>\n')
        self.writeXSPFooter(fle, limit, "random")
        fle.close()
        return flename


    def createDirectoryPlaylist(self, setting1):
        self.log("createDirectoryPlaylist " + setting1)
        fileList = []
        filecount = 0
        json_query = uni('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "files"}, "id": 1}' % ( self.escapeDirJSON(setting1),))

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "getting file list")

        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        thedir = ''

        if setting1[-1:1] == '/' or setting1[-1:1] == '\\':
            thedir = uni(os.path.split(setting1[:-1])[1])
        else:
            thedir = uni(os.path.split(setting1)[1])

        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break

            match = re.search('"file" *: *"(.*?)",', f)

            if match:
                if(match.group(1).endswith("/") or match.group(1).endswith("\\")):
                    fileList.extend(self.createDirectoryPlaylist(match.group(1).replace("\\\\", "\\")))
                else:
                    duration = self.videoParser.getVideoLength(match.group(1).replace("\\\\", "\\"))

                    if duration > 0:
                        filecount += 1

                        if self.background == False:
                            if filecount == 1:
                                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entry")
                            else:
                                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entries")

                        afile = uni(os.path.split(match.group(1).replace("\\\\", "\\"))[1])
                        afile, ext = os.path.splitext(afile)
                        afile = uni(unquote(afile))
                        tmpstr = uni(str(duration) + ',')
                        tmpstr += afile + "//" + thedir + "//" + 'Directory' + "////" + 'LiveID|'
                        tmpstr = uni(tmpstr[:500])
                        tmpstr = uni(tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\""))
                        tmpstr += uni("\n") + uni(match.group(1).replace("\\\\", "\\"))
                        fileList.append(tmpstr)

        if filecount == 0:
            self.logDebug(json_folder_detail)

        return fileList


    def writeXSPHeader(self, fle, pltype, plname):
        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="' + pltype + '">\n')
        plname = self.cleanString(plname)
        fle.write('    <name>' + plname + '</name>\n')
        fle.write('    <match>one</match>\n')


    def writeXSPFooter(self, fle, limit, order):
        if limit > 0:
            fle.write('    <limit>' + str(limit) + '</limit>\n')

        fle.write('    <order direction="ascending">' + order + '</order>\n')
        fle.write('</smartplaylist>\n')


    def writeFileList(self, channel, fileList):
        try:
            channelplaylist = open("channel_" + str(channel) + ".m3u", "w")
        except:
            self.Error('writeFileList: Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)

        # get channel name from settings
        channelplaylist.write("#EXTM3U\n")
        fileList = fileList[:500]
        # Write each entry into the new playlist
        string_split = []
        totalDuration = 0
        for string in fileList:
            # capture duration of final filelist to get total duration for channel
            string_split = string.split(',')
            totalDuration = totalDuration + int(string_split[0])
            # write line
            channelplaylist.write("#EXTINF:" + string + "\n")
        channelplaylist.close()
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_totalDuration", str(totalDuration))
        # copy to prestage to ensure there is always a prestage file available for the auto reset
        # this is to cover the use case where a channel setting has been changed 
        # after the auto reset time has expired resulting in a new channel being created
        # during the next start as well as a auto reset being triggered which moves
        # files from prestage to the cache directory

    
    def cleanString(self, string):
        newstr = uni(string)
        newstr = newstr.replace('&', '&amp;')
        newstr = newstr.replace('>', '&gt;')
        newstr = newstr.replace('<', '&lt;')
        return uni(newstr)

    
    def uncleanString(self, string):
        self.log("uncleanString")
        newstr = string
        newstr = newstr.replace('&amp;', '&')
        newstr = newstr.replace('&gt;', '>')
        newstr = newstr.replace('&lt;', '<')
        return uni(newstr)
               
            
    def fillMusicInfo(self, sortbycount = False):
        self.log("fillMusicInfo")
        self.musicGenreList = []
        json_query = uni('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"fields":["genre"]}, "id": 1}')
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding music", "reading music data")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.musicGenreList[:]
                return

            if USING_FRODO:
                match = re.search('"genre" *: *\[(.*?)\]', f)
            else:
                match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                if USING_FRODO:
                    genres = match.group(1).split(',')
                else:
                    genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.musicGenreList)):
                        if self.threadPause() == False:
                            del self.musicGenreList[:]
                            return
                            
                        itm = self.musicGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.musicGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.musicGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.musicGenreList.append(genre.strip('"').strip())
    
        if sortbycount:
            self.musicGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.musicGenreList.sort(key=lambda x: x.lower())

        if (len(self.musicGenreList) == 0):
            self.logDebug(json_folder_detail)

        self.log("found genres " + str(self.musicGenreList))
     
    
    def fillTVInfo(self, sortbycount = False):
        self.log("fillTVInfo")
        json_query = uni('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"fields":["studio", "genre"]}, "id": 1}')

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "reading TV data")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.networkList[:]
                del self.showList[:]
                del self.showGenreList[:]
                return

            if USING_FRODO:
                match = re.search('"studio" *: *\[(.*?)\]', f)
            else:
                match = re.search('"studio" *: *"(.*?)",', f)

            network = ''

            if match:
                if USING_FRODO:
                    network = (match.group(1).split(','))[0]
                else:
                    network = match.group(1)

                network = network.strip('"').strip()
                found = False

                for item in range(len(self.networkList)):
                    if self.threadPause() == False:
                        del self.networkList[:]
                        del self.showList[:]
                        del self.showGenreList[:]
                        return

                    itm = self.networkList[item]

                    if sortbycount:
                        itm = itm[0]

                    if itm.lower() == network.lower():
                        found = True

                        if sortbycount:
                            self.networkList[item][1] += 1

                        break

                if found == False and len(network) > 0:
                    if sortbycount:
                        self.networkList.append([network, 1])
                    else:
                        self.networkList.append(network)

            match = re.search('"label" *: *"(.*?)",', f)

            if match:
                show = match.group(1).strip()
                self.showList.append([show, network])

            if USING_FRODO:
                match = re.search('"genre" *: *\[(.*?)\]', f)
            else:
                match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                if USING_FRODO:
                    genres = match.group(1).split(',')
                else:
                    genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.showGenreList)):
                        if self.threadPause() == False:
                            del self.networkList[:]
                            del self.showList[:]
                            del self.showGenreList[:]
                            return

                        itm = self.showGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.showGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.showGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.showGenreList.append(genre.strip('"').strip())

        if sortbycount:
            self.networkList.sort(key=lambda x: x[1], reverse = True)
            self.showGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.networkList.sort(key=lambda x: x.lower())
            self.showGenreList.sort(key=lambda x: x.lower())

        if (len(self.showList) == 0) and (len(self.showGenreList) == 0) and (len(self.networkList) == 0):
            self.logDebug(json_folder_detail)

        self.log("found shows " + str(self.showList))
        self.log("found genres " + str(self.showGenreList))
        self.log("fillTVInfo return " + str(self.networkList))


    def fillMovieInfo(self, sortbycount = False):
        self.log("fillMovieInfo")
        studioList = []
        json_query = uni('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"fields":["studio", "genre"]}, "id": 1}')

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "reading movie data")

        json_folder_detail = self.sendJSON(json_query)
        self.logDebug(json_folder_detail)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.movieGenreList[:]
                del self.studioList[:]
                del studioList[:]
                break

            if USING_FRODO:
                match = re.search('"genre" *: *\[(.*?)\]', f)
            else:
                match = re.search('"genre" *: *"(.*?)",', f)

            if match:
                if USING_FRODO:
                    genres = match.group(1).split(',')
                else:
                    genres = match.group(1).split('/')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.movieGenreList)):
                        itm = self.movieGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.movieGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.movieGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.movieGenreList.append(genre.strip('"').strip())

            if USING_FRODO:
                match = re.search('"studio" *: *\[(.*?)\]', f)
            else:
                match = re.search('"studio" *: *"(.*?)"', f)

            if match:
                if USING_FRODO:
                    studios = match.group(1).split(',')
                else:
                    studios = match.group(1).split('/')

                for studio in studios:
                    curstudio = studio.strip('"').strip()
                    found = False

                    for i in range(len(studioList)):
                        if studioList[i][0].lower() == curstudio.lower():
                            studioList[i][1] += 1
                            found = True
                            break

                    if found == False and len(curstudio) > 0:
                        studioList.append([curstudio, 1])

        maxcount = 0

        for i in range(len(studioList)):
            if studioList[i][1] > maxcount:
                maxcount = studioList[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0

            for j in range(len(studioList)):
                if studioList[j][1] == i:
                    itemcount += 1

            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount

            counteditems += itemcount

        if sortbycount:
            studioList.sort(key=lambda x: x[1], reverse=True)
            self.movieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            studioList.sort(key=lambda x: x[0].lower())
            self.movieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(studioList)):
            if studioList[i][1] >= bestmatch:
                if sortbycount:
                    self.studioList.append([studioList[i][0], studioList[i][1]])
                else:
                    self.studioList.append(studioList[i][0])

        if (len(self.movieGenreList) == 0) and (len(self.studioList) == 0):
            self.logDebug(json_folder_detail)

        self.log("found genres " + str(self.movieGenreList))
        self.log("fillMovieInfo return " + str(self.studioList))


    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break

        self.log("makeMixedList return " + str(newlist))
        return newlist

    
    def buildLiveID(self, imdbid, tvdbid, sbManaged, cpManaged, dbid, type, Unaired):
        self.log("buildLiveID")
        LiveID = ''
        
        if imdbid != 0:
            IID = ('imdb_' + str(imdbid))
            LiveID = (IID + '|')
        else:
            LiveID = ('NA' + '|')

        if tvdbid != 0:
            TID = ('tvdb_' + str(tvdbid))
            LiveID = (LiveID + '|' + TID + '|')
        else:
            LiveID = (LiveID + '|' + 'NA' + '|')
                              
        if sbManaged == True:
            LiveID = (LiveID + '|' + 'SB' + '|')
        elif cpManaged == True:
            LiveID = (LiveID + '|' + 'CP' + '|')
        else:
            LiveID = (LiveID + '|' + 'NA' + '|')
        
        if dbid != 0:
            DID = ('dbid_' + str(dbid) + ',' + str(type))
            LiveID = (LiveID + '|' + DID + '|')
        elif Unaired == True:
            LiveID = (LiveID + '|' + 'NEW' + ',' + str(type) + '|')
        else:
            LiveID = (LiveID + '|' + 'OLD' + ',' + str(type) + '|')

        LiveID = LiveID.replace('||','|')
        LiveID = str(LiveID)
        self.logDebug('buildLiveID.LiveID = ' + LiveID)
        
        return LiveID
        
        
    def buildGenreLiveID(self, showtitle, type): ##return genre and LiveID by json
        #query GetTVShows/GetMovie for tv/movie: get title/genre, match title return genre...
        self.log("buildGenreLiveID")
        match = []
        TVtype = False
        MovieType = False
        genre = ''
        imdbid = 0
        tvdbid = 0
        dbid = 0
        
        try:
            if type == 'TV':
                json_query = uni('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":["title","year","genre","imdbnumber"]}, "id": 1}')
                if not self.cached_json_detailed_TV:
                    self.log('buildGenreLiveID, json_detail creating cache')
                    self.cached_json_detailed_TV = self.sendJSON(json_query)
                    json_detail = self.cached_json_detailed_TV
                    TVtype = True
                else:
                    json_detail = self.cached_json_detailed_TV
                    self.log('buildGenreLiveID, json_detail using cache')
                    TVtype = True
            else:
                json_query = uni('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":["title","year","genre","imdbnumber"]}, "id": 1}')
                if not self.cached_json_detailed_Movie:
                    self.log('buildGenreLiveID, json_detail creating cache')
                    self.cached_json_detailed_Movie = self.sendJSON(json_query)
                    json_detail = self.cached_json_detailed_Movie 
                    MovieType = True
                else:
                    json_detail = self.cached_json_detailed_Movie 
                    self.log('buildGenreLiveID, json_detail using cache')
                    MovieType = True
            
            file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
            showtitle = ('"title":"' + showtitle + '"')
            match = [s for s in file_detail if showtitle in s]
            match = match[0]
            genre = match.split('"],"imdbnumber":')[0]
            genre = genre.split('"genre":["', 1)[-1]
            genre = genre.split('","')[0]        
            
            if genre == '':
                genre = 'Unknown'
            
            if type == 'TV':
                dbid = match.split('tvshowid":', 1)[-1]
            else:
                dbid = match.split('movieid":', 1)[-1]
            
            dbid = dbid.split(',"')[0]
            
            if TVtype:
                tvdbid = match.split('","label":')[0]
                tvdbid = tvdbid.split('"],"', 1)[-1]
                tvdbid = tvdbid.split('imdbnumber":"', 1)[-1]
                tvdbid = (str(tvdbid))
                GenreLiveID = ( str(genre) + ',' + str(tvdbid) + ',' + str(dbid))
                
            elif MovieType:
                imdbid = match.split('","label":')[0]
                imdbid = imdbid.split('"],"', 1)[-1]
                imdbid = imdbid.split('imdbnumber":"', 1)[-1]
                imdbid = (str(imdbid))
                GenreLiveID = (str(genre) + ',' + str(imdbid) + ',' + str(dbid))
            
            self.log("buildGenreLiveID, GenreLiveID = " + str(GenreLiveID))
            return GenreLiveID
            
        except:
            return 'Unknown'
            self.log('buildGenreLiveID, GenreLiveID failed...')
    

    def buildFileList(self, dir_name, channel): ##fix music channel todo
        self.log("buildFileList")
        fileList = []
        seasoneplist = []
        filecount = 0
        imdbid = 0
        tvdbid = 0
        genre = ''
        cpManaged = False
        sbManaged = False
        json_query = uni('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "fields":["season","episode","playcount","duration","runtime","tagline","showtitle","album","artist","plot","plotoutline"]}, "id": 1}' % (self.escapeDirJSON(dir_name)))   

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "querying database")
        
        if REAL_SETTINGS.getSetting("tvdb.enabled") == "true" and REAL_SETTINGS.getSetting("tmdb.enabled") == "true":
            self.apis = True
            tvdbAPI = TVDB(REAL_SETTINGS.getSetting('tvdb.apikey'))
            t = tvdb_api.Tvdb()
            tmdbAPI = TMDB(REAL_SETTINGS.getSetting('tmdb.apikey'))
        else:
            self.apis = False
            
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break

            f = uni(f)
            match = re.search('"file" *: *"(.*?)",', f)
            istvshow = False

            if match:
                if(match.group(1).endswith("/") or match.group(1).endswith("\\")):
                    fileList.extend(self.buildFileList(match.group(1), channel))
                else:
                    f = self.runActions(RULES_ACTION_JSON, channel, f)
                    duration = re.search('"duration" *: *([0-9]*?),', f)

                    try:
                        dur = int(duration.group(1))
                    except:
                        self.log("Json Duration Failed, defaulting to 0")
                        dur = 0

                    # As a last resort (since it's not as accurate), use runtime
                    if dur == 0:
                        duration = re.search('"runtime" *: *([0-9]*?),', f)

                        try:
                            dur = int(duration.group(1))
                        except:
                            self.log("Json Duration Failed, defaulting to 0")
                            dur = 0

                    # If duration doesn't exist, try to figure it out
                    if dur == 0:
                        dur = self.videoParser.getVideoLength(uni(match.group(1)).replace("\\\\", "\\"))
                        
                    # Remove any file types that we don't want (ex. IceLibrary, ie. Strms)
                    if self.incIceLibrary == False:
                        if match.group(1).replace("\\\\", "\\")[-4:].lower() == 'strm':
                            dur = 0
 
                    try:
                        if dur > 0:
                            filecount += 1
                            seasonval = -1
                            epval = -1

                            if self.background == False:
                                if filecount == 1:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entry")
                                else:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "adding videos", "added " + str(filecount) + " entries")

                            title = re.search('"label" *: *"(.*?)"', f)
                            tmpstr = str(dur) + ','
                            showtitle = re.search('"showtitle" *: *"(.*?)"', f)
                            plot = re.search('"plot" *: *"(.*?)",', f)
                            plotoutline = re.search('"plotoutline" *: *"(.*?)",', f)
                            
                            if plot == None:
                                theplot = ""
                            else:
                                theplot = plot.group(1)
                            
                            try:
                                theplot = uni(self.trim(theplot, 300, '...'))
                            except:
                                self.log("Plot Trim failed")
                                theplot = uni(theplot[:300])
                            
                            # This is a TV show
                            if showtitle != None and len(showtitle.group(1)) > 0:
                                season = re.search('"season" *: *(.*?),', f)
                                episode = re.search('"episode" *: *(.*?),', f)
                                swtitle = title.group(1)
                                swtitle = swtitle.split('.', 1)[-1]
                                
                                try:
                                    seasonval = int(season.group(1))
                                    epval = int(episode.group(1))

                                    if self.showSeasonEpisode:
                                        swtitle = ('S' + ('0' if seasonval < 10 else '') + str(seasonval) + 'E' + ('0' if epval < 10 else '') + str(epval) + ' - '+ swtitle)
                                
                                    else:
                                        swtitle = (('0' if seasonval < 10 else '') + str(seasonval) + 'x' + ('0' if epval < 10 else '') + str(epval) + ' - '+ swtitle)
                                    
                                except:
                                    self.log("Season/Episode formating failed")
                                    seasonval = -1
                                    epval = -1
                                    
                                GenreLiveID = self.buildGenreLiveID(showtitle.group(1), 'TV')
                                self.logDebug('buildFileList.GenreLiveID.TV = ' + str(GenreLiveID))

                                if GenreLiveID != 'Unknown':
                                    GenreLiveID = GenreLiveID.split(',')
                                    genre = GenreLiveID[0]
                                    genre = str(genre)
                                    tvdbid = GenreLiveID[1]                     
                                    tvdbid = int(tvdbid)
                                    dbid = GenreLiveID[2]                     
                                    dbid = int(dbid) 
                                
                                    # Lookup IMDBID, 1st with tvdb, then with tvdb_api
                                    if self.apis == True and tvdbid > 0 and imdbid == 0:
                                        try:
                                            imdbid = t[showtitle.group(1)]['imdb_id']
                                            if imdbid == None:
                                                imdbid = 0
                                        except:
                                            self.log("IMDBID Lookup failed")
                                            pass
                                        if imdbid == 0:
                                            try:
                                                imdbid = tvdbAPI.getIMDBbyShowName(showtitle.group(1))
                                                if imdbid == None:
                                                    imdbid = 0
                                            except:
                                                imdbid = 0
                                                self.log('buildFileList, imdbid lookup failed')
                                   
                                        ## Correct Invalid IMDBID format   
                                        if imdbid != 0 and str(imdbid[0:2]) != 'tt':
                                            imdbid = ('tt' + str(imdbid))
                                        
                                        sbManaged = self.sbManaged(tvdbid)
                                    
                                    LiveID = self.buildLiveID(imdbid, tvdbid, sbManaged, cpManaged, dbid, 'tvshow', '')
                                    self.logDebug('buildFileList.LiveID = ' + str(LiveID))
                                           
                                    tmpstr = ascii(tmpstr)
                                    swtitle = ascii(swtitle)
                                    theplot = ascii(theplot)
                                    genre = ascii(genre)
                                    
                                    tmpstr += showtitle.group(1) + "//" + swtitle + "//" + theplot + "//" + genre + "////" + LiveID
                                    istvshow = True

                                else:                               
                                           
                                    tmpstr = ascii(tmpstr)
                                    swtitle = ascii(swtitle)
                                    theplot = ascii(theplot)
                                    genre = ascii(genre)
                                    
                                    tmpstr += showtitle.group(1) + "//" + swtitle + "//" + theplot + "//" + 'Unknown' + "////" + 'LiveID|'
                                    istvshow = True

                            else:
                                tmpstr += title.group(1) + "//"
                                album = re.search('"album" *: *"(.*?)"', f)
                                # showtitle.group(1)

                                # This is a movie
                                if album == None or len(album.group(1)) == 0:
                                    tagline = re.search('"tagline" *: *"(.*?)",', f)
                                    
                                    if tagline != None:
                                        tmpstr += tagline.group(1)
                                    
                                    GenreLiveID = self.buildGenreLiveID(title.group(1), 'Movie')
                                    self.logDebug('buildFileList.GenreLiveID.Movie = ' + str(GenreLiveID))
                                    
                                    if GenreLiveID != 'Unknown':
                                        GenreLiveID = (GenreLiveID.split(','))
                                        genre = GenreLiveID[0]
                                        genre = str(genre)
                                        tvdbid = 0
                                        imdbid = GenreLiveID[1]
                                        dbid = GenreLiveID[2]                     
                                        dbid = int(dbid) 
                                    
                                        # Lookup IMDBID, 1st with tvdb, then with tvdb_api
                                        if self.apis == True and imdbid == 0:
                                            try:
                                                movieInfo = tmdbAPI.getMovie(title.group(1), '')
                                                imdbid = movieInfo['imdb_id']
                                                if imdbid == None:
                                                    imdbid = 0
                                            except:
                                                pass
                                            self.log('buildFileList, imdbid movie lookup failed')
                                       
                                            ## Correct Invalid IMDBID format   
                                            if imdbid != 0 and str(imdbid[0:2]) != 'tt':
                                                imdbid = ('tt' + str(imdbid))

                                            cpManaged = self.cpManaged(title.group(1), imdbid)
                                        
                                        LiveID = self.buildLiveID(imdbid, tvdbid, sbManaged, cpManaged, dbid, 'movie', '')
                                        self.logDebug('buildFileList.LiveID = ' + str(LiveID))
                                                                            
                                        tmpstr = ascii(tmpstr)
                                        theplot = ascii(theplot)
                                        genre = ascii(genre)
                                        
                                        if (REAL_SETTINGS.getSetting('EPGcolor_MovieGenre') == "true" and REAL_SETTINGS.getSetting('EPGcolor_enabled') == "1"):
                                            tmpstr += "//" + theplot + "//" + genre + "////" + LiveID
                                        else:
                                            tmpstr += "//" + theplot + "//" + 'Movie' + "////" + LiveID
                                    else:
                                        tmpstr += "//" + theplot + "//" + 'Movie' + "////" + 'LiveID|'
                                else:  
                                    artist = re.search('"artist" *: *"(.*?)"', f)
                                    tmpstr += album.group(1) + "//" + artist.group(1) + "//" + 'Music' + "////" + 'LiveID|'

                            tmpstr = tmpstr
                            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                            tmpstr = tmpstr + '\n' + match.group(1).replace("\\\\", "\\")
                            
                            if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
                                seasoneplist.append([seasonval, epval, tmpstr])                        
                            else:
                                fileList.append(tmpstr)
                    except:
                        self.log('buildFileList, failed...')
                        pass
            else:
                continue

        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])

            for seepitem in seasoneplist:
                fileList.append(seepitem[2])

        if filecount == 0:
            self.logDebug(json_folder_detail)

        self.log("buildFileList return")
        return fileList


    def buildMixedFileList(self, dom1, channel):
        fileList = []
        self.log('buildMixedFileList')

        try:
            rules = dom1.getElementsByTagName('rule')
            order = dom1.getElementsByTagName('order')
        except:
            self.log('buildMixedFileList Problem parsing playlist ' + filename, xbmc.LOGERROR)
            xml.close()
            return fileList

        for rule in rules:
            rulename = rule.childNodes[0].nodeValue

            if FileAccess.exists(xbmc.translatePath('special://profile/playlists/video/') + rulename):
                FileAccess.copy(xbmc.translatePath('special://profile/playlists/video/') + rulename, MADE_CHAN_LOC + rulename)
                fileList.extend(self.buildFileList(MADE_CHAN_LOC + rulename, channel))
            else:
                fileList.extend(self.buildFileList(GEN_CHAN_LOC + rulename, channel))

        self.log("buildMixedFileList returning")
        return fileList

    
    def parseXMLTVDate(self, dateString):
        if dateString is not None:
            if dateString.find(' ') != -1:
                # remove timezone information
                dateString = dateString[:dateString.find(' ')]
            t = time.strptime(dateString, '%Y%m%d%H%M%S')
            return datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
        else:
            return None
    
    
    def buildLiveTVFileList(self, setting1, setting2, setting3, channel):
        showList = []
        seasoneplist = []
        showcount = 0  
        elements_parsed = 0
        xmltv = setting3
        title = ''
        description = ''
        subtitle = ''                
                        
        if REAL_SETTINGS.getSetting("tvdb.enabled") == "true" and REAL_SETTINGS.getSetting("tmdb.enabled") == "true":
            self.apis = True
            tvdbAPI = TVDB(REAL_SETTINGS.getSetting('tvdb.apikey'))
            t = tvdb_api.Tvdb()
            tmdbAPI = TMDB(REAL_SETTINGS.getSetting('tmdb.apikey'))
        else:
            self.apis = False
                        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Parsing LiveTV...")
            if REAL_SETTINGS.getSetting('Live.art.enable') == 'true' and self.apis == True:
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Parsing LiveTV & Enhancing Guide Data")
  
        if setting3 != None:
            f = FileAccess.open(self.xmlTvFile, "rb")

        context = ET.iterparse(f, events=("start", "end")) 
        event, root = context.next()
        inSet = False
        
        for event, elem in context:
            if self.threadPause() == False:
                del showList[:]
                break
                
            if event == "end":
                if elem.tag == "programme":
                    channel = elem.get("channel")
                    url = unquote(setting2)
                    if setting1 == channel:
                        inSet = True
                        title = elem.findtext('title')
                        try:
                            title = title.split("*")[0] #Remove "*" from title
                            Unaired = True
                        except:
                            Unaired = False
                            pass
                        description = elem.findtext("desc")
                        iconElement = elem.find("icon")
                        icon = None
                        if iconElement is not None:
                            icon = iconElement.get("src")
                        subtitle = elem.findtext("sub-title")
                        if not description:
                            if not subtitle:
                                description = title  
                            else:
                                description = subtitle  
                        if not subtitle:                        
                                subtitle = 'LiveTV'
                        ##################################
                        #Parse the category of the program
                        istvshow = True
                        movie = False
                        category = 'Unknown'
                        categories = ''
                        categoryList = elem.findall("category")
                        for cat in categoryList:
                            categories += ', ' + cat.text
                            if cat.text == 'Movie':
                                category = cat.text
                                movie = True
                                istvshow = False
                            elif cat.text == 'Sports':
                                category = cat.text
                            elif cat.text == 'Children':
                                category = 'Kids'
                            elif cat.text == 'Kids':
                                category = cat.text
                            elif cat.text == 'News':
                                category = cat.text
                            elif cat.text == 'Comedy':
                                category = cat.text
                            elif cat.text == 'Drama':
                                category = cat.text
                        
                        #Trim prepended comma and space (considered storing all categories, but one is ok for now)
                        categories = categories[2:]
                        
                        #If the movie flag was set, it should override the rest (ex: comedy and movie sometimes come together)
                        if movie:
                            category = 'Movie'
                        
                        self.logDebug("buildLiveTVFileList.PreEnhancedParse = " + title + ' - ' + subtitle + ' - ' + category)
                        self.logDebug("buildLiveTVFileList.PreEnhancedParse = " + description)
                        
                        #TVDB/TMDB Parsing    
                        dd_progid = ''
                        tvdbid = 0
                        imdbid = 0
                        dbid = 0
                        seasonNumber = 0
                        episodeNumber = 0
                        episodeDesc = ''
                        episodeName = ''
                        episodeGenre = ''
                        movieTitle = ''
                        movieYear = ''
                        plot = ''
                        tagline = ''
                        genres = '' 
                        LiveID = ''
                        type = ''
                        Unaired = False
                        sbManaged = False
                        cpManaged = False
                        ignore = False
                        
                        #filter unwanted ids by title
                        if title == ('Paid Programming') or subtitle == ('Paid Programming') or description == ('Paid Programming') or category == 'News' or category == 'Sports':
                            ignore = True
                                        
                        now = datetime.datetime.now()
                        stopDate = self.parseXMLTVDate(elem.get('stop'))
                        startDate = self.parseXMLTVDate(elem.get('start'))
                        
                        if (((now > startDate and now < stopDate) or (now < startDate)) and (ignore == False)):
                            #Enable Enhanced Parsing
                            if not movie and self.apis == True and REAL_SETTINGS.getSetting('EnhancedLiveTV') == 'true':
                                type = 'tvshow'
                                #Decipher the TVDB ID by using the Zap2it ID in dd_progid
                                episodeNumList = elem.findall("episode-num")
                                for epNum in episodeNumList:
                                    if epNum.attrib["system"] == 'dd_progid':
                                        dd_progid = epNum.text
                                        
                                #The Zap2it ID is the first part of the string delimited by the dot
                                #  Ex: <episode-num system="dd_progid">MV00044257.0000</episode-num>
                                dd_progid = dd_progid.split('.',1)[0]
                                try:
                                    tvdbid = tvdbAPI.getIdByZap2it(dd_progid)
                                    if tvdbid == None:
                                        tvdbid = 0
                                except:
                                    pass
                                
                                #Find TVDBID
                                if tvdbid == 0:
                                    try:
                                        tvdbid = int(t[title]['id'])
                                        if tvdbid == None:
                                            tvdbid = 0
                                    except:
                                        pass
                                    if tvdbid == 0:
                                        try:
                                            tvdbid = int(tvdbAPI.getIdByShowName(title))
                                            if tvdbid == None:
                                                tvdbid = 0
                                        except:
                                            pass

                                #Find IMDBID via TVDBID
                                if imdbid == 0:
                                    try:
                                        imdbid = t[title]['imdb_id']
                                        if imdbid == None:
                                            imdbid = 0
                                    except:
                                        pass
                                    if imdbid == 0:
                                        try:
                                            imdbid = tvdbAPI.getIMDBbyShowName(title)
                                            if imdbid == None:
                                                imdbid = 0
                                        except:
                                            pass

                                #Find TVDBID via IMDBID, Last chance lookup
                                if tvdbid == 0 and imdbid != 0 and imdbid[0:2] == 'tt':
                                    try:
                                        tvdbid = tvdbAPI.getIdByIMDB(imdbid)
                                        if tvdbid == None:
                                            tvdbid = 0
                                    except:
                                        pass

                                #Find Episode info by air date.
                                if tvdbid != 0:
                                    #Date element holds the original air date of the program
                                    airdateStr = elem.findtext('date')
                                    if airdateStr != None:
                                        try:
                                            #Change date format into the byAirDate lookup format (YYYY-MM-DD)
                                            t = time.strptime(airdateStr, '%Y%m%d')
                                            airDateTime = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                                            airdate = airDateTime.strftime('%Y-%m-%d')
                                            #Only way to get a unique lookup is to use TVDB ID and the airdate of the episode
                                            episode = ET.fromstring(tvdbAPI.getEpisodeByAirdate(tvdbid, airdate))
                                            episode = episode.find("Episode")
                                            seasonNumber = int(episode.findtext("SeasonNumber"))
                                            episodeNumber = int(episode.findtext("EpisodeNumber"))
                                            episodeDesc = episode.findtext("Overview")
                                            episodeName = episode.findtext("EpisodeName")
                                        except:
                                            pass
                                            
                                    #Find Episode info by subtitle (ie Episode Name).
                                    if subtitle != 'LiveTV':
                                        try:
                                            episode = t[title].search(subtitle, key = 'episodename')
                                            # Output example: [<Episode 01x01 - My First Day>]
                                            episode = str(episode[0])
                                            episode = episode.split('x')
                                            seasonNumber = int(episode[0].split('Episode ')[1])
                                            episodeNumber = int(episode[1].split(' -')[0])
                                        except:
                                            pass
                                    # Find Episode info by SeasonNum x EpisodeNum
                                    if (seasonNumber != 0 and episodeNumber != 0):
                                        try:
                                            episode = t[title][seasonNumber][episodeNumber]
                                            episodeName = episode['episodename']
                                            episodeDesc = episode['overview']
                                            episodeGenre = t[title]['genre']
                                            # Output ex. Comedy|Talk Show|
                                            episodeGenre = episodeGenre.split('|')[1]
                                        except:
                                            pass
                                    
                                    if episodeName:
                                        subtitle = episodeName
                                    if episodeDesc:
                                        description = episodeDesc
                                    if episodeGenre:
                                        category = episodeGenre
                                        
                                    sbManaged = self.sbManaged(tvdbid)

                            elif movie and REAL_SETTINGS.getSetting('EnhancedLiveTV') == 'true' and self.apis == True:
                                type = 'movie'
                                movieYear = elem.findtext('date')
                                movieTitle = title
                                try:
                                    #Date element holds the original air date of the program
                                    movieInfo = tmdbAPI.getMovie(movieTitle, movieYear)
                                    imdbid = movieInfo['imdb_id']
                                    plot = movieInfo['overview']
                                    tagline = movieInfo['tagline']
                                    genres = movieInfo['genres'][0]
                                    genres = str(genres)
                                    genres = genres.split(": u'")[1]
                                    genres = genres.split("'}")[0]
                                    if imdbid == None:
                                        imdbid = 0
                                except:
                                    pass

                                if tagline:
                                    subtitle = tagline
                                if plot:
                                    description = plot           
                                if genres:
                                    if (REAL_SETTINGS.getSetting('EPGcolor_enabled') == "1" and REAL_SETTINGS.getSetting('EPGcolor_MovieGenre') == "true"):
                                        category = genres
                                    else:
                                        category = 'Movie'
                                        
                                cpManaged = self.cpManaged(movieTitle, imdbid)
                            
                            title = ascii(title)
                            subtitle = ascii(subtitle)
                            description = ascii(description)

                            self.logDebug("buildLiveTVFileList.PostEnhancedParse = " + title + ' - ' + subtitle + ' - ' + category)
                            self.logDebug("buildLiveTVFileList.PostEnhancedParse = " + description)

                        if seasonNumber > 0:
                            seasonNumber = '%02d' % int(seasonNumber)
                            self.logDebug('title.seasonNumber = ' + title + ' - ' + str(seasonNumber))
                        
                        if episodeName > 0:
                            episodeNumber = '%02d' % int(episodeNumber)
                            self.logDebug('title.episodeNumber = ' + title + ' - ' + str(episodeNumber))  
                                                   
                        #Read the "new" boolean for this program
                        if elem.find("new") != None:
                            Unaired = True
                            title = (title + '*NEW*')
                        else:
                            Unaired = False                        
                        
                        description = description.replace("\n", "").replace("\r", "")
                        subtitle = subtitle.replace("\n", "").replace("\r", "")
                        
                        try:
                            description = uni(self.trim(description, 200, '...'))
                        except:
                            description = uni(description[:200])
                            
                        try:
                            subtitle = uni(self.trim(subtitle, 100, ''))
                        except:
                            subtitle = uni(subtitle[:100])
                            
                        genre = category
                        
                        LiveID = self.buildLiveID(imdbid, tvdbid, sbManaged, cpManaged, dbid, type, Unaired)
                        self.logDebug('LiveID = ' + LiveID)
                        
                        #skip old shows that have already ended
                        if now > stopDate:
                            self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + "  OLD: " + title)
                            self.logDebug("Unaired = " + str(Unaired) + ", tvdbid = " + str(tvdbid) + ", imdbid = " + str(imdbid) + ", seasonNumber = " + str(seasonNumber) + ", episodeNumber = " + str(episodeNumber) + ", category = " + str(category) + ", sbManaged = " + str(sbManaged) + ", cpManaged = " + str(cpManaged))         
                            continue
                        
                        #adjust the duration of the current show
                        if now > startDate and now < stopDate:
                            try:
                                dur = ((stopDate - startDate).seconds)
                                self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + "  NOW PLAYING: " + title + "  DUR: " + str(dur))
                                self.logDebug("Unaired = " + str(Unaired) + ", tvdbid = " + str(tvdbid) + ", imdbid = " + str(imdbid) + ", seasonNumber = " + str(seasonNumber) + ", episodeNumber = " + str(episodeNumber) + ", category = " + str(category) + ", sbManaged = " + str(sbManaged) + ", cpManaged = " + str(cpManaged))           
                            except:
                                dur = 3600  #60 minute default
                                self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + " - Error calculating show duration (defaulted to 60 min)")
                                raise
                        
                        #use the full duration for an upcoming show
                        if now < startDate:
                            try:
                                dur = (stopDate - startDate).seconds
                                self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + "  UPCOMING: " + title + "  DUR: " + str(dur))
                                self.logDebug("Unaired = " + str(Unaired) + ", tvdbid = " + str(tvdbid) + ", imdbid = " + str(imdbid) + ", seasonNumber = " + str(seasonNumber) + ", episodeNumber = " + str(episodeNumber) + ", category = " + str(category) + ", sbManaged = " + str(sbManaged) + ", cpManaged = " + str(cpManaged))          
                            except:
                                dur = 3600  #60 minute default
                                self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + " - Error calculating show duration (default to 60 min)")
                                raise

                        if REAL_SETTINGS.getSetting('EnhancedLiveTV') == 'true' and self.apis == True:#Enhanced tmpstr
                            
                            if not movie: #TV
                                if self.showSeasonEpisode:
                                    episodetitle = ('S' + ('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'E' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ str(subtitle))
                                else:
                                    episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ str(subtitle))
                                
                                if str(episodetitle[0:6]) == 'S00E00':
                                    episodetitle = episodetitle.split("- ", 1)[-1]
                                    
                                tmpstr = str(dur) + ',' + title + "//" + episodetitle + "//" + description + "//" + genre + "//" + str(startDate) + "//" + LiveID + '\n' + url
                            
                            else: #Movie
                                tmpstr = str(dur) + ',' + title + "//" + subtitle + "//" + description + "//" + genre + "//" + str(startDate) + "//" + LiveID + '\n' + url
                        
                        else: #Default Playlist
                                
                            tmpstr = str(dur) + ',' + title + "//" + subtitle + "//" + description + "//" + genre + "//" + str(startDate) + "//" + 'LiveID|' + '\n' + url       
                        
                        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                        showList.append(tmpstr)

                    else:
                        if inSet == True:
                            self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + "  DONE")
                            break
                    showcount += 1
                
            root.clear()
                
        self.logDebug("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + ' "' + str(showcount) + 'SHOWS FOUND"')   
        if showcount == 0:
            self.log("buildLiveTVFileList, CHANNEL: " + str(self.settingChannel) + " 0 SHOWS FOUND")
        
        return showList

    
    def buildInternetTVFileList(self, setting1, setting2, setting3, setting4, channel):
        self.log('buildInternetTVFileList')
        showList = []
        seasoneplist = []
        showcount = 0
            
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Building InternetTV")
   
        try:
            self.ninstance = xbmc.translatePath(os.path.join(Globals.SETTINGS_LOC, 'settings.xml'))
        except:
            self.log("buildInternetTVFileList, Could not find settings.xml. Run configuration first...")
            return   
            
        f = open(self.ninstance, "rb")
        context = ET.iterparse(f, events=("start", "end"))

        event, root = context.next()
     
        inSet = False
        for event, elem in context:
            if self.threadPause() == False:
                del showList[:]
                break
                
            if event == "end":
                if setting1 >= 1:
                    inSet = True
                    title = setting3
                    url = unquote(setting2)
                    description = setting4
                    iconElement = elem.find("icon")
                    icon = None
                    if iconElement is not None:
                        icon = iconElement.get("src")
                    if not description:
                        if not subtitle:
                            description = title
                        else:
                            description = subtitle 
                    istvshow = True

                    if setting1 >= 1:
                        try:
                            dur = setting1
                            self.log("buildInternetTVFileList, CHANNEL: " + str(self.settingChannel) + ", " + title + "  DUR: " + str(dur))
                        except:
                            dur = 5400  #90 minute default
                            self.log("buildInternetTVFileList, CHANNEL: " + str(self.settingChannel) + " - Error calculating show duration (defaulted to 90 min)")
                            raise

                    tmpstr = str(dur) + ',' + title + "//" + "InternetTV" + "//" + description + "//" 'InternetTV' + "////" + 'LiveID|' + '\n' + url
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")

                    showList.append(tmpstr)

                showcount += 1
                    
            root.clear()

        return showList

        
    def createYoutubeFilelist(self, setting1, setting2, setting3, setting4, channel):
        showList = []
        seasoneplist = []
        showcount = 0   
        limit = 0
        stop = 0
        global youtube
        youtube = ''

        if setting3 == '':
            limit = 50
            self.log("createYoutubeFilelist, Using Global Parse-limit " + str(limit))
        else:
            limit = int(setting3)
            self.log("createYoutubeFilelist, Overriding Global Parse-limit to " + str(limit))
            
        if setting2 == '2':
            stop = 2
        else:
            stop = (limit / 25)

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Parsing Youtube")
        
        inSet = False
        startIndex = 1
        for x in range(stop):    
            if self.threadPause() == False:
                del showList[:]
                break

            if setting2 == '1': #youtubechannel
                self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + ", Youtube Channel" + ", Limit = " + str(limit))
                youtubechannel = 'http://gdata.youtube.com/feeds/api/users/' +setting1+ '/uploads?start-index=' +str(startIndex)+ '&max-results=25'
                youtube = youtubechannel
            elif setting2 == '2': #youtubeplaylist 
                self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + ", Youtube Playlist" + ", Limit = " + str(limit))
                youtubeplaylist = 'https://gdata.youtube.com/feeds/api/playlists/' +setting1+ '?start-index=1'
                youtube = youtubeplaylist                        
            elif setting2 == '3': #youtubesubscript 
                self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + ", Youtube Subscription" + ", Limit = " + str(limit))
                youtubesubscript = 'http://gdata.youtube.com/feeds/api/users/' +setting1+ '/newsubscriptionvideos?start-index=' +str(startIndex)+ '&max-results=25'
                youtube = youtubesubscript      
            
            feed = feedparser.parse(youtube)
            self.logDebug('createYoutubeFilelist, youtube = ' + str(youtube))                
            startIndex = startIndex + 25
                
            for i in range(len(feed['entries'])):
                try:
                    showtitle = feed.channel.author_detail['name']
                    showtitle = showtitle.replace(":", "")
                    try:
                        genre = (feed.entries[0].tags[1]['term'])
                    except:
                        self.log("createYoutubeFilelist, Invalid genre")
                        genre = 'Youtube'
                        pass
                    
                    try:
                        thumburl = feed.entries[i].media_thumbnail[0]['url']
                    except:
                        self.log("createYoutubeFilelist, Invalid media_thumbnail")
                        pass 
        
                    #Time when the episode was published
                    time = (feed.entries[i].published_parsed)
                    time = str(time)
                    time = time.replace("time.struct_time", "")            
                    
                    #Some channels release more than one episode daily.  This section converts the mm/dd/hh to season=mm episode=dd+hh
                    showseason = [word for word in time.split() if word.startswith('tm_mon=')]
                    showseason = str(showseason)
                    showseason = showseason.replace("['tm_mon=", "")
                    showseason = showseason.replace(",']", "")
                    showepisodenum = [word for word in time.split() if word.startswith('tm_mday=')]
                    showepisodenum = str(showepisodenum)
                    showepisodenum = showepisodenum.replace("['tm_mday=", "")
                    showepisodenum = showepisodenum.replace(",']", "")
                    showepisodenuma = [word for word in time.split() if word.startswith('tm_hour=')]
                    showepisodenuma = str(showepisodenuma)
                    showepisodenuma = showepisodenuma.replace("['tm_hour=", "")
                    showepisodenuma = showepisodenuma.replace(",']", "")
                
                    eptitle = feed.entries[i].title
                    eptitle = re.sub('[!@#$/:]', '', eptitle)
                    eptitle = uni(eptitle)
                    eptitle = re.sub("[\W]+", " ", eptitle.strip()) 
                    
                    try:
                        showtitle = uni(self.trim(showtitle, 100, ''))
                    except:
                        showtitle = uni(showtitle[:100])
                   
                    try:
                        eptitle = uni(self.trim(eptitle, 100, ''))
                    except:
                        eptitle = uni(eptitle[:100])  
                        
                    summary = feed.entries[i].summary
                    summary = uni(summary)
                    summary = re.sub("[\W]+", " ", summary.strip())                        
                    
                    try:
                        summary = uni(self.trim(summary, 300, '...'))
                    except:
                        summary = uni(summary[:300])
                        
                    # try:
                        # runtime = feed.entries[i].media_content[0]['duration']
                        # self.log("createYoutubeFilelist, Invalid media_content_duration")
                    # except:
                        # runtime = feed.entries[i].yt_duration['seconds']
                        # self.log("createYoutubeFilelist, Invalid yt_duration")
                    # else:
                        # pass
                        
                    runtime = feed.entries[i].yt_duration['seconds']
                    self.logDebug('createYoutubeFilelist, runtime = ' + str(runtime))
                    runtime = int(runtime)
                    # runtime = round(runtime/60.0)
                    # runtime = int(runtime)
                    
                    if runtime >= 1:
                        duration = runtime
                    else:
                        duration = 90
                        self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + " - Error calculating show duration (defaulted to 90 min)")
                    
                    # duration = round(duration*60.0)
                    self.logDebug('createYoutubeFilelist, duration = ' + str(duration))
                    duration = int(duration)
                    url = feed.entries[i].media_player['url']
                    self.logDebug('createYoutubeFilelist, url.1 = ' + str(url))
                    
                    if setting2 == '1':  
                        url = url.replace("https://", "").replace("http://", "").replace("www.youtube.com/watch?v=", "").replace("&feature=youtube_gdata_player", "")     
                    elif setting2 == '2':                    
                        url = url.replace("https://", "").replace("http://", "").replace("www.youtube.com/watch?v=", "").replace("&feature=youtube_gdata_player", "").replace("?version=3&f=playlists&app=youtube_gdata", "")
                    elif setting2 == '3':
                        url = url.replace("https://", "").replace("http://", "").replace("www.youtube.com/watch?v=", "").replace("&feature=youtube_gdata_player", "").replace("?version=3&f=newsubscriptionvideos&app=youtube_gdata", "")
                    
                    self.logDebug('createYoutubeFilelist, url.2 = ' + str(url))
                    
                    # Build M3U
                    if setting2 == '1'or setting2 == '2'or setting2 == '3':
                        inSet = True
                        istvshow = True
                        tmpstr = str(duration) + ',' + eptitle + '//' + "Youtube - " + showtitle + "//" + summary + "//" + genre + "////" + 'LiveID|' + '\n' + 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid='+url
                        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                        self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + ", " + eptitle + "  DUR: " + str(duration))
                        showList.append(tmpstr)

                    else:
                        if inSet == True:
                            self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + ", DONE")
                            break                    
                except:
                    pass
        
        return showList


    def createRSSFileList(self, setting1, setting2, setting3, setting4, channel):
        self.log("createRSSFileList ")
        showList = []
        seasoneplist = []
        showcount = 0
        limit = 0
        stop = 0 
        runtime = 0
        genre = ''
        
        if setting3 == '':
            limit = 50
            self.log("createRSSFileList, Using Global Parse-limit " + str(limit))
        else:
            limit = int(setting3)
            self.log("createRSSFileList, Overiding Global Parse-limit to " + str(limit))    
            
        if setting2 == '1':
            stop = 1
        else:
            stop = (limit / 25)
               
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Parsing RSS")

        inSet = False
        startIndex = 1
        for x in range(stop):    
            if self.threadPause() == False:
                del showList[:]
                break
                
            if setting2 == '1': #RSS
                self.log("createRSSFileList, RSS " + ", Limit = " + str(limit))
                rssfeed = setting1
                feed = feedparser.parse(rssfeed)

                for i in range(len(feed['entries'])):
                    try:
                        showtitle = feed.channel.title
                        showtitle = showtitle.replace(":", "")
                        eptitle = feed.entries[i].title
                        eptitle = eptitle.replace("/", "-")
                        eptitle = eptitle.replace(":", " ")
                        eptitle = eptitle.replace("\"", "")
                        eptitle = eptitle.replace("?", "")
                        
                        try:
                            showtitle = uni(self.trim(showtitle, 100, ''))
                        except:
                            showtitle = uni(showtitle[:100])
                       
                        try:
                            eptitle = uni(self.trim(eptitle, 100, ''))
                        except:
                            eptitle = uni(eptitle[:100])
                            
                        if 'author_detail' in feed.entries[i]:
                            studio = feed.entries[i].author_detail['name']  
                        else:
                            self.log("createRSSFileList, Invalid author_detail")  
                            
                        if 'media_thumbnail' in feed.entries[i]:
                            thumburl = feed.entries[i].media_thumbnail[0]['url']
                        else:
                            self.log("createRSSFileList, Invalid media_thumbnail")

                        if not '<p>' in feed.entries[i].summary_detail.value:
                            epdesc = feed.entries[i]['summary_detail']['value']
                            head, sep, tail = epdesc.partition('<div class="feedflare">')
                            epdesc = head
                        else:
                            epdesc = feed.entries[i]['subtitle']
                        
                        if epdesc == '':
                            epdesc = eptitle
                            
                        try:
                            epdesc = uni(self.trim(epdesc, 300, '...'))
                        except:
                            epdesc = uni(epdesc[:300])
                        
                        if 'media_content' in feed.entries[i]:
                            url = feed.entries[i].media_content[0]['url']
                        else:
                            url = feed.entries[i].links[1]['href']
                        
                        try:
                            runtimex = feed.entries[i]['itunes_duration']
                        except:
                            runtimex = 1350
                            pass
                        
                        try:
                            summary = feed.channel.subtitle
                            summary = summary.replace(":", "")
                        except:
                            pass
                        
                        if feed.channel.has_key("tags"):
                            genre = feed.channel.tags[0]['term']
                            genre = str(genre)
                        else:
                            genre = "RSS"
                        
                        try:
                            time = (feed.entries[i].published_parsed)
                            time = str(time)
                            time = time.replace("time.struct_time", "")
                        
                            showseason = [word for word in time.split() if word.startswith('tm_mon=')]
                            showseason = str(showseason)
                            showseason = showseason.replace("['tm_mon=", "")
                            showseason = showseason.replace(",']", "")
                            showepisodenum = [word for word in time.split() if word.startswith('tm_mday=')]
                            showepisodenum = str(showepisodenum)
                            showepisodenum = showepisodenum.replace("['tm_mday=", "")
                            showepisodenum = showepisodenum.replace(",']", "")
                            showepisodenuma = [word for word in time.split() if word.startswith('tm_hour=')]
                            showepisodenuma = str(showepisodenuma)
                            showepisodenuma = showepisodenuma.replace("['tm_hour=", "")
                            showepisodenuma = showepisodenuma.replace(",']", "")  
                            
                            if len(runtimex) > 4:
                                runtime = runtimex.split(':')[-2]
                                runtimel = runtimex.split(':')[-3]
                                runtime = int(runtime)
                                runtimel = int(runtimel)
                                runtime = runtime + (runtimel*60)
                            if not len(runtimex) > 4:
                                runtimex = int(runtimex)
                                runtime = round(runtimex/60.0)
                                runtime = int(runtime)
                        except:
                            pass
                        
                        if runtime >= 1:
                            duration = runtime
                        else:
                            duration = 90
                            
                        duration = round(duration*60.0)
                        duration = int(duration)
                        
                        # Build M3U
                        if setting2 == '1':
                            inSet = True
                            istvshow = True
                            
                            if 'http://www.youtube.com' in url:
                                url = url.replace("http://www.youtube.com/watch?v=", "").replace("&amp;amp;feature=youtube_gdata", "")
                            
                            tmpstr = str(duration) + ',' + eptitle + "//" + "RSS - " + showtitle + "//" + epdesc + "//" + genre + "////" + 'LiveID|' + '\n' + url + '\n'
                            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                            self.log("createRSSFileList, CHANNEL: " + str(self.settingChannel) + ", " + eptitle + "  DUR: " + str(duration))
                            showList.append(tmpstr)

                        else:
                            if inSet == True:
                                self.log("createRSSFileList, CHANNEL: " + str(self.settingChannel) + ", DONE")
                                break         
                    except:
                        pass

        return showList

     
    def lastFM(self, setting1, setting2, setting3, channel):
        self.log('LastFM') #Last.fm Music Videos 
        # Sample xml output:
        # <clip>
            # <artist url="http://www.last.fm/music/Tears+for+Fears">Tears for Fears</artist>
            # <track url="http://www.last.fm/music/Tears+for+Fears/_/Everybody+Wants+to+Rule+the+World">Everybody Wants to Rule the World</track>
            # <url>http://www.youtube.com/watch?v=ST86JM1RPl0&amp;feature=youtube_gdata_player</url>
            # <duration>191</duration>
            # <thumbnail>http://i.ytimg.com/vi/ST86JM1RPl0/0.jpg</thumbnail>
            # <rating max="5">4.9660454</rating>
            # <stats hits="1" misses="4" />
        # </clip>
        showList = [] 
        api = setting1
        limit = 0
        duration = 0
        artist = ''
        track = ''
        url = ''
        thumburl = ''
        rating = 0
        eptitle = ''
        epdesc = ''
        
        if setting3 == '':
            limit = 50
            self.log("LastFM, Using Global Parse-limit " + str(limit))
        else:
            limit = int(setting3)
            self.log("LastFM, Overriding Global Parse-limit to " + str(limit))
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Parsing Last.FM")
        
        inSet = False
        for i in range(limit):
            if self.threadPause() == False:
                del fileList[:]
                break
            try:
                file = urllib2.urlopen(api)
                self.log('file' + str(file))
                data = file.read()
                self.log('data' + str(data))
                file.close()
                dom = parseString(data)

                xmlartist = dom.getElementsByTagName('artist')[0].toxml()
                artist = xmlartist.replace('<artist>','').replace('</artist>','')
                artist = artist.rsplit('>', -1)
                artist = artist[1]
                # artist = str(artist)
                artist = self.uncleanString(artist)

                xmltrack = dom.getElementsByTagName('track')[0].toxml()
                track = xmltrack.replace('<track url>','').replace('</track>','')
                track = track.rsplit('>', -1)
                track = track[1]
                # track = str(track)
                track = self.uncleanString(track)

                xmlurl = dom.getElementsByTagName('url')[0].toxml()
                url = xmlurl.replace('<url>','').replace('</url>','')  
                url = url.replace("https://", "").replace("http://", "").replace("www.youtube.com/watch?v=", "").replace("&feature=youtube_gdata_player", "")     

                xmlduration = dom.getElementsByTagName('duration')[0].toxml()
                duration = xmlduration.replace('<duration>','').replace('</duration>','')

                xmlthumbnail = dom.getElementsByTagName('thumbnail')[0].toxml()
                thumburl = xmlthumbnail.replace('<thumbnail>','').replace('</thumbnail>','')

                xmlrating = dom.getElementsByTagName('rating')[0].toxml()
                rating = xmlrating.replace('<rating>','').replace('</rating>','')
                rating = rating.rsplit('>', -1)
                rating = rating[1]            
                eptitle = uni(artist + ' - ' + track)
                epdesc = uni('Rated ' + rating + '/5.0')
                    
            except:
                self.log("User hasn't listened to enough artists on Last.fm yet. Using Default User...")
                api = 'http://api.tv.timbormans.com/user/por/topartists.xml'
                file = urllib2.urlopen(api)
                data = file.read()
                file.close()
                dom = parseString(data)
                continue
            
            if setting2 == '1':
                inSet = True
                istvshow = True
                url = 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid='+url
                tmpstr = str(duration) + ',' + eptitle + "//" + "Last.FM" + "//" + epdesc + "//" + 'Music' + "////" + 'LiveID|' + '\n' + url + '\n'
                tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                self.log("LastFM, CHANNEL: " + str(self.settingChannel) + ", " + eptitle + "  DUR: " + str(duration))
                
                showList.append(tmpstr)                    
            else:
                if inSet == True:
                    self.log("LastFM, CHANNEL: " + str(self.settingChannel) + ", DONE")
                    break    
        
        return showList

    # Run rules for a channel
    def runActions(self, action, channel, parameter):
        self.log("runActions " + str(action) + " on channel " + str(channel))
        if channel < 1:
            return

        self.runningActionChannel = channel
        index = 0

        for rule in self.channels[channel - 1].ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "processing rule " + str(index + 1), '')

                parameter = rule.runAction(action, self, parameter)

            index += 1

        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def threadPause(self):
        if threading.activeCount() > 1:
            while self.threadPaused == True and self.myOverlay.isExiting == False:
                time.sleep(self.sleepTime)

            # This will fail when using config.py
            try:
                if self.myOverlay.isExiting == True:
                    self.log("IsExiting")
                    return False
            except:
                pass

        return True


    def escapeDirJSON(self, dir_name):
        mydir = uni(dir_name)

        if (mydir.find(":")):
            mydir = mydir.replace("\\", "\\\\")

        return mydir


    def getSmartPlaylistType(self, dom):
        self.log('getSmartPlaylistType')

        try:
            pltype = dom.getElementsByTagName('smartplaylist')
            return pltype[0].attributes['type'].value
        except:
            self.log("Unable to get the playlist type.", xbmc.LOGERROR)
            return ''
    
  
    def strm_ok(self, setting2):
        self.log("strm_ok, " + str(setting2))
        self.strmFailed = False
        self.strmValid = False
        rtmpOK = True
        urlOK = True
        pluginOK = True
        lines = ''
        
        if int(REAL_SETTINGS.getSetting('Offair')) == 0:
            fallback = str(REAL_SETTINGS.getSetting('Offair_Local'))
        else:
            fallback = str(REAL_SETTINGS.getSetting('Offair_Youtube'))

        try:
            f = FileAccess.open(setting2, "r")
            linesLST = f.readlines()
            self.log("strm_ok.Lines = " + str(linesLST))
            f.close()

            for i in range(len(set(linesLST))):
                lines = linesLST[i]
                if lines[0:4] == 'rtmp':#rtmp check
                    rtmpOK = self.rtmpDump(lines)
                    self.logDebug("strm_ok.Lines rtmp = " + str(lines))
                    #if invalid delete line
                elif lines[0:4] == 'http':#http check                
                    urlOK = self.url_ok(lines)
                    self.logDebug("strm_ok.Lines http = " + str(lines))
                    #if invalid delete line
                elif lines[0:6] == 'plugin':#plugin check                
                    pluginOK = self.plugin_ok(lines)
                    self.logDebug("strm_ok.Lines plugin = " + str(lines))
                elif lines[0:9] == 'hdhomerun':#hdhomerun check 
                    self.logDebug("strm_ok.Lines hdhomerun = " + str(lines))
                    self.strmValid = True
                    return
                
                if rtmpOK == False or urlOK == False or pluginOK == False:
                    self.strmFailed = True
                
            if self.strmFailed == True:
                self.log("strm_ok, failed strmCheck; writing fallback video")
                f = FileAccess.open(setting2, "w")
                for i in range(len(linesLST)):
                    lines = linesLST[i]
                    if lines != fallback:
                        f.write(lines + '\n')
                    self.logDebug("strm_ok, file write lines = " + str(lines))
                f.write(fallback)
                f.close()
                self.strmValid = True           
        except:
            pass
            
   
    def xmltv_ok(self, setting3):
        self.xmltvValid = False
        self.xmlTvFile = ''
        self.log("setting3 = " + str(setting3))
        
        # if setting3 == 'ustvnow':
            # self.log("xmltv_ok, testing " + str(setting3))
            # url = 'http://' # USTVnow XMLTV list
            # url_bak = 'http://' # USTVnow BACKUP XMLTV list
            # try: 
                # urllib2.urlopen(url)
                # self.log("INFO: URL Connected...")
                # self.xmltvValid = True
                # self.xmlTvFile = url 
            # except urllib2.URLError as e:
                # urllib2.urlopen(url_bak)
                # self.log("INFO: URL_BAK Connected...")
                # self.xmltvValid = True
                # self.xmlTvFile = url_bak
            # except urllib2.URLError as e:
                # if "Errno 10054" in e:
                    # raise
                # else:                
                    # self.log("ERROR: Problem accessing the DNS. USTVnow XMLTV URL NOT VALiD, ERROR: " + str(e))
                    # self.xmltvValid = False

        if setting3 != '':
            self.xmlTvFile = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('xmltvLOC'), str(setting3) +'.xml'))
            self.log("xmltv_ok, testing " + str(self.xmlTvFile))
            try:
                FileAccess.exists(self.xmlTvFile)
                # channelplaylist.seek(0, 2)#todo add open, seek to verify info inside xmltv.xml
                self.log("INFO: XMLTV Data Found...")
                self.xmltvValid = True
            except IOError as e:
                self.xmltvValid = False
                self.log("ERROR: Problem accessing the DNS. " + str(setting3) +".xml XMLTV file NOT FOUND, ERROR: " + str(e))

        self.log("xmltvValid = " + str(self.xmltvValid))
                    
        
    def rtmpDump(self, stream):
        self.rtmpValid = False
        url = unquote(stream)
        
        OSplat = REAL_SETTINGS.getSetting('os')
        if OSplat == '0':
            OSpath = 'androidarm/rtmpdump'
        elif OSplat == '1':
            OSpath = 'android86/rtmpdump'
        elif OSplat == '2':
            OSpath = 'atv1linux/rtmpdump'
        elif OSplat == '3':
            OSpath = 'atv1stock/rtmpdump'
        elif OSplat == '4':
            OSpath = 'atv2/rtmpdump'
        elif OSplat == '5':
            OSpath = 'ios/rtmpdump'
        elif OSplat == '6':
            OSpath = 'linux32/rtmpdump'
        elif OSplat == '7':
            OSpath = 'linux64/rtmpdump'
        elif OSplat == '8':
            OSpath = 'mac32/rtmpdump'
        elif OSplat == '9':
            OSpath = 'mac64/rtmpdump'
        elif OSplat == '10':
            OSpath = 'pi/rtmpdump'
        elif OSplat == '11':
            OSpath = 'win/rtmpdump.exe'
        elif OSplat == '12':
            OSpath = '/usr/bin/rtmpdump'
            
        RTMPDUMP = xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'lib', 'rtmpdump', OSpath))
        self.log("RTMPDUMP = " + RTMPDUMP)
        assert os.path.isfile(RTMPDUMP)
        
        if "playpath" in url:
            url = re.sub(r'playpath',"-y playpath",url)
            self.log("playpath url = " + str(url))
            command = [RTMPDUMP, '-B 1', '-m 2', '-r', url,'-o','test.flv']
            self.log("RTMPDUMP command = " + str(command))
        else:
            command = [RTMPDUMP, '-B 1', '-m 2', '-r', url,'-o','test.flv']
            self.log("RTMPDUMP command = " + str(command))
       
        CheckRTMP = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        output = CheckRTMP.communicate()[0]
        self.log("output = " + output)
        
        if "ERROR:" in output:
            self.log("ERROR: Problem accessing the DNS. RTMP URL NOT VALiD")
            self.rtmpValid = False 
        elif "WARNING:" in output:
            self.log("WARNING: Problem accessing the DNS. RTMP URL NOT VALiD")
            self.rtmpValid = False
        elif "INFO: Connected..." in output:
            self.log("INFO: Connected...")
            self.rtmpValid = True
        else:
            self.log("ERROR?: Unknown response...")
            self.rtmpValid = False
        
        self.log("rtmpValid = " + str(self.rtmpValid))
        return self.rtmpValid

        
    def url_ok(self, url):
        self.urlValid = False
        url = unquote(url)
        try: 
            urllib2.urlopen(urllib2.Request(url))
            self.log("INFO: Connected...")
            self.urlValid = True
        except urllib2.URLError as e:
            self.log("ERROR: Problem accessing the DNS. HTTP URL NOT VALID, ERROR: " + str(e))
            self.urlValid = False
        
        self.log("urlValid = " + str(self.urlValid))
        return self.urlValid
        
        
    def plugin_ok(self, plugin):
        self.PluginFound = False
        self.Pluginvalid = False
        stream = plugin
        self.log("plugin stream = " + stream)
        id = plugin.split("/?")[0]
        id = id.split('//', 1)[-1]
        self.log("plugin id = " + id)
        try:
            xbmcaddon.Addon(id)
            self.PluginFound = True
        except:
            self.PluginFound = False 
        self.log("PluginFound = " + str(self.PluginFound))
        
        if self.PluginFound == True:
            if REAL_SETTINGS.getSetting("plugin_ok_level") == "0":#Low Check
                self.Pluginvalid = True     
                return self.Pluginvalid
            elif REAL_SETTINGS.getSetting("plugin_ok_level") == "1":#High Check todo
                try:
                    json_query = uni('{"jsonrpc": "2.0", "method": "Files.GetDirectory","params":{"directory":"%s"}, "id": 1}' % (self.escapeDirJSON(stream)))
                    json_folder_detail = self.sendJSON(json_query)
                    file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
                    self.log('json_folder_detail = ' + str(json_folder_detail))
                    self.log('file_detail = ' + str(file_detail))
                    self.Pluginvalid = True        
                except:
                    self.Pluginvalid = False
        else:
            self.Pluginvalid = False     
        
        self.log("Pluginvalid = " + str(self.Pluginvalid))
        return self.Pluginvalid
                
    
    def trim(self, content, limit, suffix):
        if len(content) <= limit:
            return content
        else:
            return content[:limit].rsplit(' ', 1)[0]+suffix

            
    def insertFiles(self, channel, fileList, type):
        self.log("insertFiles")
        self.logDebug("insertFiles, channel = " + str(channel))
        BCT_AUTO = False
        newFileList = []
        fileListNum = len(fileList)
        BumperMediaLST = []
        CommercialMediaLST = []
        TrailerMediaLST = []
        BumperLST = []
        CommercialLST = []
        TrailerLST = []
        BumperNum = 0
        CommercialNum = 0
        TrailerNum = 0
        chtype = (ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
        numbumpers = int(REAL_SETTINGS.getSetting("numbumpers"))#number of Bumpers between shows
        numcommercials = int(REAL_SETTINGS.getSetting("numcommercials"))#number of Commercial between shows
        numTrailers = int(REAL_SETTINGS.getSetting("numtrailers"))#number of trailers between shows
        self.logDebug("insertFiles, channel = " + str(channel))
        self.logDebug("insertFiles, chtype = " + str(chtype))
        self.logDebug("insertFiles, fileList count = " + str(len(fileList)))
        
        if numbumpers == 0 and numcommercials == 0 and numTrailers == 0:
            BCT_AUTO = True

        #Bumpers
        if (REAL_SETTINGS.getSetting('bumpers') == "true" and type != 'movies') and (chtype == '0' or chtype == '1'): # Bumpers not disabled,and is custom or network playlist.
            BumperLST = self.GetBumperList(channel, fileList)#build full Bumper list
            random.shuffle(BumperLST)
            BumperNum = len(BumperLST)#number of Bumpers items in full list
            self.logDebug("insertFiles, Bumpers.numbumpers = " + str(numbumpers))
            
        #Commercial
        if REAL_SETTINGS.getSetting('commercials') != '0' and type != 'movies': # commercials not disabled, and not a movie
            CommercialLST = self.GetCommercialList(channel, fileList)#build full Commercial list
            random.shuffle(CommercialLST)
            CommercialNum = len(CommercialLST)#number of Commercial items in full list
            self.logDebug("insertFiles, Commercials.numcommercials = " + str(numcommercials))
        
        #Trailers
        if REAL_SETTINGS.getSetting('trailers') != '0': # trailers not disabled, and not a movie
            TrailerLST = self.GetTrailerList(channel, fileList)
            random.shuffle(TrailerLST)
            TrailerNum = len(TrailerLST)#number of trailer items in full list
            self.logDebug("insertFiles, trailers.numTrailers = " + str(numTrailers))    

        if not BCT_AUTO:
            for i in range(fileListNum):
                BumperDur = 0
                BumperMediaLST = []
                BumperInt = []
                CommercialDur = 0
                CommercialMediaLST = []
                CommercialInt = []
                trailerDur = 0
                trailerMediaLST = []
                TrailerInt = []
                bctFileList = []
                File = uni(fileList[i])
                File = uni(File + '\n')
                
                if BumperNum > 0:
                    for n in range(numbumpers):
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding Bumpers", '')
                        Bumper = random.choice(BumperLST)#random fill Bumper per show by user selected amount
                        self.logDebug("insertFiles, Bumpers.Bumper = " + uni(Bumper))
                        BumperDur = int(Bumper.split(',')[0]) #duration of Bumper
                        BumperMedia = Bumper.split(',', 1)[-1] #link of Bumper
                        BumperMedia = ('#EXTINF:' + str(BumperDur) + ',//////Bumper////LIVEID|\n' + uni(BumperMedia))
                        BumperMediaLST.append(BumperMedia)
                
                if CommercialNum > 0:
                    for n in range(numcommercials):
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding Commercials", '')
                        Commercial = random.choice(CommercialLST)#random fill Commercial per show by user selected amount
                        self.logDebug("insertFiles, Commercials.Commercial = " + uni(Commercial))
                        CommercialDur = int(Commercial.split(',')[0]) #duration of Commercial
                        CommercialMedia = Commercial.split(',', 1)[-1] #link of Commercial
                        CommercialMedia = ('#EXTINF:' + str(CommercialDur) + ',//////Commercial////LIVEID|\n' + uni(CommercialMedia))
                        CommercialMediaLST.append(CommercialMedia)

                if TrailerNum > 0:
                    for n in range(numTrailers):
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding Trailers", '')
                        trailer = random.choice(TrailerLST)#random fill trailers per show by user selected amount
                        self.logDebug("insertFiles, trailers.trailer = " + uni(trailer))
                        trailerDur = int(trailer.split(',')[0]) #duration of trailer
                        trailerMedia = trailer.split(',', 1)[-1] #link of trailer
                        trailerMedia = ('#EXTINF:' + str(trailerDur) + ',//////Trailer////LIVEID|\n' + uni(trailerMedia))
                        trailerMediaLST.append(trailerMedia)   
                
                bctFileList.extend(BumperMediaLST)
                bctFileList.extend(CommercialMediaLST)
                bctFileList.extend(trailerMediaLST)
                random.shuffle(bctFileList)
                File = uni(File + '\n'.join(bctFileList))
                newFileList.append(File)

        else: #Auto BCT, Is Hide enabled? Get length or set it. Limit fill to under cliplength
            HideClips = str(REAL_SETTINGS.getSetting('HideClips'))
            MaxLength = SHORT_CLIP_ENUM[int(REAL_SETTINGS.getSetting("ClipLength"))]
            
            if HideClips == 'false':
                REAL_SETTINGS.setSetting('HideClips', "true")
                REAL_SETTINGS.setSetting('ClipLength', "5")
            self.logDebug("insertFiles, Auto.HideClips = " + str(HideClips))
            self.logDebug("insertFiles, Auto.ClipLength = " + str(MaxLength))
            
            if MaxLength > 0:
                for i in range(fileListNum):
                    global BCTtotal
                    BCTtotal = 0
                    BCTLength = 0
                    BumperDur = 0
                    BCTLeft = (MaxLength - BCTLength)
                    BumperMediaLST = []
                    BumperInt = []
                    CommercialDur = 0
                    CommercialMediaLST = []
                    CommercialInt = []
                    trailerDur = 0
                    trailerMediaLST = []
                    TrailerInt = []
                    bctFileList = []
                    File = uni(fileList[i])
                    File = uni(File + '\n')
                    
                    if BumperNum > 0:
                        for n in range(1):
                            self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding Bumpers", '')
                            Bumper = random.choice(BumperLST)#random fill Bumper per show by user selected amount
                            self.logDebug("insertFiles, Bumpers.Bumper = " + uni(Bumper))
                            BumperDur = int(Bumper.split(',')[0]) #duration of Bumper
                            BumperMedia = Bumper.split(',', 1)[-1] #link of Bumper
                            BumperMedia = ('#EXTINF:' + str(BumperDur) + ',//////Bumper////LIVEID|\n' + uni(BumperMedia))
                            BumperMediaLST.append(BumperMedia)
                        BCTtotal = BumperDur
                            
                    self.logDebug("insertFiles.BCTtotal.BumperDur = " + str(BCTtotal))
                    
                    for l in range(BCTLeft):
                        if BCTtotal >= MaxLength:
                            break
                            
                        if CommercialNum > 0:
                            for n in range(1):
                                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding Commercials", '')
                                Commercial = random.choice(CommercialLST)#random fill Commercial per show by user selected amount
                                self.logDebug("insertFiles, Commercials.Commercial = " + uni(Commercial))
                                CommercialDur = int(Commercial.split(',')[0]) #duration of Commercial
                                CommercialMedia = Commercial.split(',', 1)[-1] #link of Commercial
                                CommercialMedia = ('#EXTINF:' + str(CommercialDur) + ',//////Commercial////LIVEID|\n' + uni(CommercialMedia))
                                CommercialMediaLST.append(CommercialMedia)
                            BCTtotal = BCTtotal + CommercialDur
                    
                        self.logDebug("insertFiles.BCTtotal.CommercialDur = " + str(BCTtotal))
                    
                        if TrailerNum > 0:
                            for n in range(1):
                                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "adding Trailers", '')
                                trailer = random.choice(TrailerLST)#random fill trailers per show by user selected amount
                                self.logDebug("insertFiles, trailers.trailer = " + uni(trailer))
                                trailerDur = int(trailer.split(',')[0]) #duration of trailer
                                trailerMedia = trailer.split(',', 1)[-1] #link of trailer
                                trailerMedia = ('#EXTINF:' + str(trailerDur) + ',//////Trailer////LIVEID|\n' + uni(trailerMedia))
                                trailerMediaLST.append(trailerMedia)
                            BCTtotal = BCTtotal + trailerDur

                        self.logDebug("insertFiles.BCTtotal.trailerDur = " + str(BCTtotal))
                    
                    bctFileList.extend(BumperMediaLST)
                    bctFileList.extend(CommercialMediaLST)
                    bctFileList.extend(trailerMediaLST)
                    random.shuffle(bctFileList)
                    if len(bctFileList) != 0:
                        LastItem = len(bctFileList) - 1
                        bctFileList.pop(LastItem)#remove last line, to ensure under MaxLength... todo improve logic     
                    File = uni(File + '\n'.join(bctFileList))
                    newFileList.append(File)        
                            
        fileList = newFileList   

        return fileList
        
            
    def GetBumperList (self, channel, fileList):
        self.log("GetBumperList")
        BumperCachePath = xbmc.translatePath(os.path.join(BCT_LOC, 'bumpers')) + '/'  
        chtype = (ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
        
        if chtype == '0':
            setting1 = str(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1'))
            directory, filename = os.path.split(setting1)
            filename = uni(filename.split('.'))
            chname = uni(filename[0])
        else:
            chname = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")  
            
        PATH = REAL_SETTINGS.getSetting('bumpersfolder')
        PATH = uni(PATH + chname)
        LocalBumperLST = []
        BumperLST = []
        duration = 0
        
        #Local
        if FileAccess.exists(PATH) and REAL_SETTINGS.getSetting('bumpers') == "true":            
            BumperLocalCache = 'Bumper_Local_Cache_' + chname +'.xml'
            CacheExpired = self.Cache_ok(BumperCachePath, BumperLocalCache) 

            if CacheExpired == False:
                BumperLST = self.readCache(BumperCachePath, BumperLocalCache)
                
            elif CacheExpired == True: 
                LocalFLE = ''
                LocalBumper = ''
                LocalLST = xbmcvfs.listdir(PATH)[1]
                for i in range(len(LocalLST)):
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Bumpers...", '')
                    LocalFLE = (LocalLST[i])
                    filename = uni(PATH + '/' + LocalFLE)
                    duration = self.videoParser.getVideoLength(filename)
                    if duration == 0:
                        duration = 3
                    
                    if duration > 0:
                        LocalBumper = (str(duration) + ',' + filename)
                        LocalBumperLST.append(LocalBumper)#Put all bumpers found into one List
                BumperLST.extend(LocalBumperLST)#Put local bumper list into master bumper list.                
                self.writeCache(BumperLST, BumperCachePath, BumperLocalCache)
        return (BumperLST)        
        
    
    def GetCommercialList (self, channel, fileList):
        self.log("GetCommercialList")
        CommercialCachePath = xbmc.translatePath(os.path.join(BCT_LOC, 'commercials')) + '/'   
        chtype = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type')
        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Commercials...", '')
        
        if chtype == '0':
            setting1 = str(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1'))
            directory, filename = os.path.split(setting1)
            filename = uni(filename.split('.'))
            chname = uni(filename[0])
        else:
            chname = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")  
            
        PATH = REAL_SETTINGS.getSetting('commercialsfolder')
        LocalCommercialLST = []
        InternetCommercialLST = []
        YoutubeCommercialLST = []
        CommercialLST = []
        duration = 0
        
        #Local
        if FileAccess.exists(PATH) and REAL_SETTINGS.getSetting('commercials') == '1':
            CommercialLocalCache = 'Commercial_Local_Cache.xml'
            CacheExpired = self.Cache_ok(CommercialCachePath, CommercialLocalCache) 

            if CacheExpired == False:
                CommercialLST = self.readCache(CommercialCachePath, CommercialLocalCache)
                
            elif CacheExpired == True: 
                LocalFLE = ''
                LocalCommercial = ''
                LocalLST = xbmcvfs.listdir(PATH)[1]
                for i in range(len(LocalLST)):
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Local Commercials...", '')
                    LocalFLE = (LocalLST[i])
                    filename = uni(PATH + LocalFLE)
                    duration = self.videoParser.getVideoLength(filename)
                    if duration == 0:
                        duration = 30
                    
                    if duration > 0:
                        LocalCommercial = (str(duration) + ',' + filename)
                        LocalCommercialLST.append(LocalCommercial)
                CommercialLST.extend(LocalCommercialLST)                
                self.writeCache(CommercialLST, CommercialCachePath, CommercialLocalCache)
        
        #Internet (advertolog.com, ispot.tv)
        if REAL_SETTINGS.getSetting('commercials') == '2' and REAL_SETTINGS.getSetting("Donor_Enabled") == "true":
            CommercialInternetCache = 'Commercial_Internet_Cache.xml'
            CacheExpired = self.Cache_ok(CommercialCachePath, CommercialInternetCache) 

            if CacheExpired == False:
                CommercialLST = self.readCache(CommercialCachePath, CommercialInternetCache)
                
            elif CacheExpired == True:
                try:
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Internet Commercials...", '')
                    CommercialLST = self.Donor.InternetCommercial(CommercialCachePath)
                    self.writeCache(CommercialLST, CommercialCachePath, CommercialInternetCache)
                except:
                    self.log("Donor Code Unavailable")
                    pass

                    
        #Youtube
        if REAL_SETTINGS.getSetting('commercials') == '3':
            YoutubeCommercial = REAL_SETTINGS.getSetting('commercialschannel') # info,type,limit
            YoutubeCommercial = YoutubeCommercial.split(',')
            setting1 = YoutubeCommercial[0]
            setting2 = YoutubeCommercial[1]
            setting3 = YoutubeCommercial[2]
            setting4 = YoutubeCommercial[3]
            
            YoutubeLST = self.createYoutubeFilelist(setting1, setting2, setting3, setting4, channel)
            for i in range(len(YoutubeLST)):
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Youtube Commercials...", '')
                Youtube = YoutubeLST[i]
                duration = Youtube.split(',')[0]
                Commercial = Youtube.split('\n', 1)[-1]
                if Commercial != '' or Commercial != None:
                    YoutubeCommercial = (str(duration) + ',' + Commercial)
                    YoutubeCommercialLST.append(YoutubeCommercial)
            CommercialLST.extend(YoutubeCommercialLST)
        return (CommercialLST)    

    
    def GetTrailerList (self, channel, fileList):
        self.log("GetTrailerList")
        TrailerCachePath = xbmc.translatePath(os.path.join(BCT_LOC, 'trailers')) + '/'  
        chtype = (ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
        
        if chtype == '0':
            setting1 = str(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1'))
            directory, filename = os.path.split(setting1)
            filename = (filename.split('.'))
            chname = (filename[0])
        else:
            chname = ascii(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1"))
            
        if chtype == '3' or chtype == '4' or chtype == '5':
            GenreChtype = True
        else:
            GenreChtype = False
        
        self.log("GetTrailerList, GenreChtype = " + str(GenreChtype))
        PATH = REAL_SETTINGS.getSetting('trailersfolder')
            
        LocalTrailerLST = []
        JsonTrailerLST = []
        YoutubeTrailerLST = []
        TrailerLST = []
        duration = 0
        genre = ''
        
        #Local
        if (FileAccess.exists(PATH) and REAL_SETTINGS.getSetting('trailers') == '1'): 
            TrailerLocalCache = 'Trailer_Local_Cache.xml'
            CacheExpired = self.Cache_ok(TrailerCachePath, TrailerLocalCache) 

            if CacheExpired == False:
                TrailerLST = self.readCache(TrailerCachePath, TrailerLocalCache)
                
            elif CacheExpired == True: 
                LocalFLE = ''
                LocalTrailer = ''
                LocalLST = self.walk(PATH)
                LocalLST = str(LocalLST)
                LocalLST = LocalLST.split("', ''], ['")
                for i in range(len(LocalLST)):
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Local Trailers...", '')
                    LocalFLE = LocalLST[i]
                    if '-trailer' in LocalFLE:
                        LocalFLE = LocalFLE.replace("', '']]", "")
                        duration = self.videoParser.getVideoLength(LocalFLE)
                        if duration == 0:
                            duration = 120
                    
                        if duration > 0:
                            LocalTrailer = (str(duration) + ',' + LocalFLE)
                            LocalTrailerLST.append(LocalTrailer)
                TrailerLST.extend(LocalTrailerLST)                
                self.writeCache(TrailerLST, TrailerCachePath, TrailerLocalCache)
        
        #XBMC Library - Local Json
        if (REAL_SETTINGS.getSetting('trailers') == '2'):
            json_query = uni('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":["genre","trailer","runtime"]}, "id": 1}')
            genre = chname
            
            if REAL_SETTINGS.getSetting('trailersgenre') == 'true' and GenreChtype == True:
                TrailerInternetCache = 'Trailer_Json_Cache_' + genre + '.xml'
            else:
                TrailerInternetCache = 'Trailer_Json_Cache_All.xml'

            CacheExpired = self.Cache_ok(TrailerCachePath, TrailerInternetCache) 

            if CacheExpired == False:
                TrailerLST = self.readCache(TrailerCachePath, TrailerInternetCache)
                
            elif CacheExpired == True:
            
                if not self.cached_json_detailed_trailers:
                    self.logDebug('GetTrailerList, json_detail creating cache')
                    self.cached_json_detailed_trailers = self.sendJSON(json_query)   
                    json_detail = self.cached_json_detailed_trailers.encode('utf-8')   
                else:
                    json_detail = self.cached_json_detailed_trailers.encode('utf-8')   
                    self.logDebug('GetTrailerList, json_detail using cache')
                
                if REAL_SETTINGS.getSetting('trailersgenre') == 'true' and GenreChtype == True:
                    JsonLST = uni(json_detail.split("},{"))
                    match = [s for s in JsonLST if genre in s]
                    for i in range(len(match)): 
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Library Trailers, Matching Genres...", '')
                        duration = 120
                        json = uni(match[i])
                        trailer = json.split(',"trailer":"',1)[-1]
                        if ')"' in trailer:
                            trailer = trailer.split(')"')[0]
                        else:
                            trailer = trailer[:-1]
                        if trailer != '' or trailer != None or trailer != '"}]}':
                            if 'http://www.youtube.com/watch?hd=1&v=' in trailer:
                                trailer = trailer.replace("http://www.youtube.com/watch?hd=1&v=", "plugin://plugin.video.youtube/?action=play_video&videoid=").replace("http://www.youtube.com/watch?v=", "plugin://plugin.video.youtube/?action=play_video&videoid=")
                            JsonTrailer = (str(duration) + ',' + trailer)
                            if JsonTrailer != '120,':
                                JsonTrailerLST.append(JsonTrailer)
                    TrailerLST.extend(JsonTrailerLST)
                    self.writeCache(TrailerLST, TrailerCachePath, TrailerInternetCache)
                else:
                    JsonLST = uni(json_detail.split("},{"))
                    match = [s for s in JsonLST if 'trailer' in s]
                    for i in range(len(match)):
                        self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Library Trailers...", '')
                        duration = 120
                        json = uni(match[i])
                        trailer = json.split(',"trailer":"',1)[-1]
                        if ')"' in trailer:
                            trailer = trailer.split(')"')[0]
                        else:
                            trailer = trailer[:-1]
                        if trailer != '' or trailer != None or trailer != '"}]}':
                            if 'http://www.youtube.com/watch?hd=1&v=' in trailer:
                                trailer = trailer.replace("http://www.youtube.com/watch?hd=1&v=", "plugin://plugin.video.youtube/?action=play_video&videoid=").replace("http://www.youtube.com/watch?v=", "plugin://plugin.video.youtube/?action=play_video&videoid=")
                            JsonTrailer = (str(duration) + ',' + trailer)
                            if JsonTrailer != '120,':
                                JsonTrailerLST.append(JsonTrailer)
                    TrailerLST.extend(JsonTrailerLST)     
                    self.writeCache(TrailerLST, TrailerCachePath, TrailerInternetCache)
                
        #Internet
        if REAL_SETTINGS.getSetting('trailers') == '3' and REAL_SETTINGS.getSetting("Donor_Enabled") == "true":
            TrailerInternetCache = 'Trailer_Internet_Cache.xml'
            CacheExpired = self.Cache_ok(TrailerCachePath, TrailerInternetCache) 

            if CacheExpired == False:
                TrailerLST = self.readCache(TrailerCachePath, TrailerInternetCache)
                
            elif CacheExpired == True:
                try:
                    self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Internet Trailers...", '')
                    TrailerLST = self.Donor.InternetTrailer(TrailerCachePath)
                    self.writeCache(TrailerLST, TrailerCachePath, TrailerInternetCache)
                except:
                    self.log("Donor Code Unavailable")
                    pass

        
        #Youtube
        if REAL_SETTINGS.getSetting('trailers') == '4':
            YoutubeTrailers = REAL_SETTINGS.getSetting('trailerschannel') # info,type,limit
            YoutubeTrailers = YoutubeTrailers.split(',')
            setting1 = YoutubeTrailers[0]
            setting2 = YoutubeTrailers[1]
            setting3 = YoutubeTrailers[2]
            setting4 = YoutubeTrailers[3]
            
            YoutubeLST = self.createYoutubeFilelist(setting1, setting2, setting3, setting4, channel)
            for i in range(len(YoutubeLST)):
                self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(channel), "Parsing Youtube Trailers...", '')
                Youtube = YoutubeLST[i]
                duration = Youtube.split(',')[0]
                trailer = Youtube.split('\n', 1)[-1]
                if trailer != '' or trailer != None:
                    YoutubeTrailer = (str(duration) + ',' + trailer)
                    YoutubeTrailerLST.append(YoutubeTrailer)
            TrailerLST.extend(YoutubeTrailerLST)
        return (TrailerLST)

        
    def walk(self, path):
        self.logDebug("walk")     
        VIDEO_TYPES = ('.avi', '.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov', '.mkv', '.flv', '.ts', '.m2ts')
        video = []
        folders = []
        # multipath support
        if path.startswith('multipath://'):
            # get all paths from the multipath
            paths = path[12:-1].split('/')
            for item in paths:
                folders.append(urllib.unquote_plus(item))
        else:
            folders.append(path)
        for folder in folders:
            if xbmcvfs.exists(xbmc.translatePath(folder)):
                # get all files and subfolders
                dirs,files = xbmcvfs.listdir(folder)
                for item in files:
                    # filter out all video
                    if os.path.splitext(item)[1].lower() in VIDEO_TYPES:
                        video.append([os.path.join(folder,item), ''])
                for item in dirs:
                    # recursively scan all subfolders
                    video += self.walk(os.path.join(folder,item))
        return video
        
    
    def writeCache(self, thelist, thepath, thefile):
        self.log("writeCache")  
        now = datetime.datetime.today()

        if not os.path.exists(os.path.join(thepath)):
            os.makedirs(os.path.join(thepath))
        
        thefile = uni(thepath + thefile)        
        self.log("writeCache, thefile = " + thefile)  
        try:
            fle = FileAccess.open(thefile, "w")
            fle.write("%s\n" % now)
            for item in thelist:
                fle.write("%s\n" % item)
        except:
            pass
        
    def readCache(self, thepath, thefile):
        self.log("readCache") 
        thelist = []  
        thefile = uni(thepath + thefile)
        try:
            fle = FileAccess.open(thefile, "r")
            thelist = fle.readlines()
            LastItem = len(thelist) - 1
            thelist.pop(LastItem)#remove last line (empty line)
            thelist.pop(0)#remove first line (datetime)
            self.logDebug("readCache, thelist.count = " + str(len(thelist)))
            fle.close()
            return thelist
        except:
            pass
    
    
    def Cache_ok(self, thepath, thefile):
        self.log("Cache_ok")   
        CacheExpired = False
        thefile = thepath + thefile
        now = datetime.datetime.today()
        self.logDebug("Cache_ok, now = " + str(now))
        try:
            if FileAccess.exists(thefile):
                fle = FileAccess.open(thefile, "r")
                cacheDate = str(fle.readlines()[0])
                cacheDate = cacheDate.split('.')[0]
                cacheDate = datetime.datetime.strptime(cacheDate, '%Y-%m-%d %H:%M:%S')
                self.logDebug("Cache_ok, cacheDate = " + str(cacheDate))
                cacheDateEXP = (cacheDate + datetime.timedelta(days=30))
                self.logDebug("Cache_ok, cacheDateEXP = " + str(cacheDateEXP))
                fle.close()  
                if now >= cacheDateEXP:
                    CacheExpired = True      
            else:
                CacheExpired = True         
        except:
            self.logDebug("Cache_ok, exception")
            
        self.log("Cache_ok, CacheExpired = " + str(CacheExpired))
        return CacheExpired

    
    def sbManaged(self, tvdbid):
        sbManaged = False
        sbAPI = SickBeard(REAL_SETTINGS.getSetting('sickbeard.baseurl'),REAL_SETTINGS.getSetting('sickbeard.apikey'))
        if REAL_SETTINGS.getSetting('sickbeard.enabled') == 'true':
            try:
                sbAPI = SickBeard(REAL_SETTINGS.getSetting('sickbeard.baseurl'),REAL_SETTINGS.getSetting('sickbeard.apikey'))
                if sbAPI.isShowManaged(tvdbid):
                    sbManaged = True
            except:
                self.logDebug("sbManaged, exception")
        return sbManaged

        
    def cpManaged(self, title, imdbid):    
        cpManaged = False
        cpAPI = CouchPotato(REAL_SETTINGS.getSetting('couchpotato.baseurl'),REAL_SETTINGS.getSetting('couchpotato.apikey'))        
        if REAL_SETTINGS.getSetting('couchpotato.enabled') == 'true':
            try:
                r = cpAPI.getMoviebyTitle(title)
                r = str(r)
                r = r.split("u'")
                match = [s for s in r if imdbid in s][1]
                if imdbid in match:    
                    cpManaged = True
            except:
                self.logDebug("cpManaged, exception")
        return cpManaged 
        
    
    def loadFavourites(self):
        entries = list()
        path = xbmc.translatePath('special://userdata/favourites.xml')
        if os.path.exists(path):
            f = open(path)
            xml = f.read()
            f.close()

            try:
                doc = ET.fromstring(xml)
                for node in doc.findall('favourite'):
                    value = node.text
                    if value[0:11] == 'PlayMedia("':
                        value = value[11:-2]
                    elif value[0:10] == 'PlayMedia(':
                        value = value[10:-1]
                    else:
                        continue

                    entries.append((translation(30409), value))
            except ExpatError:
                pass

        return entries