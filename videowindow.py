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

print "script.pseudotv.live-VideoWindow, Patcher Started"

found = False
install = False
copy = False
patch = False
dlg = xbmcgui.Dialog()
mediaPath =  xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media')) + '/'
thumb = (DEFAULT_IMAGES_LOC + 'icon.png')

# Find Addon Path
AddonPath = 'special://home/addons/script.pseudotv.live/resources/skins/'
MasterPath = 'special://home/addons/script.pseudotv.live-master/resources/skins/'

if xbmcvfs.exists(AddonPath):
    fleMasterPath = (AddonPath)
else:
    fleMasterPath = (MasterPath)
xbmc.log('script.pseudotv.live-VideoWindow.fleMasterPath = ' + fleMasterPath)


# Find Pseudo Skin Path
PseudoSkin = (os.path.join(fleMasterPath, Skin_Select, '720p')) + '/'

if xbmcvfs.exists(PseudoSkin):
    PseudoSkinfle = xbmc.translatePath(os.path.join(fleMasterPath, Skin_Select, '720p', 'script.pseudotv.live.EPG.xml'))
else:
    PseudoSkinfle = xbmc.translatePath(os.path.join(fleMasterPath, Skin_Select, '1080i', 'script.pseudotv.live.EPG.xml'))
xbmc.log('script.pseudotv.live-VideoWindow.PseudoSkinfle = ' + PseudoSkinfle)
    
    
# Find XBMC Skin Path
skin = ('special://skin')
fle = 'Custom_PTVL_9506.xml'

if xbmcvfs.exists(os.path.join(skin ,'1080i')):
    skinPath = (os.path.join(skin ,'1080i', fle))
    found = True
else:
    skinPath = (os.path.join(skin ,'720p', fle))
    found = True
xbmc.log('script.pseudotv.live-VideoWindow.SkinPath = ' + skinPath)
  
Path = (os.path.join(ADDON_INFO, 'resources', 'skins', 'default', '720p'))
flePath = (os.path.join(Path, fle))

a = '<!-- PATCH START -->'
b = '<!-- PATCH START --> <!--'
c = '<!-- PATCH END -->'
d = '--> <!-- PATCH END -->'

# Delete Old VideoWindow Patch
if xbmcvfs.exists(skinPath):
    if dlg.yesno("PseudoTV Live", "VideoWindow Patch Found!\nDelete Patch?"):
        try:
            xbmcvfs.delete(skinPath)   
            replaceAll(PseudoSkinfle,a,b) #Replace with search n replace regex pattern todo  
            replaceAll(PseudoSkinfle,c,d)
            xbmc.log('script.pseudotv.live-VideoWindow, Deleted')
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "VideoWindow Patch Deleted!", 4000, thumb) )
        except:
            xbmc.log('script.pseudotv.live-VideoWindow, Delete Failed')
            pass
    else:
        if dlg.yesno("PseudoTV Live", "VideoWindow Patch Found!\nUpdate Skin?"):
            found = True
else:
    install = True
  
# Copy VideoWindow Patch  
if install:
    try:
        xbmcvfs.copy(flePath, skinPath)   
        replaceAll(PseudoSkinfle,b,a) #Replace with search n replace regex pattern todo  
        replaceAll(PseudoSkinfle,d,c)
        if xbmcvfs.exists(skinPath):
            copy = True
    except:
        xbmc.log('script.pseudotv.live-VideoWindow, Copy Failed')
        pass
    
    if copy:
        xbmc.log('script.pseudotv.live-VideoWindow, Copied')
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "VideoWindow Patched!\nXBMC Restart Required", 4000, thumb) )
    else:
        xbmc.log('script.pseudotv.live-VideoWindow, Copy Failed')
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "VideoWindow Patch Error!", 4000, thumb) )

# Update Pseudo Skin with VideoWindow Patch        
if found:
    try: 
        replaceAll(PseudoSkinfle,b,a) #Replace with search n replace regex pattern todo  
        replaceAll(PseudoSkinfle,d,c)
        if xbmcvfs.exists(skinPath):
            patch = True
    except:
        xbmc.log('script.pseudotv.live-VideoWindow, Copy Failed')
        pass
    
    if patch:
        xbmc.log('script.pseudotv.live-VideoWindow, Patched')
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "VideoWindow Patched!\nXBMC Restart Required", 4000, thumb) )
    else:
        xbmc.log('script.pseudotv.live-VideoWindow, Patched Failed')
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "VideoWindow Patch Error!", 4000, thumb) )
        
