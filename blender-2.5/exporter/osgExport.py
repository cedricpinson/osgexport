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
#  Cedric Pinson <cedric.pinson@plopbyte.com>
#

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

def main():
    import sys       # to get command line args
    import argparse  # to parse options for us and print a nice help message

    # get the args passed to blender after "--", all of which are ignored by
    # blender so scripts may receive their own arguments
    argv = sys.argv

    if "--" not in argv:
        argv = []  # as if no args are passed
    else:
        argv = argv[argv.index("--") + 1:]  # get all args after "--"

    # When --help or no args are given, print this help
    usage_text = \
    "Run blender in background mode with this script:"
    "  blender --background --python " + __file__ + " -- [options]"

    parser = argparse.ArgumentParser(description=usage_text)

    # Example utility, add some text and renders or saves it (with options)
    # Possible types are: string, int, long, choice, float and complex.
    parser.add_argument("-s", "--save", dest="save_path", metavar='FILE|PATH',
            help="Save the generated file to the specified path")

    args = parser.parse_args(argv)  # In this example we wont use the args

    config = osgconf.Config({'FILENAME': args.save_path 
                     })
    OpenSceneGraphExport(config)
    

if __name__ == "__main__":
    main()

bl_info = {
    "name": "Export OSG format (.osg)",
    "author": "Jeremy Moles, Cedric Pinson",
    "version": (2, 5, 9),
    "blender": (2, 5, 9),
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
    default_path = os.path.splitext(bpy.data.filepath)[0]
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
    bl_idname = "osg.export"
    bl_label = "OSG Model"

    filename_ext = ".osg"

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    AUTHOR = StringProperty(name="Author's Name", description="Name of the Author of this model", default="")
    SELECTED = BoolProperty(name="Only Export Selected", description="Only export the selected model", default=False)
    INDENT = IntProperty(name="Number of Indent Spaces", description="Number of Spaces to use for indentation in the model file", default=3, min=1, max=8)
    FLOATPRE = IntProperty(name="Floating Point Precision", description="The Floating Point Precision to use in exported model file", min=1, max=8, default=4)
    ANIMFPS = IntProperty(name="Frames Per Second", description="Number of Frames Per Second to use for exported animations", min=1, max=25, default=25)
    EXPORTANIM = BoolProperty(name="Export animations", description="Export animation yes/no", default=False)
    APPLYMODIFIERS = BoolProperty(name="Apply Modifiers", description="Apply modifiers before exporting yes/no", default=False)

    def execute(self, context):
        if not self.filepath:
            raise Exception("filepath not set")

        selected = "ALL"
        if self.SELECTED:
                selected = "SELECTED_ONLY_WITH_CHILDREN"

        config = osgconf.Config( {
                "FILENAME": self.filepath,
                "AUTHOR": self.AUTHOR,
                "LOG": True,
                "SELECTED": selected,
                "INDENT": self.INDENT,
                "FLOATPRE": self.FLOATPRE,
                "ANIMFPS": self.ANIMFPS,
                "EXPORTANIM": self.EXPORTANIM,
                "APPLY_MODIFIERS": self.APPLYMODIFIERS
                })

        print("FILENAME:" + repr(config.filename))
        OpenSceneGraphExport(config)
        return {'FINISHED'}
