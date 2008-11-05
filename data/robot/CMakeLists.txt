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


SET ( DATA_SOURCE
  ${PROJECT_SOURCE_DIR}/data/robot/robot.blend 
  )

SET ( DATA_NAME robot)

IF (BUILD_DATA)

  SET (DATA_BUILD ${DATA_NAME}.osg)
  ADD_CUSTOM_COMMAND (OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${DATA_BUILD}
    COMMAND blender
    ARGS  -b ${DATA_SOURCE} -P osgExport.py 
    --osg="filename=${CMAKE_CURRENT_BINARY_DIR}/${DATA_NAME}\;RELATIVE_PATH=True"
    WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/blenderExporter
    DEPENDS ${DATA_SOURCE}
    COMMENT "build data from " ${DATA_SOURCE}
    )
  ADD_CUSTOM_TARGET (${DATA_NAME} ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${DATA_BUILD})

ENDIF (BUILD_DATA)
