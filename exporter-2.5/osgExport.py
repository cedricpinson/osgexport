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
import bpy

sys.path.insert(0, "./")
BlenderExporterDir = os.getenv("BlenderExporter", os.path.join(bpy.context.user_preferences.filepaths.script_directory,"blenderExporter"))
print("BlenderExporter directory ", BlenderExporterDir)
sys.path.append(BlenderExporterDir)

import bpy
import osg
from osg import osgdata
from osg import osgconf
#from osg import osggui

__version__ = osg.VERSION
__author__  = osg.AUTHOR
__email__   = osg.EMAIL
__url__     = osg.URL
__bpydoc__  = osg.DOC

def OpenSceneGraphExport(config=None):
    export = osg.osgdata.Export(config)
    print("....................", config.filename)
    export.process()
    export.write()

if __name__ == "__main__":
    # If the user wants to run in "batch" mode, assume that ParseArgs
    # will correctly set atkconf data and go.
    print(sys.argv)
    config = osg.parseArgs(sys.argv)
    
    if config:
        OpenSceneGraphExport(config)
        bpy.ops.wm.quit_blender()

	# Otherwise, let the atkcgui module take over.
    else:
        gui = OSGGUI(OpenSceneGraphExport)
        gui.Register()

bl_info = {
    "name": "Export OSG format (.osg)",
    "author": "Jeremy Moles, Cedric Pinson",
    "version": (2, 5, 7),
    "blender": (2, 5, 7),
    "api": 36339,
    "location": "File > Export > OSG Model (*.osg)",
    "description": "Export models and animations for use in OpenSceneGraph",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/"\
        "Scripts/Import-Export/Blender-toOSG",
    "tracker_url": "https://projects.blender.org/tracker/index.php?"\
        "func=detail&atid=281",
    "category": "Import-Export"}


def menu_export_osg_model(self, context):
    import os
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".osg"
    self.layout.operator(OSGGUI.bl_idname, text="OSG Model(.osg)").filepath = default_path


def register():
        
        bpy.utils.register_module(__name__)
        bpy.types.INFO_MT_file_export.append(menu_export_osg_model)

def unregister():
        bpy.utils.unregister_module(__name__)
        bpy.types.INFO_MT_file_export.remove(menu_export_osg_model)


from bpy.props import *
try:
    from io_utils import ExportHelper
    print("Use old import path - your blender is not the latest version")
except:
    from bpy_extras.io_utils import ExportHelper
    print("Use new import path")

class OSGGUI(bpy.types.Operator, ExportHelper):
    '''Export model data to an OpenSceneGraph file'''
    bl_idname = "osg_model.osg"
    bl_label = "OSG Model"

    filename_ext = ".osg"

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    AUTHOR = StringProperty(name="Author's Name", description="Name of the Author of this model", default="")
    SELECTED = BoolProperty(name="Only Export Selected", description="Only export the selected model", default=False)
    INDENT = IntProperty(name="Number of Indent Spaces", description="Number of Spaces to use for indentation in the model file", default=3, min=1, max=8)
    FLOATPRE = IntProperty(name="Floating Point Precision", description="The Floating Point Precision to use in exported model file", min=1, max=8, default=4)
    ANIMFPS = IntProperty(name="Frames Per Second", description="Number of Frames Per Second to use for exported animations", min=1, max=60, default=25)

    def execute(self, context):
        if not self.filepath:
            raise Exception("filepath not set")

        selected = "ALL"
        if self.SELECTED:
                selected = "SELECTED_ONLY_WITH_CHILDREN"

        config = osg.parseArgs(["""--osg=
                AUTHOR     = %s;
                LOG        = %s;
                SELECTED   = %s;
                INDENT  = %s;
                FLOATPRE   = %g;
                ANIMFPS    = %s;
                FILENAME   = %s;
        """ % (
                self.AUTHOR,
                True, #self.objects["LOG"].val,
                selected,
                self.INDENT,
                self.FLOATPRE,
                self.ANIMFPS,
                self.filepath
        )])

        print("FILENAME:" + repr(config.filename))
        OpenSceneGraphExport(config)
        return {'FINISHED'}
