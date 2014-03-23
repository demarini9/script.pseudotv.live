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


def replaceAll(file,searchExp,replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = line.replace(searchExp,replaceExp)
        sys.stdout.write(line)
        

def main():
    pass

if __name__ == '__main__':
    main()
    
import os, sys, re, fileinput
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from resources.lib.Globals import *
from resources.lib.FileAccess import *

xbmc.log('script.pseudotv.live-VideoWindow.Patcher Started')

# Find Addon Path
AddonPath = 'special://home/addons/script.pseudotv.live/resources/skins/'
MasterPath = 'special://home/addons/script.pseudotv.live-master/resources/skins/'

if xbmcvfs.exists(AddonPath):
    fleMasterPath = (AddonPath)
else:
    fleMasterPath = (MasterPath)
xbmc.log('script.pseudotv.live-VideoWindow.fleMasterPath = ' + fleMasterPath)


# Find PseudoTV Skin Path
PseudoSkin = (os.path.join(fleMasterPath, Skin_Select, '720p')) + '/'

if xbmcvfs.exists(PseudoSkin):
    PseudoSkinfle = xbmc.translatePath(os.path.join(fleMasterPath, Skin_Select, '720p', 'script.pseudotv.live.EPG.xml'))
else:
    PseudoSkinfle = xbmc.translatePath(os.path.join(fleMasterPath, Skin_Select, '1080i', 'script.pseudotv.live.EPG.xml'))
xbmc.log('script.pseudotv.live-VideoWindow.PseudoSkinfle = ' + PseudoSkinfle)
    
    
# Find XBMC Skin Path
Found = False
skin = ('special://skin')
fle = 'Custom_PTVL_9506.xml'

if xbmcvfs.exists(os.path.join(skin ,'1080i')):
    skinPath = (os.path.join(skin ,'1080i', fle))
    Found = True
else:
    skinPath = (os.path.join(skin ,'720p', fle))
    Found = True
xbmc.log('script.pseudotv.live-VideoWindow.SkinPath = ' + skinPath)

Path = (os.path.join(fleMasterPath, 'default', '720p'))
flePath = (os.path.join(Path, fle))
  
a = '<!-- PATCH START -->'
b = '<!-- PATCH START --> <!--'
c = '<!-- PATCH END -->'
d = '--> <!-- PATCH END -->'

Install = False
Installed = False
Reapply = False
Patched = False
Error = False
Uninstall = False
UnPatch = False

# Delete Old VideoWindow Patch
if xbmcvfs.exists(skinPath):
    if dlg.yesno("PseudoTV Live", "VideoWindow Patch Found!\nRemove Patch?"):
        try:
            xbmcvfs.delete(skinPath) 
            Uninstall = True
            xbmc.log('script.pseudotv.live-VideoWindow, Uninstall')
        except:
            xbmc.log('script.pseudotv.live-VideoWindow, Delete Patch Failed')
            Error = True
            pass
            
        try:
            f = FileAccess.open(PseudoSkinfle, "r")
            linesLST = f.readlines()            
            f.close()
            
            for i in range(len(set(linesLST))):
                lines = linesLST[i]
                if a in lines:
                    replaceAll(PseudoSkinfle,a,b)
                elif c in lines:
                    replaceAll(PseudoSkinfle,c,d)
            UnPatch = True
            xbmc.log('script.pseudotv.live-VideoWindow, UnPatch')
        except:
            xbmc.log('script.pseudotv.live-VideoWindow, Remove Patch Failed')
            Error = True
            pass
    else:
        if dlg.yesno("PseudoTV Live", "VideoWindow Patch Found!\nReapply Patch?"):
            Reapply = True
else:
    Install = True
  

  
# Copy VideoWindow Patch  
if Found and Install:
    try:
        xbmcvfs.copy(flePath, skinPath)
        if xbmcvfs.exists(skinPath):
            Installed = True
            xbmc.log('script.pseudotv.live-VideoWindow, Installed')
            Reapply = True
    except:
        xbmc.log('script.pseudotv.live-VideoWindow, Intall Failed')
        Error = True
        pass
    
if Reapply:
    try:
        f = FileAccess.open(PseudoSkinfle, "r")
        linesLST = f.readlines()            
        f.close()
        
        for i in range(len(set(linesLST))):
            lines = linesLST[i]
            if b in lines:
                replaceAll(PseudoSkinfle,b,a)
            elif d in lines:
                replaceAll(PseudoSkinfle,d,c)            
        xbmc.log('script.pseudotv.live-VideoWindow, Patched')
        Patched = True
    except:
        xbmc.log('script.pseudotv.live-VideoWindow, Reapply Failed')
        Error = True
        pass
    
    
if Installed or Patched:
    MSG = "VideoWindow Patched!\nXBMC Restart Required"
else:
    MSG = "VideoWindow Patch Not Installed"
    
if Uninstall or UnPatch:
    MSG = "VideoWindow Patch Removed!\nXBMC Restart Required"
else:
    MSG = "VideoWindow Patch Not Uninstalled"

if Error:
    MSG = "VideoWindow Patch Error!"
    
xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", MSG, 4000, THUMB) )