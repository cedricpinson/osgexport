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
#  Peter Amstutz <peter.amstutz@tseboston.com>

import sys
import os
import bpy
import pickle

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
    parser.add_argument("-s", "--save", dest="save_path", metavar='FILE|PATH', help="Save the generated file to the specified path")
    parser.add_argument("-a", "--enable-animation", dest="enable_animation", action="store_const", const=True, default=False, help="Enable saving of animations")
    parser.add_argument("-m", "--apply-modifiers", dest="apply_modifiers", action="store_const", const=True, default=False, help="Apply modifiers before exporting")

    args = parser.parse_args(argv)  # In this example we wont use the args

    config = osgconf.Config({'FILENAME': args.save_path,
                             'EXPORTANIM': args.enable_animation,
                             'APPLY_MODIFIERS': args.apply_modifiers,
                             })
    OpenSceneGraphExport(config)
    

if __name__ == "__main__":
    main()

bl_info = {
    "name": "Export OSG format (.osg)",
    "author": "Jeremy Moles, Cedric Pinson",
    "version": (0,9,0),
    "blender": (2, 5, 9),
    "api": 36339,
    "location": "File > Export > OSG Model (*.osg)",
    "description": "Export models and animations for use in OpenSceneGraph",
    "warning": "",
    "wiki_url": "https://github.com/cedricpinson/osgexport/wiki",
    "tracker_url": "http://github.com/cedricpinson/osgexport",
    "category": "Import-Export"}


