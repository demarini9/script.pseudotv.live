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
from resources.lib.unzip import *

print "script.pseudotv.live-PseudoTV Live, Donor Download Started"

mediaPath =  xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media')) + '/'
thumb = (DEFAULT_IMAGES_LOC + 'icon.png')
dlg = xbmcgui.Dialog()
un = unzip()
UserPass = REAL_SETTINGS.getSetting('Donor_UP')
DonorFle = 'Donor.pyo'
GenericFle = 'Generic.zip'
AddonPath = (xbmc.translatePath(os.path.join('special://home/addons/script.pseudotv.live/resources/lib/')))
MasterPath = (xbmc.translatePath(os.path.join('special://home/addons/script.pseudotv.live-master/resources/lib/')))
CachePath = (xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache')) + '/')
StrmsPath = (xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'strms')) + '/')
GenericPath = (xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'strms', 'Generic')) + '/')
BaseURL = ('http://'+UserPass+'@ptvl.comeze.com/PTVL/')
DonorURLPath = (BaseURL + DonorFle)   
GenericURLPath = (BaseURL + GenericFle) 
GenericURLFlePath = (CachePath + GenericFle) 
DonorDownload = False
DonorInstall = False


if REAL_SETTINGS.getSetting("Donor_Enabled") == "true":  
    # Find Addon Path
    if os.path.exists(AddonPath):
        fleMasterPath = (AddonPath + DonorFle)
    else:
        fleMasterPath = (MasterPath + DonorFle)
    
    # Find Donor.pyo, Activate/Update
    if os.path.exists(fleMasterPath):
        if dlg.yesno("PseudoTV Live", "Update Donor Features?"):
            try:
                os.remove(fleMasterPath)
            except:
                pass
            DonorDownload = True           
    else:
        DonorDownload = True    
        
if DonorDownload:
    
    # Download Donor.pyo
    try:
        urllib.urlretrieve(DonorURLPath, fleMasterPath)
        xbmc.log('script.pseudotv.live-Downloading Donor.pyo')
        REAL_SETTINGS.setSetting('Donor_Update', "false")
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Donor Features Activated\Updated\nThank you for your support...", 1000, thumb) )
    except:
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Donor Features Activated\Updated Failed\nTry Again Later...", 1000, thumb) )
        xbmc.log('script.pseudotv.live-Downloading Donor.pyo Failed: EXCEPTION', xbmc.LOGERROR)
        pass

    # Download Generic.Zip
    if os.path.exists(GenericPath):
        xbmc.log('script.pseudotv.live-Removing Old Generic Folder')
        try:
            shutil.rmtree(GenericPath)
        except:
            xbmc.log('script.pseudotv.live-removing Generic.zip Failed: EXCEPTION', xbmc.LOGERROR)
            pass
    try:
        xbmc.log('script.pseudotv.live-Downloading Generic.zip')
        urllib.urlretrieve(GenericURLPath, GenericURLFlePath)
    except:
        xbmc.log('script.pseudotv.live-Downloading Generic.zip Failed: EXCEPTION', xbmc.LOGERROR)
        pass
    
    try:
        if not os.path.exists(StrmsPath):
            os.makedirs(StrmsPath)   
        xbmc.log('script.pseudotv.live - Extracting Generic.zip')
        un.extract(GenericURLFlePath, StrmsPath)
    except:
        xbmc.log('script.pseudotv.live-extracting Generic.zip Failed: EXCEPTION', xbmc.LOGERROR)
        pass
    
    try:
        xbmc.log('script.pseudotv.live - Removing Generic.zip')
        os.remove(GenericURLFlePath)
    except:
        xbmc.log('script.pseudotv.live-Updating Generic.zip Failed: EXCEPTION', xbmc.LOGERROR)
        pass

    if os.path.exists(GenericPath):
        DonorInstall = True
        
        
if DonorInstall == True:
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Donor Channels Synced!\nXBMC Restart Required", 1000, thumb) )
else:
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Not All Donor Channels Synced\nTry Again Later...", 1000, thumb) )
