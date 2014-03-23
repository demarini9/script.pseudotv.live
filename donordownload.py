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

def main():
    pass

if __name__ == '__main__':
    main()
 
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, sys, re, shutil, fileinput
import urllib

from resources.lib.Globals import *

xbmc.log("script.pseudotv.live-PseudoTV Live, Donor Download Started")

UserPass = REAL_SETTINGS.getSetting('Donor_UP')

CachePath = (xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache')) + '/')
StrmsPath = (xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'strms')) + '/')
GenericPath = (xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'strms', 'Generic')) + '/')

DonorFle = 'Donor.pyo'
GenericFle = 'Generic.zip'

BaseURL = ('http://'+UserPass+'@ptvl.comeze.com/PTVL/')
DonorURLPath = (BaseURL + DonorFle)   
GenericURLPath = (BaseURL + GenericFle) 
GenericURLFlePath = (CachePath + GenericFle) 

DonorDownload = False
Installed = False
Error = False

AddonPath = (xbmc.translatePath(os.path.join('special://home/addons/script.pseudotv.live/resources/lib/')))
MasterPath = (xbmc.translatePath(os.path.join('special://home/addons/script.pseudotv.live-master/resources/lib/')))

if REAL_SETTINGS.getSetting("Donor_Enabled") == "true": 
    # Find Addon Path
    if xbmcvfs.exists(AddonPath):
        fleMasterPath = (AddonPath + DonorFle)
    else:
        fleMasterPath = (MasterPath + DonorFle)
    
    xbmc.log('script.pseudotv.live-donordownload.fleMasterPath = ' + fleMasterPath)

    # Find Donor.pyo, Activate/Update
    if xbmcvfs.exists(fleMasterPath):
        if dlg.yesno("PseudoTV Live", "Update Donor Features?"):
            try:
                os.remove(fleMasterPath)
                DonorDownload = True    
            except:
                Error = True
                pass       
    else:
        DonorDownload = True    
        
if DonorDownload:
    # Download Donor.pyo
    try:
        urllib.urlretrieve(DonorURLPath, fleMasterPath)
        xbmc.log('script.pseudotv.live-donordownload.Downloading Donor.pyo')
        REAL_SETTINGS.setSetting('Donor_Update', "false")
        if xbmcvfs.exists(fleMasterPath):
            Installed = True
        else:
            Error = True
            Installed = False
    except:
        xbmc.log('script.pseudotv.live-Downloading Donor.pyo Failed: EXCEPTION', xbmc.LOGERROR)
        Error = True
        pass

if Error:
    MSG = "Donor Features Activated\Update Failed!\nTry Again Later..."

if Installed:
    MSG = "Donor Features Activated\Updated\nXBMC Restart Required..."
else:
    MSG = "Donor Features Not Updated..."
    
xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", MSG, 4000, THUMB) )