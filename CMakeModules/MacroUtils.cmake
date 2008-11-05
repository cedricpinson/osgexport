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
#  Cedric Pinson <mornifle@plopbyte.net


MACRO(BUILD_DATA)
  # need DATA_SOURCE and DATA_TARGET
  SET(DATA_TARGETNAME ${DATA_TARGET}.osg)
  ADD_CUSTOM_COMMAND (OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGETNAME}
    COMMAND blender
    ARGS  -b ${DATA_SOURCE} -P osgExport.py --osg="filename=${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGET}\;RELATIVE_PATH=True"
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/blenderExporter
    DEPENDS ${DATA_SOURCE}
    COMMENT "build data from ${DATA_SOURCE}"
    )
  ADD_CUSTOM_TARGET (${DATA_TARGET} ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGETNAME})
ENDMACRO(BUILD_DATA)
