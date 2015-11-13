# -*- python-indent: 4; mode: python -*-
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2008-2012 Cedric Pinson
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
#  Cedric Pinson <cedric@plopbyte.com>
#  Jeremy Moles <jeremy@emperorlinux.com>
#  Aurélien Chatelain <chatelain.aurelien@gmail.com>


import bpy
from .osgobject import *

# IMAGES HELPERS
# ----------------------------
def createImageFilename(texturePath, image):
    fn = bpy.path.basename(bpy.path.display_name_from_filepath(image.filepath))

    # for packed file, fallback to image name
    if not fn:
        fn = image.name

    i = fn.rfind(".")
    if i != -1:
        name = fn[0:i]
    else:
        name = fn
    # [BMP, IRIS, PNG, JPEG, TARGA, TARGA_RAW, AVI_JPEG, AVI_RAW, FRAMESERVER]
    if image.file_format == 'PNG':
        ext = "png"
    elif image.file_format == 'HDR':
        ext = "hdr"
    elif image.file_format == 'JPEG':
        ext = "jpg"
    elif image.file_format == 'TARGA' or image.file_format == 'TARGA_RAW':
        ext = "tga"
    elif image.file_format == 'BMP':
        ext = "bmp"
    elif image.file_format == 'AVI_JPEG' or image.file_format == 'AVI_RAW':
        ext = "avi"
    else:
        ext = "unknown"
    name = name + "." + ext
    print("create Image Filename " + name)
    if texturePath != "" and not texturePath.endswith("/"):
        texturePath = texturePath + "/"
    return texturePath + name


def getImageFilesFromStateSet(stateset):
    images = []
    if stateset is not None and len(stateset.texture_attributes) > 0:
        for unit, attributes in stateset.texture_attributes.items():
            for a in attributes:
                if a.className() == "Texture2D":
                    images.append(a.source_image)
    return images


# ARMATURE AND ANIMATION HELPERS
# ----------------------------
def findBoneInHierarchy(scene, bonename):
    if scene.name == bonename and (type(scene) == type(Bone()) or type(scene) == type(Skeleton())):
        return scene

    if isinstance(scene, Group) is False:
        return None

    for child in scene.children:
        result = findBoneInHierarchy(child, bonename)
        if result is not None:
            return result
    return None


def getRootBonesList(armature):
    bones = []
    for bone in armature.bones:
        if bone.parent is None:
            bones.append(bone)
    return bones


def getTransform(matrix):
    return (matrix.translationPart(),
            matrix.scalePart(),
            matrix.toQuat())


def getDeltaMatrixFrom(parent, child):
    if parent is None:
        return child.matrix_world

    return getDeltaMatrixFromMatrix(parent.matrix_world,
                                    child.matrix_world)


def getWidestActionDuration(scene):
    start = min([obj.animation_data.action.frame_range[0] for obj in scene.objects if hasAction(obj)])
    end = max([obj.animation_data.action.frame_range[1] for obj in scene.objects if hasAction(obj)])

    # If scene frame range is wider, use it
    start = min(scene.frame_start, start)
    end = max(scene.frame_end, end)

    return (start, end)


def hasConstraints(blender_object):
        return hasattr(blender_object, "constraints") and (len(blender_object.constraints) > 0)


def hasAction(blender_object):
    return hasattr(blender_object, "animation_data") and \
           hasattr(blender_object.animation_data, "action") and \
           blender_object.animation_data.action is not None

def hasNLATracks(blender_object):
    return hasattr(blender_object, "animation_data") and \
           hasattr(blender_object.animation_data, "nla_tracks") and \
           blender_object.animation_data.nla_tracks


# OBJECTS HELPERS
# ------------------------------
def getDeltaMatrixFromMatrix(parent, child):
    p = parent
    bi = p.copy()
    bi.invert()
    return bi * child


def getChildrenOf(scene, object):
    children = []
    for obj in scene.objects:
        if obj.parent == object:
            children.append(obj)
    return children


def isActionLinkedToObject(action, objects_name):
    action_fcurves = action.fcurves

    for fcurve in action_fcurves:
        path = fcurve.data_path.split("\"")
        if objects_name in path:
            return True
    return False


def unselectAllObjects():
    for obj in bpy.context.selected_objects:
        obj.select = False


def selectObjects(object_list):
    for obj in object_list:
        obj.select = True