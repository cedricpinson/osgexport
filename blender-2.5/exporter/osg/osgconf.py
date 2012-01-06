# -*- python-indent: 4; coding: iso-8859-1; mode: python -*-
# Copyright (C) 2008 Cedric Pinson, Jeremy Moles
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
#  Jeremy Moles <jeremy@emperorlinux.com>



import os
from . import osglog
from . import osgobject

DEBUG = False
def debug(str):
    if DEBUG:
        osglog.log(str)

class Config(object):
    def __init__(self, map = None):
        object.__init__(self)
        if map is None:
            map = {}
        self.filename = map.get("FILENAME", "")
        self.author = map.get("AUTHOR","")
        self.indent = map.get("INDENT", int(2))
        self.float_precision = map.get("FLOATPRE",int(5))
        self.format_num = map.get("FLOATNUM", 0)
        self.anim_fps = map.get("ANIMFPS", 25.0)
        self.log_file = None
        self.log = map.get("LOG", True)
        self.selected = map.get("SELECTED", "ALL")
        self.relative_path = map.get("RELATIVE_PATH", False)
        self.anim_bake = map.get("BAKE", "FORCE")
        self.export_anim = map.get("EXPORTANIM", True)
        self.object_selected = map.get("OBJECT_SELECTED", None)
        self.apply_modifiers = map.get("APPLY_MODIFIERS", True)
        self.bake_constraints = map.get("BAKE_CONSTRAINTS", True)
        self.bake_frame_step = map.get("BAKE_FRAME_STEP", 1)
        self.fullpath = ""
        self.exclude_objects = []
        osglog.LOGFILE = None
        self.initFilePaths()
        status = " without log"
        if self.log:
            status = " with log"
        print("save path %s %s" %(self.fullpath, status))
        
    def createLogfile(self):
        logfilename = self.getFullName( "log")
        osglog.LOGFILE = None
        if self.log:
            self.log_file = open(logfilename, "w")
            osglog.LOGFILE = self.log_file
            #print("log %s %s" % (logfilename, osglog.LOGFILE))
        if self.export_anim is False:
            osglog.log("Animations will not be exported")
        
    def closeLogfile(self):
        filename = self.log_file.name
        osglog.log("Check log file " + filename)
        self.log_file.close()
        osglog.LOGFILE = None

    def validFilename(self):
        if len(self.filename) == 0:
            return False
        return True
        
    def initFilePaths(self):
        if len(self.filename) == 0:
            dirname  = "."
        else:
            dirname = os.path.dirname(self.filename)
        basename = os.path.splitext(os.path.basename(self.filename))[0]
        
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

        self.fullpath = dirname + os.sep
        self.filename = basename
        osgobject.INDENT = self.indent
        osgobject.FLOATPRE = self.float_precision

    def getFilenameIfRelative(self, name):
        if self.relative_path is True:
            return os.path.basename(name)
        return name

    def getFullPath(self):
        return self.fullpath

    def getFullName(self, extension):
        if self.filename[-(len(extension)+1):] == "." + extension:
            f = "%s%s" % (self.fullpath, self.filename)
        else:
            f = "%s%s.%s" % (self.fullpath, self.filename, extension)
        return f

# FILENAME   = ""
# AUTHOR     = ""
# FLOATPRE   = 5
# FORMATNUM  = 0
# ANIMFPS    = 25.0
# LOGFILE    = None
# LOG        = True
# SELECTED   = "ALL" #"SELECTED_ONLY_WITH_CHILDREN" #False
# BAKE       = ""

# FULLPATH   = ""
