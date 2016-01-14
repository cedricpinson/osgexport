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

FILE(COPY
     ${CMAKE_CURRENT_SOURCE_DIR}/cube.blend
     ${CMAKE_CURRENT_SOURCE_DIR}/test.blend
     ${CMAKE_CURRENT_SOURCE_DIR}/test-shadernode.blend
     ${CMAKE_CURRENT_SOURCE_DIR}/test-animation.blend
     DESTINATION ${CMAKE_CURRENT_BINARY_DIR}
)


CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-armature.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-armature.py
  IMMEDIATE @ONLY
  )
#animation is not yet implemented on 2.5
ADD_TEST(NAME "test-armature"
         COMMAND ${BLENDER} --background ${CMAKE_CURRENT_BINARY_DIR}/test.blend --python ${CMAKE_CURRENT_BINARY_DIR}/test-armature.py)

CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-bug_multimaterial.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-bug_multimaterial.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-bug_multimaterial"
         COMMAND ${BLENDER} --background ${CMAKE_CURRENT_BINARY_DIR}/test.blend --python ${CMAKE_CURRENT_BINARY_DIR}/test-bug_multimaterial.py)

CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-geometry_and_material.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-geometry_and_material.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-geometry_and_material"
         COMMAND ${BLENDER} --background ${CMAKE_CURRENT_BINARY_DIR}/test.blend --python ${CMAKE_CURRENT_BINARY_DIR}/test-geometry_and_material.py)


CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-exporter.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-exporter.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-exporter"
         COMMAND ${BLENDER} --background ${CMAKE_CURRENT_BINARY_DIR}/test.blend --python ${CMAKE_CURRENT_BINARY_DIR}/test-exporter.py)


#CONFIGURE_FILE(
#  ${CMAKE_CURRENT_SOURCE_DIR}/test-baked_ipo.py.in
#  ${CMAKE_CURRENT_BINARY_DIR}/test-baked_ipo.py
#  IMMEDIATE @ONLY
#  )
#ADD_TEST("test-bake_ipo" ${BLENDER} -b ${CMAKE_CURRENT_BINARY_DIR}/test.blend -P test-baked_ipo.py --osg="filename=${CMAKE_CURRENT_BINARY_DIR}/${DATA_DEST}\;RELATIVE_PATH=True" )

CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-bug_uvnan.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-bug_uvnan.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-bug_uvnan"
         COMMAND ${BLENDER} --background "${CMAKE_CURRENT_BINARY_DIR}/cube.blend" --python "${CMAKE_CURRENT_BINARY_DIR}/test-bug_uvnan.py")

CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-material.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-material.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-material"
         COMMAND ${BLENDER} --background "${CMAKE_CURRENT_SOURCE_DIR}/../samples/multimaterial/floor.blend" --python "${CMAKE_CURRENT_BINARY_DIR}/test-material.py")

CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-shadernode.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-shadernode.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-shadernode"
         COMMAND ${BLENDER} --background "${CMAKE_CURRENT_BINARY_DIR}/test-shadernode.blend" --python "${CMAKE_CURRENT_BINARY_DIR}/test-shadernode.py")


CONFIGURE_FILE(
  ${CMAKE_CURRENT_SOURCE_DIR}/test-animation.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/test-animation.py
  IMMEDIATE @ONLY
  )
ADD_TEST(NAME "test-animation"
         COMMAND ${BLENDER} --background "${CMAKE_CURRENT_BINARY_DIR}/test-animation.blend" --python "${CMAKE_CURRENT_BINARY_DIR}/test-animation.py")
