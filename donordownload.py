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
BaseURL = ('http://'+UserPass+'@ptvl.comeze.com/PTVL/')

DonorURLPath = (BaseURL + 'Donor.py')
DonorPath = (os.path.join(fleMasterPath, 'resources', 'lib', 'Donor.pyo'))
DL_DonorPath = (os.path.join(fleMasterPath, 'resources', 'lib', 'Donor.py'))

DonorDownload = False
Installed = False
Error = False

if REAL_SETTINGS.getSetting("Donor_Enabled") == "true": 
    # Find Donor.pyo, Activate/Update
    if xbmcvfs.exists(DonorPath):
        if dlg.yesno("PseudoTV Live", "Update Donor Features?"):
            try:
                os.remove(xbmc.translatePath(DonorPath))
                DonorDownload = True    
            except Exception,e:
                xbmc.log(str(e))
                Error = True
                pass  
    elif xbmcvfs.exists(DL_DonorPath):
        if dlg.yesno("PseudoTV Live", "Update Donor Features?"):
            try: 
                os.remove(xbmc.translatePath(DL_DonorPath))
                DonorDownload = True   
            except Exception,e:
                xbmc.log(str(e))
                Error = True
                pass  
    else:
        DonorDownload = True   
        
if DonorDownload:
    # Download Donor.py
    try:
        urllib.urlretrieve(DonorURLPath, (xbmc.translatePath(DL_DonorPath)))
        xbmc.log('script.pseudotv.live-donordownload.Downloading Donor.pyo')
        REAL_SETTINGS.setSetting('Donor_Update', "false")
        if xbmcvfs.exists(DL_DonorPath):
            Installed = True
        else:
            Error = True
            Installed = False
    except Exception,e:
        xbmc.log(str(e))
        xbmc.log('script.pseudotv.live-Downloading Donor.pyo Failed: EXCEPTION', xbmc.LOGERROR)
        Error = True
        pass

if Error:
    MSG = "Donor Features Activated\Update Failed!\nTry Again Later..."

if Installed:
    MSG = "Donor Features Activated\Updated"
else:
    MSG = "Donor Features Not Updated..."
    
xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", MSG, 1000, THUMB) )