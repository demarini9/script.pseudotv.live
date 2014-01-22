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

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random, traceback
import urllib
import urllib2
import fanarttv

from fanarttv import *
from Globals import *
from FileAccess import FileLock, FileAccess
from xml.etree import ElementTree as ET

class Downloader:

    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)

    
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if REAL_SETTINGS.getSetting('enable_Debug') == "true":
            log('ChannelList: ' + msg, level)
    

    def ArtDownloader(self, mtype, id, type, typeEXT, mediapath, mediapathTYPE):
        self.log("fanartDownloader")
        print mtype
        print id
        print type
        print typeEXT
        print mediapath
        print mediapathTYPE
        
        if mtype == 'tvshow':
            # try:
            fanartTV = fanarttv.FTV_TVProvider()
            URLLST = fanartTV.get_image_list(id)
            self.logDebug('fanartDownloader.tvdb.URLLST.1 = ' + str(URLLST))
            if URLLST != None:
                URLLST = str(URLLST)
                URLLST = URLLST.split("{'art_type': ")
                self.logDebug('fanartDownloader.tvdb.URLLST.2 = ' + str(URLLST))
                Art1 = [s for s in URLLST if type in s]
                Art1 = Art1[0]
                self.logDebug('fanartDownloader.tvdb.Art1.1 = ' + uni(Art1))
                Art1 = Art1[Art1.find("'url': '")+len("'url': '"):Art1.rfind("',")]
                self.logDebug('fanartDownloader.tvdb.Art1.2 = ' + uni(Art1))
                Art1 = Art1.split("',")[0]
                self.logDebug('fanartDownloader.tvdb.Art1.3 = ' + uni(Art1))
                URLimage1 = Art1
                URLimage1 = URLimage1.rsplit('/')[-1]
                self.logDebug('fanartDownloader.tvdb.URLimage1.1 = ' + uni(URLimage1))
                URLimage1 = typeEXT
                self.logDebug('fanartDownloader.tvdb.URLimage1.2 = ' + uni(URLimage1))
                flename1 = mediapathTYPE
                self.logDebug('fanartDownloader.tvdb.flename1.1 = ' + uni(flename1))
            # except:
                # pass

    # elif mtype == 'movie':
        # try:
            # fanartTV = fanarttv.FTV_MovieProvider()
            # URLLST = fanartTV.get_image_list(id)
            # self.logDebug('fanartDownloader.imdb.URLLST.1 = ' + str(URLLST))
            # if URLLST != None:
                # URLLST = str(URLLST)
                # URLLST = URLLST.split("{'art_type': ")
                # self.logDebug('fanartDownloader.imdb.URLLST.2 = ' + str(URLLST))
                # Art1 = [s for s in URLLST if type1 in s]
                # Art1 = Art1[0]
                # self.logDebug('fanartDownloader.imdb.Art1.1 = ' + uni(Art1))
                # Art2 = [s for s in URLLST if type2 in s]
                # Art2 = Art2[0]
                # self.logDebug('fanartDownloader.imdb.Art2 = ' + uni(Art2))
                # Art1 = Art1[Art1.find("'url': '")+len("'url': '"):Art1.rfind("',")]
                # self.logDebug('fanartDownloader.imdb.Art1.2 = ' + uni(Art1))
                # Art1 = Art1.split("',")[0]
                # self.logDebug('fanartDownloader.imdb.Art1.3 = ' + uni(Art1))
                # Art2 = Art2[Art2.find("'url': '")+len("'url': '"):Art2.rfind("',")]
                # self.logDebug('fanartDownloader.imdb.Art2.2 = ' + uni(Art2))
                # Art2 = Art2.split("',")[0]
                # self.logDebug('fanartDownloader.imdb.Art2.3 = ' + uni(Art2))
                # URLimage1 = Art1
                # URLimage1 = URLimage1.rsplit('/')[-1]
                # self.logDebug('fanartDownloader.imdb.URLimage1.1 = ' + uni(URLimage1))
                # URLimage2 = Art2
                # URLimage1 = 
                # self.logDebug('fanartDownloader.imdb.URLimage1.2 = ' + uni(URLimage1))
                # flename1 = mediapathTYPE
        # except:
            # pass
                # if FileAccess.exists(flename1):
                    # self.getControl(508).setImage(flename1)
                # else:
                    # if not os.path.exists(os.path.join(Artpath)):
                        # os.makedirs(os.path.join(Artpath))
                    
                    # resource = urllib.urlopen(Art1)# Replace with urlretrieve todo
                    # self.logDebug('fanartDownloader.tvdb.resource = ' + uni(resource))
                    # output = open(flename1,"wb")
                    # self.logDebug('fanartDownloader.tvdb.output = ' + uni(output))
                    # output.write(resource.read())
                    # output.close()
                    # self.getControl(508).setImage(flename1)
                
                # flename2 = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'generated')  + '/' + 'artwork' + '/' + URLimage2)
                
                # if FileAccess.exists(flename2):
                    # self.getControl(510).setImage(flename2)
                # else:
                    # if not os.path.exists(os.path.join(Artpath)):
                        # os.makedirs(os.path.join(Artpath))
                    
                    # resource = urllib.urlopen(Art2)# Replace with urlretrieve todo
                    # self.logDebug('fanartDownloader.tvdb.resource = ' + uni(resource))
                    # output = open(flename2,"wb")
                    # self.logDebug('fanartDownloader.tvdb.output = ' + uni(output))
                    # output.write(resource.read())
                    # output.close()
                    # self.getControl(510).setImage(flename2)  

