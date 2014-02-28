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
    
import os, sys, re
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

from resources.lib.Globals import *
from resources.lib.FileAccess import *

print "script.pseudotv.live-restore, Setting2 Restore Started"

settingsFile = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.xml'))
nsettingsFile = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.bak.xml'))
dlg = xbmcgui.Dialog()
mediaPath =  xbmc.translatePath(os.path.join(ADDON_INFO, 'resources', 'skins', 'default', 'media')) + '/'
thumb = (DEFAULT_IMAGES_LOC + 'icon.png')

if REAL_SETTINGS.getSetting("ATRestore") == "true":
    if FileAccess.exists(settingsFile) and FileAccess.exists(nsettingsFile):
        # try:
        xbmc.log('Autotune, Removing Setting2...')
        os.remove(settingsFile)
        xbmc.log('Autotune, Restoring Backup Setting2...')   
        FileAccess.rename(nsettingsFile, settingsFile)  
        REAL_SETTINGS.setSetting("ATRestore","false")   
        xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Backup Channels Restored", 4000, thumb) )
        # except:        
            # REAL_SETTINGS.setSetting("ATRestore","false")
            # xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Restoring Backup Channels Failed!", 4000, thumb) )
            # pass 
