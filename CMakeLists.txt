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
#  Jeremy Moles <cubicool@gmail.com>
#  Cedric Pinson <cedric.pinson@plopbyte.com>

PROJECT(osgexporter)

SET(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/CMakeModules/")
CMAKE_MINIMUM_REQUIRED(VERSION 2.4.7)

IF(COMMAND cmake_policy)
  cmake_policy(SET CMP0003 NEW)
ENDIF(COMMAND cmake_policy)

# Let's set up our PACKAGING information.
SET(CPACK_GENERATOR TGZ)
SET(CPACK_SOURCE_GENERATOR TGZ)
SET(CPACK_SOURCE_IGNORE_FILES
	"~$"
	".*.pyc"
	"\\\\.hgignore$"
	"\\\\.hgtags$"
	"\\\\.hg/"
	".*build/"
	".*debug/"
	".*release/"
	".*web/"
)

SET(OSGEXPORTER_VERSION "0.0.1")
SET(CPACK_SOURCE_PACKAGE_FILE_NAME "osgexporter-${OSGEXPORTER_VERSION}")

SET(BLENDER "blender" CACHE FILEPATH "(Absolute) path to blender binary")
SET(EXPORTER "${PROJECT_SOURCE_DIR}/exporter" CACHE FILEPATH "(Absolute) path to exporter modules")
OPTION(TEST "Enable test" OFF)
OPTION(BUILD_DATA "Build samples" ON)

IF(TEST)
  ENABLE_TESTING()
  SET(BUILD_DATA ON)
ENDIF(TEST)


ADD_SUBDIRECTORY(samples)
IF(TEST)
  ADD_SUBDIRECTORY(tests/)
ENDIF(TEST)
