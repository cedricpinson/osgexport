#!BPY
# -*- python-indent: 4; coding: iso-8859-1; mode: python -*-
# Copyright (C) 2008 Cedric Pinson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Cedric Pinson <cedric.pinson@plopbyte.net>
#

"""
Name: 'OpenSceneGraph (.osg)'
Blender: 248
Group: 'Export'
Tip: 'Export armature/bone/action/mesh data to osg formats.'
"""


import sys
import os
import Blender

sys.path.insert(0, "./")
sys.path.append(os.path.join(Blender.Get("scriptsdir"),"blenderExporter"))

import bpy
import osg
import osg.osgdata
import osg.osgconf
import osg.osggui

__version__ = osg.VERSION
__author__  = osg.AUTHOR
__email__   = osg.EMAIL
__url__     = osg.URL
__bpydoc__  = osg.DOC

def OpenSceneGraphExport(config=None):
    export = osg.osgdata.Export(config)
    print "....................", config.filename
    export.process()
    export.write()

if __name__ == "__main__":
    # If the user wants to run in "batch" mode, assume that ParseArgs
    # will correctly set atkconf data and go.
    config = osg.parseArgs(sys.argv)
    
    if config:
        OpenSceneGraphExport(config)
        Blender.Quit()

	# Otherwise, let the atkcgui module take over.
    else:
        gui = osg.osggui.OSGGUI(OpenSceneGraphExport)
        gui.Register()
