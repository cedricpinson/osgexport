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


MACRO(BUILD_DATA)
  find_program (BASH_PROGRAM bash)

  IF (${ARGC} EQUAL 1)
    SET(flags "${ARGV0}")
  ELSE (${ARGC} EQUAL 1)
    SET(flags "--enable-animation")
  ENDIF (${ARGC} EQUAL 1)

  # need DATA_SOURCE and DATA_TARGET
  SET(DATA_TARGETNAME ${DATA_TARGET}.osgt)
  ADD_CUSTOM_COMMAND (OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGETNAME}
    COMMAND ${BLENDER}  --background ${DATA_SOURCE} --python osg/__init__.py -- --output="${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGET}" "${flags}"
    COMMAND ${BASH_PROGRAM} -c "[ -f ${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGETNAME} ]"
    WORKING_DIRECTORY ${EXPORTER}
    DEPENDS ${DATA_SOURCE}
    COMMENT "build data from ${DATA_SOURCE}"
    )
  ADD_CUSTOM_TARGET (${DATA_TARGET} ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/${DATA_TARGETNAME})
ENDMACRO(BUILD_DATA)