def menu_export_osg_model(self, context):
    #import os
    #default_path = os.path.splitext(bpy.data.filepath)[0] + "_" + bpy.context.scene.name
    #default_path = default_path.replace('.', '_')
    #self.layout.operator(OSGGUI.bl_idname, text="OSG Model(.osg)").filepath = default_path
	self.layout.operator(OSGGUI.bl_idname, text="OSG Model(.osg)")

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
    
    AUTHOR = StringProperty(name="Author", description="Name of the Author of this model", default="")
    SELECTED = BoolProperty(name="Only Export Selected", description="Only export the selected model", default=False)
    ONLY_VISIBLE = BoolProperty(name="Only Export Visible", description="Only export the visible models", default=False)
    INDENT = IntProperty(name="Number of Indent Spaces", description="Number of Spaces to use for indentation in the model file", default=3, min=1, max=8)
    FLOATPRE = IntProperty(name="Floating Point Precision", description="The Floating Point Precision to use in exported model file", min=1, max=8, default=4)
    ANIMFPS = IntProperty(name="Frames Per Second", description="Number of Frames Per Second to use for exported animations", min=1, max=300, default=30)
    EXPORTANIM = BoolProperty(name="Export animations", description="Export animation yes/no", default=True)
    APPLYMODIFIERS = BoolProperty(name="Apply Modifiers", description="Apply modifiers before exporting yes/no", default=True)
    LOG = BoolProperty(name="Write log", description="Write log file yes/no", default=False)
    BAKE_CONSTRAINTS = BoolProperty(name="Bake Constraints", description="Bake constraints into actions", default=True)
    BAKE_FRAME_STEP = IntProperty(name="Bake frame step", description="Frame step when baking actions", default=1, min=1, max=30)
    OSGCONV_TO_IVE = BoolProperty(name="Convert to IVE (uses osgconv)", description="Use osgconv to convert to IVE", default=False)
    OSGCONV_EMBED_TEXTURES = BoolProperty(name="Embed textures in IVE", default=False)
    OSGCONV_CLEANUP = BoolProperty(name="Cleanup after conversion", default=False)
    OSGCONV_PATH = StringProperty(name="osgconv path", subtype="FILENAME", default="")
    RUN_VIEWER = BoolProperty(name="Run viewer (viewer path)", description="Run viewer after export", default=False)
    VIEWER_PATH = StringProperty(name="viewer path", subtype="FILENAME", default="")
    TEXTURE_PREFIX = StringProperty(name="texture prefix", default="")
    EXPORT_ALL_SCENES = BoolProperty(name="Export all scenes", default=False)
   
    def draw(self, context):
        layout = self.layout
        
        layout.row(align=True).label("Author:")
        layout.row(align=True).prop(self, "AUTHOR", text="")
        layout.row(align=True).prop(self, "SELECTED")
        layout.row(align=True).prop(self, "ONLY_VISIBLE")
        layout.row(align=True).prop(self, "EXPORTANIM")
        layout.row(align=True).prop(self, "EXPORT_ALL_SCENES")
        layout.row(align=True).prop(self, "APPLYMODIFIERS")
        layout.row(align=True).prop(self, "BAKE_CONSTRAINTS")
        layout.row(align=True).prop(self, "LOG")
        layout.row(align=True).prop(self, "ANIMFPS")
        layout.row(align=True).prop(self, "BAKE_FRAME_STEP")
        layout.row(align=True).prop(self, "FLOATPRE")
        layout.row(align=True).prop(self, "INDENT")
        layout.row(align=True).label("Texture Prefix:")
        layout.row(align=True).prop(self, "TEXTURE_PREFIX", text="")
        layout.row(align=True).prop(self, "OSGCONV_TO_IVE")
        layout.row(align=True).prop(self, "OSGCONV_EMBED_TEXTURES")
        layout.row(align=True).prop(self, "OSGCONV_CLEANUP")
        layout.row(align=True).prop(self, "OSGCONV_PATH", text="")
        layout.row(align=True).prop(self, "RUN_VIEWER")
        layout.row(align=True).prop(self, "VIEWER_PATH", text="")
        
    def invoke(self, context, event):
        print("config is " + bpy.utils.user_resource('CONFIG'))
        self.config = osgconf.Config()
        
        try:
            cfg = os.path.join(bpy.utils.user_resource('CONFIG'), "osgExport.cfg")
            if os.path.exists(cfg):
                with open(cfg, 'rb') as f:
                    self.config = pickle.load(f)
        except Exception:
            pass
        
        self.config.activate()
            
        self.SELECTED = (self.config.selected == "SELECTED_ONLY_WITH_CHILDREN")
        self.ONLY_VISIBLE = self.config.only_visible
        self.INDENT = self.config.indent
        self.FLOATPRE = self.config.float_precision
        self.ANIMFPS = context.scene.render.fps
        
        self.EXPORTANIM = self.config.export_anim
        self.APPLYMODIFIERS = self.config.apply_modifiers
        self.LOG = self.config.log
        self.BAKE_CONSTRAINTS = self.config.bake_constraints
        self.BAKE_FRAME_STEP = self.config.bake_frame_step
        self.OSGCONV_TO_IVE = self.config.osgconv_to_ive
        self.OSGCONV_EMBED_TEXTURES = self.config.osgconv_embed_textures
        self.OSGCONV_PATH = self.config.osgconv_path
        self.OSGCONV_CLEANUP = self.config.osgconv_cleanup
        
        self.RUN_VIEWER = self.config.run_viewer
        self.VIEWER_PATH = self.config.viewer_path
        self.TEXTURE_PREFIX = self.config.texture_prefix
        self.EXPORT_ALL_SCENES = self.config.export_all_scenes
        
        if bpy.data.filepath in self.config.history:
            self.filepath = self.config.history[bpy.data.filepath]
        
        return super(OSGGUI, self).invoke(context, event)
    
    def execute(self, context):
        if not self.filepath:
            raise Exception("filepath not set")

        self.config.initFilePaths(self.filepath)
        
        self.config.history[bpy.data.filepath] = self.filepath
        
        if self.SELECTED:
            self.config.selected = "SELECTED_ONLY_WITH_CHILDREN"
        else:
            self.config.selected = "ALL"
        self.config.indent = self.INDENT
        self.config.only_visible = self.ONLY_VISIBLE
        self.config.float_precision =  self.FLOATPRE
        self.config.fps = self.ANIMFPS
        self.config.export_anim = self.EXPORTANIM
        self.config.apply_modifiers = self.APPLYMODIFIERS
        self.config.log = self.LOG
        self.config.bake_constraints = self.BAKE_CONSTRAINTS
        self.config.bake_frame_step = self.BAKE_FRAME_STEP
        self.config.osgconv_to_ive = self.OSGCONV_TO_IVE
        self.config.osgconv_path = self.OSGCONV_PATH
        self.config.run_viewer = self.RUN_VIEWER
        self.config.viewer_path = self.VIEWER_PATH
        self.config.texture_prefix = self.TEXTURE_PREFIX
        self.config.osgconv_embed_textures = self.OSGCONV_EMBED_TEXTURES
        self.config.export_all_scenes = self.EXPORT_ALL_SCENES
        self.config.osgconv_cleanup = self.OSGCONV_CLEANUP
        
        try:
            cfg = os.path.join(bpy.utils.user_resource('CONFIG'), "osgExport.cfg")
            with open(cfg, 'wb') as f:
                pickle.dump(self.config, f)
        except Exception:
            pass
        
        if self.config.export_all_scenes:
            for scene in bpy.data.scenes:
                self.config.scene = scene
                print(self.filepath + "_" + scene.name)
                self.config.initFilePaths(os.path.splitext(self.filepath)[0] + "_" + scene.name)
                print(self.config.fullpath)
                print(self.config.filename)
                OpenSceneGraphExport(self.config)
        else:
            print("FILENAME:" + repr(self.config.filename))
            self.config.scene = bpy.context.scene
            OpenSceneGraphExport(self.config)
            
        return {'FINISHED'}
