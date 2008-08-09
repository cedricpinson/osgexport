#!BPY
""" Registration info for Blender menus: <- these words are ignored
Name: 'OpenSceneGraph (.osg)'
Blender: 246
Group: 'Export'
Tip: 'Export to OpenSceneGraph (.osg) format.'
"""

__author__ = "Cedric Pinson, Ruben Lopez"
__url__ = ("Project homepage, http://www.plopbyte.net/")
__version__ = "0.1"
__email__ = "mornifle@plopbyte.net"
__bpydoc__ = """\

Description: Exports a ASCII OpenSceneGraph file from a Blender scene.

"""
#######################################################################
# Copyright (C) 2008 Cedric Pinson <mornifle@plopbyte.net>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# You can read the GNU General Public License at http://www.gnu.org
#
#######################################################################
# Copyright (C) 2002-2006 Ruben Lopez <ryu@gpul.org>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# You can read the GNU General Public License at http://www.gnu.org
#
# Description:
# This script allows you to model in blender and export your models for
# use in realtime OSG applications.
#
# Start this script with ALT+P
#
# Check README.txt for details
#
#######################################################################

import Blender
from Blender import Scene, Object, Window
from Blender import BGL
from Blender.BGL import *
from Blender import Draw
from Blender.Draw import *
from Blender import NMesh
from Blender import Types, Ipo
from math import sin, cos, pi
import sys
from sys import exit
import osg
from osg import OSGExport


#######################################################################
#######################################################################
#######################################################################
#Main script
if __name__ == "__main__":
    # If the user wants to run in "batch" mode, assume that ParseArgs
    # will correctly set atkconf data and go.
    if osg.ParseArgs(sys.argv):
        scene = Scene.getCurrent()
        objects = scene.getChildren()
        loopMode = 1
        meshAnim = 1
        fps = 25
        exporter = OSGExport(osg.osgconf.FILENAME, 
                             scene,
                             loopMode,
                             meshAnim,
                             fps,
                             objects)
        print "export to",osg.osgconf.FILENAME
        exporter.export()
        Blender.Quit()

    # Otherwise, let the atkcgui module take over.
    else:
        print "No gui"
