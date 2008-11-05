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
#  Cedric Pinson <mornifle@plopbyte.net>
#  Jeremy Moles <jeremy@emperorlinux.com>



import os
import osglog
import osgobject

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
        self.export_anim = map.get("EXORTANIM", True)
        self.fullpath = ""
        self.exclude_objects = []
        osglog.LOGFILE = None
        self.initFilePaths()

    def createLogfile(self):
        logfilename = self.getFullName( "log")
        osglog.LOGFILE = None
	if self.log:
		self.log_file = file(logfilename, "w")
                osglog.LOGFILE = self.log_file
        
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

    # This lets us ignore the leading underscore if we don't specify an actual filename.
    # It also stores the formatted name for our use later, which is handy if we want to
    # create a "master" viewer file or to inform the user which files were actually created.
    def getFullName(self, extension):
        f = "%s%s.%s" % (self.fullpath, self.filename, extension)
#        f = self.fullpath[-1:] == os.sep and "%s%s.%s" % (self.fullpath, self.filename,"osg") or "%s_%s.%s" % (self.fullpath, name,extension)
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