###############################
# if tvdbid != 0 and genre != 'Movie': #TV
                        # fanartTV = fanarttv.FTV_TVProvider()
                        # URLLST = fanartTV.get_image_list(tvdbid)
                        # self.logDebug('setShowInfo.tvdb.URLLST.1 = ' + uni(URLLST))
                        # if URLLST != None:
                            # URLLST = uni(URLLST)
                            # URLLST = URLLST.split("{'art_type': ")
                            # self.logDebug('setShowInfo.tvdb.URLLST.2 = ' + uni(URLLST))
                            # try:
                                # Art1 = [s for s in URLLST if type1 in s]
                                # Art1 = Art1[0]
                                # self.logDebug('setShowInfo.tvdb.Art1.1 = ' + uni(Art1))
                                # Art1 = Art1[Art1.find("'url': '")+len("'url': '"):Art1.rfind("',")]
                                # self.logDebug('setShowInfo.tvdb.Art1.2 = ' + uni(Art1))
                                # Art1 = Art1.split("',")[0]
                                # self.logDebug('setShowInfo.tvdb.Art1.3 = ' + uni(Art1))
                                # URLimage1 = Art1
                                # URLimage1 = URLimage1.rsplit('/')[-1]
                                # self.logDebug('setShowInfo.tvdb.URLimage1.1 = ' + uni(URLimage1))
                                # URLimage1 = (type1 + '-' + URLimage1)
                                # self.logDebug('setShowInfo.tvdb.URLimage1.2 = ' + uni(URLimage1))
                                # flename1 = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'generated')  + '/' + 'artwork' + '/' + URLimage1)
                                
                                # if FileAccess.exists(flename1):
                                    # self.getControl(508).setImage(flename1)
                                # else:
                                    # if not os.path.exists(os.path.join(Artpath)):
                                        # os.makedirs(os.path.join(Artpath))
                                    
                                    # resource = urllib.urlopen(Art1)
                                    # self.logDebug('setShowInfo.tvdb.resource = ' + uni(resource))
                                    # output = open(flename1,"wb")
                                    # self.logDebug('setShowInfo.tvdb.output = ' + uni(output))
                                    # output.write(resource.read())
                                    # output.close()
                                    # self.getControl(508).setImage(flename1)
                            # except:
                                # self.getControl(508).setImage(self.mediaPath + type1 + '.png')
                                # pass
                            
                            # try:
                                # Art2 = [s for s in URLLST if type2 in s]
                                # Art2 = Art2[0]
                                # self.logDebug('setShowInfo.tvdb.Art2 = ' + uni(Art2))
                                # Art2 = Art2[Art2.find("'url': '")+len("'url': '"):Art2.rfind("',")]
                                # self.logDebug('setShowInfo.tvdb.Art2.2 = ' + uni(Art2))
                                # Art2 = Art2.split("',")[0]
                                # self.logDebug('setShowInfo.tvdb.Art2.3 = ' + uni(Art2))
                                # URLimage2 = Art2
                                # URLimage2 = URLimage2.rsplit('/')[-1]
                                # self.logDebug('setShowInfo.tvdb.URLimage1.1 = ' + uni(URLimage1))
                                # URLimage2 = (type2 + '-' + URLimage2)
                                # self.logDebug('setShowInfo.tvdb.URLimage2.2 = ' + uni(URLimage2))        
                                # flename2 = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'generated')  + '/' + 'artwork' + '/' + URLimage2)
                                
                                # if FileAccess.exists(flename2):
                                    # self.getControl(510).setImage(flename2)
                                # else:
                                    # if not os.path.exists(os.path.join(Artpath)):
                                        # os.makedirs(os.path.join(Artpath))
                                    
                                    # resource = urllib.urlopen(Art2)
                                    # self.logDebug('setShowInfo.tvdb.resource = ' + uni(resource))
                                    # output = open(flename2,"wb")
                                    # self.logDebug('setShowInfo.tvdb.output = ' + uni(output))
                                    # output.write(resource.read())
                                    # output.close()
                                    # self.getControl(510).setImage(flename2)  
                            # except:
                                # self.getControl(510).setImage(self.mediaPath + type2 + '.png')
                                # pass

                        # else:#fallback all artwork because there is no id
                            # self.getControl(508).setImage(self.mediaPath + type1 + '.png')
                            # self.getControl(510).setImage(self.mediaPath + type2 + '.png')

                    # elif imdbid != 0 and genre == 'Movie':#Movie
                        # fanartTV = fanarttv.FTV_MovieProvider()
                        # URLLST = fanartTV.get_image_list(imdbid)
                        # self.logDebug('setShowInfo.imdb.URLLST.1 = ' + str(imdbid))
                        # if URLLST != None:
                            # try:
                                # URLLST = uni(URLLST)
                                # URLLST = URLLST.split("{'art_type': ")
                                # self.logDebug('setShowInfo.imdb.URLLST.2 = ' + uni(URLLST))
                                # Art1 = [s for s in URLLST if type1 in s]
                                # Art1 = Art1[0]
                                # self.logDebug('setShowInfo.imdb.Art1.1 = ' + uni(Art1))
                                # Art2 = [s for s in URLLST if type2 in s]
                                # Art2 = Art2[0]
                                # self.logDebug('setShowInfo.imdb.Art2 = ' + uni(Art2))
                                # Art1 = Art1[Art1.find("'url': '")+len("'url': '"):Art1.rfind("',")]
                                # self.logDebug('setShowInfo.imdb.Art1.2 = ' + uni(Art1))
                                # Art1 = Art1.split("',")[0]
                                # self.logDebug('setShowInfo.imdb.Art1.3 = ' + uni(Art1))
                                # Art2 = Art2[Art2.find("'url': '")+len("'url': '"):Art2.rfind("',")]
                                # self.logDebug('setShowInfo.imdb.Art2.2 = ' + uni(Art2))
                                # Art2 = Art2.split("',")[0]
                                # self.logDebug('setShowInfo.imdb.Art2.3 = ' + uni(Art2))
                                # URLimage1 = Art1
                                # URLimage1 = URLimage1.rsplit('/')[-1]
                                # self.logDebug('setShowInfo.imdb.URLimage1.1 = ' + uni(URLimage1))
                                # URLimage2 = Art2
                                # URLimage1 = (type1 + '-' + URLimage1)
                                # self.logDebug('setShowInfo.imdb.URLimage1.2 = ' + uni(URLimage1))
                                # URLimage2 = URLimage1.rsplit('/')[-1]
                                # self.logDebug('setShowInfo.imdb.URLimage2.2 = ' + uni(URLimage2))
                                # URLimage2 = (type2 + '-' + URLimage2)
                                # flename1 = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'generated')  + '/' + 'artwork' + '/' + URLimage1)

                                # if FileAccess.exists(flename1):
                                    # self.getControl(508).setImage(flename1)
                                # else:
                                    # if not os.path.exists(os.path.join(Artpath)):
                                        # os.makedirs(os.path.join(Artpath))
                                    
                                    # resource = urllib.urlopen(Art1)# Replace with urlretrieve todo
                                    # self.logDebug('setShowInfo.tvdb.resource = ' + uni(resource))
                                    # output = open(flename1,"wb")
                                    # self.logDebug('setShowInfo.tvdb.output = ' + uni(output))
                                    # output.write(resource.read())
                                    # output.close()
                                    # self.getControl(508).setImage(flename1)
                                
                                # flename2 = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'generated')  + '/' + 'artwork' + '/' + URLimage2)
                                
                                # if FileAccess.exists(flename2):
                                    # self.getControl(510).setImage(flename2)
                                # else:
                                    # if not os.path.exists(os.path.join(Artpath)):
                                        # os.makedirs(os.path.join(Artpath))
                                    
                                    # resource = urllib.urlopen(Art2)# Replace with urlretrieve todo
                                    # self.logDebug('setShowInfo.tvdb.resource = ' + uni(resource))
                                    # output = open(flename2,"wb")
                                    # self.logDebug('setShowInfo.tvdb.output = ' + uni(output))
                                    # output.write(resource.read())
                                    # output.close()
                                    # self.getControl(510).setImage(flename2)  
                                # ##############################################

