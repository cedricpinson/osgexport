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

import bpy
import mathutils
import json
import math
import os
import shutil
import subprocess

import osg
from . import osglog
from . import osgconf
from .osgconf import DEBUG
from . import osgbake
from . import osgobject
from .osgobject import *
osgobject.VERSION = osg.__version__

Euler = mathutils.Euler
Matrix = mathutils.Matrix
Vector = mathutils.Vector
Quaternion = mathutils.Quaternion


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


def isActionLinkedToObject(action, objects_name):
    action_fcurves = action.fcurves

    for fcurve in action_fcurves:
        path = fcurve.data_path.split("\"")
        if objects_name in path:
            return True
    return False


def findArmatureObjectForTrack(track):
    for o in bpy.data.objects:
        if o.type.lower() == "Armature".lower():
            if list(o.animation_data.nla_tracks).count(track) > 0:
                return 0
    return None


def checkNameEncoding(elements, label, renamed_count):
    for element in elements:
        try:
            element.name
        except UnicodeDecodeError:
            element.name = 'renamed_{}_{}'.format(label, renamed_count)
            renamed_count += 1


def resolveMisencodedNames(scene):
    ''' Replace misencoded object names to avoid errors '''
    scene = bpy.context.scene
    renamed_count = 0

    renamed_count = checkNameEncoding(scene.objects, 'object', renamed_count)
    for obj in scene.objects:
        renamed_count = checkNameEncoding(obj.modifiers, 'modifier', renamed_count)
        renamed_count = checkNameEncoding(obj.vertex_groups, 'vertex_group', renamed_count)

    renamed_count = checkNameEncoding(bpy.data.armatures, 'armature', renamed_count)
    for arm in bpy.data.armatures:
        renamed_count = checkNameEncoding(arm.bones, 'bone', renamed_count)

    renamed_count = checkNameEncoding(bpy.data.materials, 'material', renamed_count)
    renamed_count = checkNameEncoding(bpy.data.textures, 'texture', renamed_count)
    renamed_count = checkNameEncoding(bpy.data.images, 'image', renamed_count)
    renamed_count = checkNameEncoding(bpy.data.curves, 'curve', renamed_count)
    renamed_count = checkNameEncoding(bpy.data.cameras, 'camera', renamed_count)
    renamed_count = checkNameEncoding(bpy.data.lamps, 'lamp', renamed_count)
    renamed_count = checkNameEncoding(bpy.data.metaballs, 'metaball', renamed_count)

    if renamed_count:
        print('Warning: [[blender]] {} entities having misencoded names were renamed'.format(renamed_count))


def unselectAllObjects():
    for obj in bpy.context.selected_objects:
        obj.select = False


def selectObjects(object_list):
    for obj in object_list:
        obj.select = True


def make_dupliverts_real(scene):
    ''' Duplicates vertex instances and makes them real'''
    unselectAllObjects()
    # Select all objects that use dupli_vertex mode
    selectObjects([obj for obj in scene.objects if obj.dupli_type == 'VERTS' and obj.children])

    # Duplicate all instances into real objects
    if bpy.context.selected_objects:
        bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True)
        print('Warning: [[blender]] Some instances (duplication at vertex) were duplicated as real objects')
        # Clear selection
        unselectAllObjects()


# def findObjectForIpo(ipo):
#     index = ipo.name.rfind('-')
#     if index != -1:
#         objname = ipo.name[index+1:]
#         try:
#             obj = self.config.scene.objects[objname]
#             log("bake ipo %s to object %s" % (ipo.name, objname))
#             return obj
#         except:
#             return None
#
#     for o in self.config.scene.objects:
#         if o.getIpo() == ipo:
#             log("bake ipo %s to object %s" % (ipo.name, o.name))
#             return o
#     return None
#
# def findMaterialForIpo(ipo):
#     index = ipo.name.rfind('-')
#     if index != -1:
#         objname = ipo.name[index+1:]
#         try:
#             obj = bpy.data.materials[objname]
#             log("bake ipo %s to material %s" % (ipo.name, objname))
#             return obj
#         except:
#             return None
#
#     for o in bpy.data.materials:
#         if o.getIpo() == ipo:
#             log("bake ipo %s to material %s" % (ipo.name, o.name))
#             return o
#     return None


def createAnimationUpdate(obj, callback, rotation_mode, prefix="", zero=False):
    has_location_keys = False
    has_scale_keys = False
    has_rotation_keys = False

    if obj.animation_data:
        action = obj.animation_data.action

        if action:
            for curve in action.fcurves:
                datapath = curve.data_path[len(prefix):]
                osglog.log("curve.data_path {} {} {}".format(curve.data_path, curve.array_index, datapath))
                if datapath == "location":
                    has_location_keys = True

                if datapath.startswith("rotation"):
                    has_rotation_keys = True

                if datapath == "scale":
                    has_scale_keys = True

    if not (has_location_keys or has_scale_keys or has_rotation_keys) and (len(obj.constraints) == 0):
        return None

    if zero:
        if has_location_keys:
            tr = StackedTranslateElement()
            tr.translate = Vector()
            callback.stacked_transforms.append(tr)

            if has_rotation_keys:
                if rotation_mode in ["XYZ", "XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]:
                    rotation_keys = [StackedRotateAxisElement(name="euler_x", axis=Vector((1, 0, 0)), angle=0),
                                     StackedRotateAxisElement(name="euler_y", axis=Vector((0, 1, 0)), angle=0),
                                     StackedRotateAxisElement(name="euler_z", axis=Vector((0, 0, 1)), angle=0)]

                    callback.stacked_transforms.append(rotation_keys[ord(obj.rotation_mode[2]) - ord('X')])
                    callback.stacked_transforms.append(rotation_keys[ord(obj.rotation_mode[1]) - ord('X')])
                    callback.stacked_transforms.append(rotation_keys[ord(obj.rotation_mode[0]) - ord('X')])

                if rotation_mode == "QUATERNION":
                    q = StackedQuaternionElement()
                    q.quaternion = Quaternion()
                    callback.stacked_transforms.append(q)

                if rotation_mode == "AXIS_ANGLE":
                    callback.stacked_transforms.append(StackedRotateAxisElement(name="axis_angle",
                                                                                axis=Vector((1, 0, 0)),
                                                                                angle=0))
        if has_scale_keys:
            sc = StackedScaleElement()
            sc.scale = Vector(obj.scale)
            callback.stacked_transforms.append(sc)

    else:
        tr = StackedTranslateElement()
        tr.translate = Vector(obj.location)
        callback.stacked_transforms.append(tr)

        if rotation_mode in ["XYZ", "XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]:
            rotation_keys = [StackedRotateAxisElement(name="euler_x", axis=Vector((1, 0, 0)), angle=obj.rotation_euler[0]),
                             StackedRotateAxisElement(name="euler_y", axis=Vector((0, 1, 0)), angle=obj.rotation_euler[1]),
                             StackedRotateAxisElement(name="euler_z", axis=Vector((0, 0, 1)), angle=obj.rotation_euler[2])]

            callback.stacked_transforms.append(rotation_keys[ord(obj.rotation_mode[2]) - ord('X')])
            callback.stacked_transforms.append(rotation_keys[ord(obj.rotation_mode[1]) - ord('X')])
            callback.stacked_transforms.append(rotation_keys[ord(obj.rotation_mode[0]) - ord('X')])

        if rotation_mode == "QUATERNION":
            q = StackedQuaternionElement()
            q.quaternion = obj.rotation_quaternion
            callback.stacked_transforms.append(q)

        if rotation_mode == "AXIS_ANGLE":
            callback.stacked_transforms.append(StackedRotateAxisElement(name="axis_angle",
                                                                        axis=Vector(obj.rotation_axis_angle[0:2]),
                                                                        angle=obj.rotation_axis_angle[3]))

        sc = StackedScaleElement()
        sc.scale = Vector(obj.scale)
        callback.stacked_transforms.append(sc)

    return callback


def createAnimationsGenericObject(osg_object, blender_object, config, update_callback, unique_objects):
    if (config.export_anim is False) or (update_callback is None) or (blender_object.animation_data is None):
        return None

    if unique_objects.hasAnimation(blender_object.animation_data.action):
        return None

    action2animation = BlenderAnimationToAnimation(object=blender_object,
                                                   config=config,
                                                   unique_objects=unique_objects)
    anim = action2animation.createAnimation()
    if len(anim) > 0:
        osg_object.update_callbacks.append(update_callback)
    return anim


def createAnimationMaterialAndSetCallback(osg_node, obj, config, unique_objects):
    osglog.log("Warning: [[blender]] Update material animations are not yet supported")
    return None
    # return createAnimationsGenericObject(osg_node, obj, config, UpdateMaterial(), uniq_anims)


class UniqueObject(object):
    def __init__(self):
        self.statesets = {}
        self.textures = {}
        self.objects = {}
        self.anims = {}

    def hasAnimation(self, obj):
        return obj in self.anims

    def getAnimation(self, obj):
        if self.hasAnimation(obj):
            return self.anims[obj]
        return None

    def registerAnimation(self, obj, reg):
        self.anims[obj] = reg

    def hasObject(self, obj):
        return obj in self.objects

    def getObject(self, obj):
        if self.hasObject(obj):
            return self.objects[obj]
        return None

    def registerObject(self, obj, reg):
        self.objects[obj] = reg

    def hasTexture(self, obj):
        return obj in self.textures

    def getTexture(self, obj):
        if self.hasTexture(obj):
            return self.textures[obj]
        return None

    def registerTexture(self, obj, reg):
        self.textures[obj] = reg

    def hasStateSet(self, obj):
        return obj in self.statesets

    def getStateSet(self, obj):
        if self.hasStateSet(obj):
            return self.statesets[obj]
        return None

    def registerStateSet(self, obj, reg):
        self.statesets[obj] = reg


class Export(object):
    def __init__(self, config=None):
        object.__init__(self)
        self.items = []
        self.config = config
        if self.config is None:
            self.config = osgconf.Config()
            self.config.defaultattr('scene', bpy.context.scene)
        self.rest_armatures = []
        self.animations = []
        self.images = set()
        self.lights = {}
        self.root = None
        self.unique_objects = UniqueObject()

    def isExcluded(self, obj):
        return obj.name in self.config.exclude_objects

    def setArmatureInRestMode(self):
        for arm in bpy.data.objects:
            if arm.type == "ARMATURE":
                print(arm)
                if arm.data.pose_position == 'POSE':
                    arm.data.pose_position = 'REST'
                    self.rest_armatures.append(arm)

    def restoreArmaturePoseMode(self):
        for arm in self.rest_armatures:
            arm.data.pose_position = 'POSE'

    def exportItemAndChildren(self, obj):
        item = self.exportChildrenRecursively(obj, None, None)
        if item is not None:
            self.items.append(item)

    def evaluateGroup(self, obj, item, rootItem):
        if obj.dupli_group is None or len(obj.dupli_group.objects) == 0:
            return

        osglog.log("resolving {} for {} offset {}".format(obj.dupli_group.name,
                                                          obj.name,
                                                          obj.dupli_group.dupli_offset))

        group = MatrixTransform()
        group.matrix = Matrix.Translation(-obj.dupli_group.dupli_offset)
        item.children.append(group)

        # for group we disable the only visible
        config_visible = self.config.only_visible
        self.config.only_visible = False
        for o in obj.dupli_group.objects:
            osglog.log("object {}".format(o))
            self.exportChildrenRecursively(o, group, rootItem)
        self.config.only_visible = config_visible
        # and restore it after processing group

    def getName(self, obj):
        if hasattr(obj, "name"):
            return obj.name
        return "no name"

    def createAnimationsSkeletonObject(self, osg_object, blender_object):
        if (self.config.export_anim is False) or (blender_object.animation_data is None) or (blender_object.animation_data.action is None):
            return None

        if self.unique_objects.hasAnimation(blender_object.animation_data.action):
            return None

        osglog.log("animation_data is {} {}".format(blender_object.name, blender_object.animation_data))

        action2animation = BlenderAnimationToAnimation(object=blender_object, config=self.config, unique_objects=self.unique_objects)
        osglog.log("animations created for object '{}'".format(blender_object.name))

        anims = action2animation.createAnimation()
        return anims

    def createAnimationsObjectAndSetCallback(self, osg_object, blender_object):
        rotation_mode = 'QUATERNION' if self.config.use_quaternions else blender_object.rotation_mode
        return createAnimationsGenericObject(osg_object, blender_object, self.config,
                                             createAnimationUpdate(blender_object,
                                                                   UpdateMatrixTransform(name=osg_object.name),
                                                                   rotation_mode),
                                             self.unique_objects)

    def isObjectVisible(self, obj):
        return obj.is_visible(self.config.scene) or not self.config.only_visible

    def exportChildrenRecursively(self, obj, parent, rootItem):
        # We skip the object if it is in the excluded objects list
        if self.isExcluded(obj):
            return None

        # Check if the object is visible. The visibility will be used for meshes and lights
        # to determine if we keep it or not. Other objects have to be taken into account even if they
        # are not visible as they can be used as modifiers (avoiding some crashs during the export)
        is_visible = self.isObjectVisible(obj)
        osglog.log("")

        anims = []
        item = None
        if self.unique_objects.hasObject(obj):
            osglog.log("use referenced item for {} {}".format(obj.name, obj.type))
            item = self.unique_objects.getObject(obj)
        else:
            osglog.log("Type of {} is {}".format(obj.name, obj.type))
            if obj.type == "ARMATURE":
                item = self.createSkeleton(obj)
                anims = self.createAnimationsSkeletonObject(item, obj)

            elif obj.type == "MESH" or obj.type == "EMPTY" or obj.type == "CAMERA":
                # because it blender can insert inverse matrix, we have to recompute the parent child
                # matrix for our use. Not if an armature we force it to be in rest position to compute
                # matrix in the good space
                matrix = getDeltaMatrixFrom(obj.parent, obj)
                item = MatrixTransform()
                item.setName(obj.name)

                item.matrix = matrix.copy()
                if self.config.zero_translations and parent is None:
                    if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 62:
                        print("zero_translations option has not been converted to blender 2.62")
                    else:
                        item.matrix[3].xyz = Vector()

                anims = self.createAnimationsObjectAndSetCallback(item, obj)

                if is_visible:
                    if obj.type == "MESH":
                        objectItem = self.createGeodeFromObject(obj)
                        item.children.append(objectItem)
                    else:
                        self.evaluateGroup(obj, item, rootItem)

            elif obj.type == "LAMP" and is_visible:
                matrix = getDeltaMatrixFrom(obj.parent, obj)
                item = MatrixTransform()
                item.setName(obj.name)
                item.matrix = matrix
                lightItem = self.createLight(obj)
                anims = self.createAnimationsObjectAndSetCallback(item, obj)
                item.children.append(lightItem)

            else:
                osglog.log("Warning: [[blender]] The object {} (type {}) was not exported".format(obj.name, obj.type))
                return None

            self.unique_objects.registerObject(obj, item)

        if anims is not None:
            self.animations += [a for a in anims if a is not None]

        if rootItem is None:
            rootItem = item

        if obj.parent_type == "BONE":
            bone = findBoneInHierarchy(rootItem, obj.parent_bone)
            if bone is None:
                osglog.log("Warning: [[blender]] {} not found".format(obj.parent_bone))
            else:
                armature = obj.parent.data
                original_pose_position = armature.pose_position
                armature.pose_position = 'REST'

                boneInWorldSpace = obj.parent.matrix_world * armature.bones[obj.parent_bone].matrix_local
                matrix = getDeltaMatrixFromMatrix(boneInWorldSpace, obj.matrix_world)
                item.matrix = matrix
                bone.children.append(item)

                armature.pose_position = original_pose_position

        elif parent:
            parent.children.append(item)

        children = getChildrenOf(self.config.scene, obj)
        for child in children:
            self.exportChildrenRecursively(child, item, rootItem)
        return item

    def createSkeleton(self, obj):
        osglog.log("processing Armature {}".format(obj.name))

        roots = getRootBonesList(obj.data)

        matrix = getDeltaMatrixFrom(obj.parent, obj)
        skeleton = Skeleton(obj.name, matrix)
        for bone in roots:
            b = Bone(obj, bone)
            b.buildBoneChildren()
            skeleton.children.append(b)
        skeleton.collectBones()
        return skeleton

    def preProcess(self):
        # The following process may alter object selection, so
        # we need to save it
        backup_selection = bpy.context.selected_objects

        make_dupliverts_real(self.config.scene)
        resolveMisencodedNames(self.config.scene)

        # restore the user's selection
        unselectAllObjects()
        selectObjects(backup_selection)

    def process(self):
        self.preProcess()

        # Object.resetWriter()
        self.scene_name = self.config.scene.name
        osglog.log("current scene {}".format(self.scene_name))
        if self.config.validFilename() is False:
            self.config.filename += self.scene_name
        self.config.createLogfile()

        self.setArmatureInRestMode()
        try:
            if self.config.object_selected is not None:
                o = bpy.data.objects[self.config.object_selected]
                try:
                    self.config.scene.objects.active = o
                    self.config.scene.objects.selected = [o]
                except ValueError:
                    osglog.log("Error, problem happens when assigning object {} to scene {}".format(o.name, self.config.scene.name))
                    raise

            for obj in self.config.scene.objects:
                osglog.log("obj {}".format(obj.name))
                if (self.config.selected == "SELECTED_ONLY_WITH_CHILDREN" and obj.select) or \
                   (self.config.selected == "ALL" and obj.parent is None):
                    self.exportItemAndChildren(obj)
        finally:
            self.restoreArmaturePoseMode()

        self.postProcess()

    # OSG requires that rig geometry be a child of the skeleton,
    # but Blender does not.  Move any meshes that are modified by
    # an armature to be under the armature.
    def reparentRiggedGeodes(self, item, parent):
        if isinstance(item, MatrixTransform) \
           and len(item.children) == 1 \
           and isinstance(item.children[0], Geode) \
           and not isinstance(parent, Skeleton):
            geode = item.children[0]
            osglog.log("geode {}".format(geode.name))

            # some blend files has a armature_modifier but a None object
            # so we have to test armature_modifier and armature_modifier.object
            if geode.armature_modifier is not None and geode.armature_modifier.object:
                parent.children.remove(item)
                modifier_object = item.children[0].armature_modifier.object

                arm = self.unique_objects.getObject(modifier_object)
                for (k, v) in self.unique_objects.objects.items():
                    if v == item:
                        meshobj = k

                item.matrix = getDeltaMatrixFromMatrix(item.children[0].armature_modifier.object.matrix_world,
                                                       meshobj.matrix_world)

                arm.children.append(item)
                osglog.log("NOTICE: Reparenting {} to {}".format(geode.name, arm.name))
        if hasattr(item, "children"):
            for c in list(item.children):
                self.reparentRiggedGeodes(c, item)

    def postProcess(self):
        # set only one root to the scene
        self.root = None
        self.root = Group()
        self.root.setName("Root")
        self.root.children = self.items
        if len(self.animations) > 0:
            animation_manager = BasicAnimationManager()
            animation_manager.animations = self.animations
            self.root.update_callbacks.append(animation_manager)

        self.reparentRiggedGeodes(self.root, None)

        # index light num for opengl use and enable them in a stateset
        if len(self.lights) > 0:
            st = StateSet()
            self.root.stateset = st
            if len(self.lights) > 8:
                osglog.log("Warning: [[blender]] The model has more than 8 lights")

            # retrieve world to global ambient
            lm = LightModel()
            lm.ambient = (1.0, 1.0, 1.0, 1.0)
            if self.config.scene.world is not None:
                amb = self.config.scene.world.ambient_color
                lm.ambient = (amb[0], amb[1], amb[2], 1.0)

            st.attributes.append(lm)

            # add by default
            st.attributes.append(Material())

            light_num = 0
            for name, ls in self.lights.items():
                ls.light.light_num = light_num
                key = "GL_LIGHT{}".format(light_num)
                st.modes[key] = "ON"
                light_num += 1

        for key in self.unique_objects.statesets.keys():
            stateset = self.unique_objects.statesets[key]
            if stateset is not None:  # register images to unpack them at the end
                images = getImageFilesFromStateSet(stateset)
                for i in images:
                    self.images.add(i)

    def write(self):
        if len(self.items) == 0:
            if self.config.log_file is not None:
                self.config.closeLogfile()
            return

        filename = self.config.getFullName("osgt")
        osglog.log("write file to {}".format(filename))
        with open(filename, "wb") as sfile:
            # sfile.write(str(self.root).encode('utf-8'))
            self.root.writeFile(sfile)

        nativePath = os.path.join(os.path.abspath(self.config.getFullPath()), self.config.texture_prefix)
        # blenderPath = bpy.path.relpath(nativePath)
        if len(self.images) > 0:
            try:
                if not os.path.exists(nativePath):
                    os.mkdir(nativePath)
            except:
                osglog.log("can't create textures directory {}".format(nativePath))
                raise

        copied_images = []
        for i in self.images:
            if i is not None:
                imagename = bpy.path.basename(createImageFilename("", i))
                try:
                    if i.packed_file:
                        original_filepath = i.filepath_raw
                        try:
                            if len(imagename.split('.')) == 1:
                                imagename += ".png"
                            filename = os.path.join(nativePath, imagename)
                            if not os.path.exists(filename):
                                # record which images that were newly copied and can be safely
                                # cleaned up
                                copied_images.append(filename)
                            i.filepath_raw = filename
                            osglog.log("packed file, save it to {}".format(os.path.abspath(bpy.path.abspath(filename))))
                            i.save()
                        except:
                            osglog.log("failed to save file {} to {}".format(imagename, nativePath))
                        i.filepath_raw = original_filepath
                    else:
                        filepath = os.path.abspath(bpy.path.abspath(i.filepath))
                        texturePath = os.path.join(nativePath, imagename)
                        if os.path.exists(filepath):
                            if not os.path.exists(texturePath):
                                # record which images that were newly copied and can be safely
                                # cleaned up
                                copied_images.append(texturePath)
                            shutil.copy(filepath, texturePath)
                            osglog.log("copy file {} to {}".format(filepath, texturePath))
                        else:
                            osglog.log("file {} not available".format(filepath))
                except Exception as e:
                    osglog.log("error while trying to copy file {} to {}: {}".format(imagename, nativePath, e))

        filetoview = self.config.getFullName("osgt")
        if self.config.osgconv_to_ive:
            if self.config.osgconv_embed_textures:
                r = [self.config.osgconv_path, "-O", "includeImageFileInIVEFile", self.config.getFullName("osgt"), self.config.getFullName("ive")]
            else:
                r = [self.config.osgconv_path, "-O", "noTexturesInIVEFile", self.config.getFullName("osgt"), self.config.getFullName("ive")]
            try:
                if subprocess.call(r) == 0:
                    filetoview = self.config.getFullName("ive")
                    if self.config.osgconv_cleanup:
                        os.unlink(self.config.getFullName("osgt"))
                        if self.config.osgconv_embed_textures:
                            for i in copied_images:
                                os.unlink(i)
            except Exception as e:
                print("Error running {}".format(r))
                print(repr(e))

        if self.config.run_viewer:
            r = [self.config.viewer_path, filetoview]
            try:
                subprocess.Popen(r)
            except Exception as e:
                print("Error running {}".format(r))
                print(repr(e))

        if self.config.log_file is not None:
            self.config.closeLogfile()

    def createGeodeFromObject(self, mesh, skeleton=None):
        osglog.log("exporting object {}".format(mesh.name))

        # check if the mesh has a armature modifier
        # if no we don't write influence
        exportInfluence = False

        # if mesh.parent and mesh.parent.type == "ARMATURE":
        #     exportInfluence = True

        armature_modifier = None
        has_non_armature_modifiers = False

        for mod in mesh.modifiers:
            if mod.type == "ARMATURE":
                armature_modifier = mod
            else:
                has_non_armature_modifiers = True

        if armature_modifier is not None:
            exportInfluence = True

        if self.config.apply_modifiers and has_non_armature_modifiers:
            mesh_object = mesh.to_mesh(self.config.scene, True, 'PREVIEW')
        else:
            mesh_object = mesh.data

        osglog.log("mesh_object is {}".format(mesh_object.name))

        if self.unique_objects.hasObject(mesh_object):
            return self.unique_objects.getObject(mesh_object)

        hasVertexGroup = False

        for vertex in mesh_object.vertices:
            if len(vertex.groups) > 0:
                hasVertexGroup = True
                break

        geometries = []
        converter = BlenderObjectToGeometry(object=mesh,
                                            mesh=mesh_object,
                                            config=self.config,
                                            unique_objects=self.unique_objects)
        sources_geometries = converter.convert()

        osglog.log("vertex groups {} {} ".format(exportInfluence, hasVertexGroup))
        if exportInfluence and hasVertexGroup:
            for geom in sources_geometries:
                rig_geom = RigGeometry()
                rig_geom.sourcegeometry = geom
                rig_geom.copyFrom(geom)
                rig_geom.groups = geom.groups
                geometries.append(rig_geom)
        else:
            geometries = sources_geometries

        geode = Geode()
        geode.setName(mesh_object.name)
        geode.armature_modifier = armature_modifier

        if len(geometries) > 0:
            for geom in geometries:
                geode.drawables.append(geom)
            for name in converter.material_animations.keys():
                self.animations.append(converter.material_animations[name])

        self.unique_objects.registerObject(mesh_object, geode)
        return geode

    def createLight(self, obj):
        converter = BlenderLightToLightSource(lamp=obj)
        lightsource = converter.convert()
        self.lights[lightsource.name] = lightsource  # will be used to index lightnum at the end
        return lightsource


class BlenderLightToLightSource(object):
    def __init__(self, *args, **kwargs):
        self.object = kwargs["lamp"]
        self.lamp = self.object.data

    def convert(self):
        ls = LightSource()
        ls.setName(self.object.name)
        light = ls.light
        energy = self.lamp.energy
        light.ambient = (1.0, 1.0, 1.0, 1.0)

        if self.lamp.use_diffuse:
            light.diffuse = (self.lamp.color[0] * energy,
                             self.lamp.color[1] * energy,
                             self.lamp.color[2] * energy,
                             1.0)
        else:
            light.diffuse = (0, 0, 0, 1.0)

        if self.lamp.use_specular:
            light.specular = (energy, energy, energy, 1.0)  # light.diffuse
        else:
            light.specular = (0, 0, 0, 1.0)

        light.getOrCreateUserData().append(StringValueObject("source", "blender"))
        light.getOrCreateUserData().append(StringValueObject("Energy", str(energy)))
        light.getOrCreateUserData().append(StringValueObject("Color", "[{}, {}, {}]".format(self.lamp.color[0],
                                                                                            self.lamp.color[1],
                                                                                            self.lamp.color[2])))

        if self.lamp.use_diffuse:
            light.getOrCreateUserData().append(StringValueObject("UseDiffuse", "true"))
        else:
            light.getOrCreateUserData().append(StringValueObject("UseDiffuse", "false"))

        if self.lamp.use_specular:
            light.getOrCreateUserData().append(StringValueObject("UseSpecular", "true"))
        else:
            light.getOrCreateUserData().append(StringValueObject("UseSpecular", "false"))

        light.getOrCreateUserData().append(StringValueObject("Distance", str(self.lamp.distance)))
        if self.lamp.type == 'POINT' or self.lamp.type == "SPOT":
            light.getOrCreateUserData().append(StringValueObject("FalloffType", str(self.lamp.falloff_type)))
            light.getOrCreateUserData().append(StringValueObject("UseSphere", str(self.lamp.use_sphere).lower()))

        light.getOrCreateUserData().append(StringValueObject("Type", str(self.lamp.type)))

        # Lamp', 'Sun', 'Spot', 'Hemi', 'Area', or 'Photon
        if self.lamp.type == 'POINT' or self.lamp.type == 'SPOT':
            # position light
            # Note DW - the distance may not be necessary anymore (blender 2.5)
            light.position = (0, 0, 0, 1)  # put light to vec3(0) it will inherit the position from parent transform
            light.linear_attenuation = self.lamp.linear_attenuation / self.lamp.distance
            light.quadratic_attenuation = self.lamp.quadratic_attenuation / self.lamp.distance

            if self.lamp.falloff_type == 'CONSTANT':
                light.quadratic_attenuation = 0
                light.linear_attenuation = 0

            if self.lamp.falloff_type == 'INVERSE_SQUARE':
                light.constant_attenuation = 0
                light.linear_attenuation = 0

            if self.lamp.falloff_type == 'INVERSE_LINEAR':
                light.constant_attenuation = 0
                light.quadratic_attenuation = 0

        elif self.lamp.type == 'SUN':
            light.position = (0, 0, 1, 0)  # put light to 0 it will inherit the position from parent transform

        if self.lamp.type == 'SPOT':
            light.spot_cutoff = math.degrees(self.lamp.spot_size * .5)
            if light.spot_cutoff > 90:
                light.spot_cutoff = 180
            light.spot_exponent = 128.0 * self.lamp.spot_blend

            light.getOrCreateUserData().append(StringValueObject("SpotSize", str(self.lamp.spot_size)))
            light.getOrCreateUserData().append(StringValueObject("SpotBlend", str(self.lamp.spot_blend)))

        return ls


class BlenderObjectToGeometry(object):
    def __init__(self, *args, **kwargs):
        self.object = kwargs["object"]
        self.config = kwargs.get("config", osgconf.Config())
        self.unique_objects = kwargs.get("unique_objects", UniqueObject())
        self.geom_type = Geometry
        self.mesh = kwargs.get("mesh", None)

        # if self.config.apply_modifiers is False:
        #     self.mesh = self.object.data
        # else:
        #     self.mesh = self.object.to_mesh(self.config.scene, True, 'PREVIEW')
        self.material_animations = {}

    def createTexture2D(self, mtex):
        image_object = None
        try:
            image_object = mtex.texture.image
        except:
            image_object = None
        if image_object is None:
            osglog.log("Warning: [[blender]] The texture {} is skipped since it has no Image".format(mtex))
            return None

        if self.unique_objects.hasTexture(mtex.texture):
            return self.unique_objects.getTexture(mtex.texture)

        texture = Texture2D()
        texture.name = mtex.texture.name

        # reference texture relative to export path
        filename = createImageFilename(self.config.texture_prefix, image_object)
        texture.file = filename
        texture.source_image = image_object
        self.unique_objects.registerTexture(mtex.texture, texture)
        return texture

    def createTexture2DFromNode(self, node):
        image_object = None
        try:
            image_object = node.image
        except:
            image_object = None
        if image_object is None:
            osglog.log("Warning: [[blender]] The texture node {} is skipped since it has no Image".format(node))
            return None

        if self.unique_objects.hasTexture(node):
            return self.unique_objects.getTexture(node)

        texture = Texture2D()
        texture.name = node.image.name

        # reference texture relative to export path
        filename = createImageFilename(self.config.texture_prefix, image_object)
        texture.file = filename
        texture.source_image = image_object
        self.unique_objects.registerTexture(node, texture)
        return texture

    def adjustUVLayerFromMaterial(self, geom, material, mesh_uv_textures):

        uvs = geom.uvs
        if DEBUG:
            osglog.log("geometry uvs {}".format(uvs))
        geom.uvs = {}

        texture_list = material.texture_slots
        if DEBUG:
            osglog.log("texture list {} - {}".format(len(texture_list), texture_list))

        # find a default channel if exist uv
        default_uv = None
        default_uv_key = None
        if len(mesh_uv_textures) > 0:
            default_uv_key = mesh_uv_textures[0].name
            default_uv = uvs[default_uv_key]

        if DEBUG:
            osglog.log("default uv key {}".format(default_uv_key))

        for texture_id, texture_slot in enumerate(texture_list):
            if texture_slot is not None:
                uv_layer = texture_slot.uv_layer

                if DEBUG:
                    osglog.log("uv layer {}".format(uv_layer))

                if len(uv_layer) > 0 and uv_layer not in uvs.keys():
                    osglog.log("Warning: [[blender]] The material '{}' with texture '{}' use an uv layer '{}' that does not exist on the mesh '{}'; using the first uv channel as fallback".format(material.name, texture_slot, uv_layer, geom.name))
                if len(uv_layer) > 0 and uv_layer in uvs.keys():
                    if DEBUG:
                        osglog.log("texture {} use uv layer {}".format(i, uv_layer))
                    geom.uvs[texture_id] = TexCoordArray()
                    geom.uvs[texture_id].array = uvs[uv_layer].array
                    geom.uvs[texture_id].index = texture_id
                elif default_uv:
                    if DEBUG:
                        osglog.log("texture {} use default uv layer {}".format(i, default_uv_key))
                    geom.uvs[texture_id] = TexCoordArray()
                    geom.uvs[texture_id].index = texture_id
                    geom.uvs[texture_id].array = default_uv.array

        # adjust uvs channels if no textures assigned
        if len(geom.uvs.keys()) == 0:
            if DEBUG:
                osglog.log("no texture set, adjust uvs channels, in arbitrary order")
            for index, k in enumerate(uvs.keys()):
                uvs[k].index = index
            geom.uvs = uvs
        return

    def createStateSet(self, index_material, mesh):
        if len(mesh.materials) == 0:
            return None

        mat_source = mesh.materials[index_material]
        if self.unique_objects.hasStateSet(mat_source):
            return self.unique_objects.getStateSet(mat_source)

        if mat_source is None:
            return None

        stateset = StateSet()
        self.unique_objects.registerStateSet(mat_source, stateset)
        material = Material()
        stateset.attributes.append(material)

        for osg_object in (stateset, material):
            osg_object.dataVariance = "DYNAMIC"
            osg_object.setName(mat_source.name)
            osg_object.getOrCreateUserData().append(StringValueObject("source", "blender"))

        if mat_source.use_nodes is True:
            self.createStateSetShaderNode(mat_source, stateset, material)
        else:
            self.createStateSetMaterial(mat_source, stateset, material)

        return stateset

    def createStateSetShaderNode(self, mat_source, stateset, material):
        """
        Reads a shadernode to an osg stateset/material
        """
        if self.config.json_shaders:
            self.createStateSetShaderNodeJSON(mat_source, stateset, material)
        else:
            self.createStateSetShaderNodeUserData(mat_source, material)

    def createStateSetShaderNodeJSON(self, mat_source, stateset, material):
        """
         Serializes a blender shadernode into a JSON object
        """
        source_tree = mat_source.node_tree

        def createSocket(source_socket):
            socket = {
                "name": source_socket.name,
                "type": source_socket.type,
                "enabled": source_socket.enabled,
                "links": []
            }
            for source_link in source_socket.links:
                socket['links'].append({
                    "from_node": source_link.from_node.name,
                    "from_socket": source_link.from_socket.name,
                    "to_node": source_link.to_node.name,
                    "to_socket": source_link.to_socket.name
                })

            if hasattr(source_socket, 'default_value'):
                value = source_socket.default_value
                if isinstance(value, Vector) or str(type(value)) \
                   in ["<class 'bpy_prop_array'>", "<class 'mathutils.Color'>"]:
                    socket['default_value'] = [v for v in value]
                else:
                    socket['default_value'] = value

            return socket

        tree = {
            "nodes": {}
        }
        texture_slot_id = 0
        for source_node in source_tree.nodes:
            node = {
                "name": source_node.name,
                "type": source_node.type,
                "inputs": [createSocket(source_input) for source_input in source_node.inputs],
                "outputs": [createSocket(source_output) for source_output in source_node.outputs]
            }

            if source_node.type == "TEX_IMAGE" and source_node.image is not None:
                node["texture_mapping"] = {
                    "mapping": source_node.texture_mapping.mapping
                }
                node["image"] = {
                    "filepath_raw": source_node.image.filepath_raw,
                    "use_alpha": source_node.image.use_alpha,
                    "colorspace": source_node.image.colorspace_settings.name,
                    "channels": source_node.image.channels
                }
                node["texture_slot"] = texture_slot_id

                texture = self.createTexture2DFromNode(source_node)
                stateset.texture_attributes.setdefault(texture_slot_id, []).append(texture)
                texture_slot_id += 1

            tree['nodes'][source_node.name] = node

        # safely delete unused nodes
        nodes = tree['nodes']
        for name in list(nodes.keys()):
            node = nodes[name]
            if all(map(lambda socket: len(socket['links']) == 0, node['inputs'])) and \
               all(map(lambda socket: len(socket['links']) == 0, node['outputs'])):
                del nodes[name]

        material.getOrCreateUserData().append(StringValueObject("NodeTree", json.dumps(tree)))

    def createStateSetShaderNodeUserData(self, mat_source, material):
        """
        reads a shadernode to a basic material
        """
        userData = material.getOrCreateUserData()
        for node in mat_source.node_tree.nodes:
            if node.type == "BSDF_DIFFUSE":
                if not node.inputs["Color"].is_linked:
                    value = node.inputs["Color"].default_value
                    userData.append(StringValueObject("DiffuseColor",
                                                      "[{}, {}, {}]".format(value[0],
                                                                            value[1],
                                                                            value[2])))
            elif node.type == "BSDF_GLOSSY":
                if not node.inputs["Color"].is_linked:
                    value = node.inputs["Color"].default_value
                    userData.append(StringValueObject("SpecularColor",
                                                      "[{}, {}, {}]".format(value[0],
                                                                            value[1],
                                                                            value[2])))

    def createStateSetMaterial(self, mat_source, stateset, material):
        """
        Reads a blender material into an osg stateset/material
        """
        anim = createAnimationMaterialAndSetCallback(material, mat_source, self.config, self.unique_objects)
        if anim:
            self.material_animations[anim.name] = anim

        if mat_source.use_shadeless:
            stateset.modes["GL_LIGHTING"] = "OFF"

        alpha = 1.0
        if mat_source.use_transparency:
            alpha = 1.0 - mat_source.alpha

        refl = mat_source.diffuse_intensity
        # we premultiply color with intensity to have rendering near blender for opengl fixed pipeline
        material.diffuse = (mat_source.diffuse_color[0] * refl,
                            mat_source.diffuse_color[1] * refl,
                            mat_source.diffuse_color[2] * refl,
                            alpha)

        # if alpha not 1 then we set the blending mode on
        if DEBUG:
            osglog.log("state material alpha {}".format(alpha))
        if alpha != 1.0:
            stateset.modes["GL_BLEND"] = "ON"

        ambient_factor = mat_source.ambient
        if bpy.context.scene.world:
            material.ambient = ((bpy.context.scene.world.ambient_color[0]) * ambient_factor,
                                (bpy.context.scene.world.ambient_color[1]) * ambient_factor,
                                (bpy.context.scene.world.ambient_color[2]) * ambient_factor,
                                1.0)
        else:
            material.ambient = (0, 0, 0, 1.0)

        # we premultiply color with intensity to have rendering near blender for opengl fixed pipeline
        spec = mat_source.specular_intensity
        material.specular = (mat_source.specular_color[0] * spec,
                             mat_source.specular_color[1] * spec,
                             mat_source.specular_color[2] * spec,
                             1)

        emissive_factor = mat_source.emit
        material.emission = (mat_source.diffuse_color[0] * emissive_factor,
                             mat_source.diffuse_color[1] * emissive_factor,
                             mat_source.diffuse_color[2] * emissive_factor,
                             1)
        material.shininess = (mat_source.specular_hardness / 512.0) * 128.0

        material_data = self.createStateSetMaterialData(mat_source, stateset)

        if self.config.json_materials:
            self.createStateSetMaterialJson(material_data, stateset)
        else:
            self.createStateSetMaterialUserData(material_data, stateset, material)

        return stateset

    def createStateSetMaterialData(self, mat_source, stateset):
        """
        Reads a blender material into an osg stateset/material json userdata
        """
        def premultAlpha(slot, data):
            if slot.texture and slot.texture.image:
                data["UsePremultiplyAlpha"] = slot.texture.image.alpha_mode == 'PREMULT'

        def useAlpha(slot, data):
            if slot.texture and slot.texture.use_alpha:
                data["UseAlpha"] = True

        data = {}

        data["DiffuseIntensity"] = mat_source.diffuse_intensity
        data["DiffuseColor"] = [mat_source.diffuse_color[0],
                                mat_source.diffuse_color[1],
                                mat_source.diffuse_color[2]]

        data["SpecularIntensity"] = mat_source.specular_intensity
        data["SpecularColor"] = [mat_source.specular_color[0],
                                 mat_source.specular_color[1],
                                 mat_source.specular_color[2]]

        data["SpecularHardness"] = mat_source.specular_hardness

        if mat_source.use_shadeless:
            data["Shadeless"] = True
        else:
            data["Emit"] = mat_source.emit
            data["Ambient"] = mat_source.ambient
        data["Translucency"] = mat_source.translucency
        data["DiffuseShader"] = mat_source.diffuse_shader
        data["SpecularShader"] = mat_source.specular_shader
        if mat_source.use_transparency:
            data["Transparency"] = True
            data["TransparencyMethod"] = mat_source.transparency_method

        if mat_source.diffuse_shader == "TOON":
            data["DiffuseToonSize"] = mat_source.diffuse_toon_size
            data["DiffuseToonSmooth"] = mat_source.diffuse_toon_smooth

        if mat_source.diffuse_shader == "OREN_NAYAR":
            data["Roughness"] = mat_source.roughness

        if mat_source.diffuse_shader == "MINNAERT":
            data["Darkness"] = mat_source.roughness

        if mat_source.diffuse_shader == "FRESNEL":
            data["DiffuseFresnel"] = mat_source.diffuse_fresnel
            data["DiffuseFresnelFactor"] = mat_source.diffuse_fresnel_factor

        # specular
        if mat_source.specular_shader == "TOON":
            data["SpecularToonSize"] = mat_source.specular_toon_size
            data["SpecularToonSmooth"] = mat_source.specular_toon_smooth

        if mat_source.specular_shader == "WARDISO":
            data["SpecularSlope"] = mat_source.specular_slope

        if mat_source.specular_shader == "BLINN":
            data["SpecularIor"] = mat_source.specular_ior

        data["TextureSlots"] = {}
        texture_list = mat_source.texture_slots
        if DEBUG:
            osglog.log("texture list {}".format(texture_list))

        for i, texture_slot in enumerate(texture_list):
            if texture_slot is None:
                continue

            texture = self.createTexture2D(texture_slot)
            if DEBUG:
                osglog.log("texture {} {}".format(i, texture_slot))
            if texture is None:
                continue

            data_texture_slot = data["TextureSlots"].setdefault(i, {})

            for (use_map, name, factor) in (('use_map_diffuse', 'DiffuseIntensity', 'diffuse_factor'),
                                            ('use_map_color_diffuse', 'DiffuseColor', 'diffuse_color_factor'),
                                            ('use_map_alpha', 'Alpha', 'alpha_factor'),
                                            ('use_map_translucency', 'Translucency', 'translucency_factor'),
                                            ('use_map_specular', 'SpecularIntensity', 'specular_factor'),
                                            ('use_map_color_spec', 'SpecularColor', 'specular_color_factor'),
                                            ('use_map_mirror', 'Mirror', 'mirror_factor'),
                                            ('use_map_normal', 'Normal', 'normal_factor'),
                                            ('use_map_ambient', 'Ambient', 'ambient_factor'),
                                            ('use_map_emit', 'Emit', 'emit_factor')):
                if getattr(texture_slot, use_map):
                    premultAlpha(texture_slot, data_texture_slot)
                    useAlpha(texture_slot, data_texture_slot)
                    data_texture_slot[name] = getattr(texture_slot, factor)

            # use blend
            data_texture_slot["BlendType"] = texture_slot.blend_type

            stateset.texture_attributes.setdefault(i, []).append(texture)

            try:
                if t.source_image.getDepth() > 24:  # there is an alpha
                    stateset.modes["GL_BLEND"] = "ON"
            except:
                pass

        return data

    def createStateSetMaterialJson(self, data, stateset):
        """
        Serialize blender material data into stateset as a JSON user data
        """
        stateset.getOrCreateUserData().append(StringValueObject("BlenderMaterial",
                                                                json.dumps(data)))

    def createStateSetMaterialUserData(self, data, stateset, material):
        """
        Serialize blender material data into material as a collection of string user data
        """
        def toUserData(value):
            # dict-like values are *not* serialized
            if isinstance(value, (list, tuple)):
                return "[{}]".format(", ".join(toUserData(x) for x in value))
            elif isinstance(value, (int, float, bool)):
                return json.dumps(value)
            elif isinstance(value, str):
                return value
            return None

        userData = material.getOrCreateUserData()

        for key, value in data.items():
            userdata = toUserData(value)
            if userdata is not None:
                userData.append(StringValueObject(key, userdata))

        slot_name = lambda index, label: "{:02}_{}".format(index, label)

        userData = stateset.getOrCreateUserData()
        for index, slot in data["TextureSlots"].items():
            for key, value in slot.items():
                userData.append(StringValueObject(slot_name(index, key), toUserData(value)))

    def createGeometryForMaterialIndex(self, material_index, mesh):
        geom = Geometry()
        geom.groups = {}

        if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 63:
            faces = mesh.tessfaces
        else:
            faces = mesh.faces

        if (len(faces) == 0):
            osglog.log("object {} has no faces, so no materials".format(self.object.name))
            return None
        if len(mesh.materials) and mesh.materials[material_index] is not None:
            material_name = mesh.materials[material_index].name
            title = "mesh {} with material {}".format(self.object.name, material_name)
        else:
            title = "mesh {} without material".format(self.object.name)
        osglog.log(title)

        vertexes = []
        collected_faces = []
        for face in faces:
            if face.material_index != material_index:
                continue
            f = []
            if DEBUG:
                fdebug = []
            for vertex in face.vertices:
                index = len(vertexes)
                vertexes.append(mesh.vertices[vertex])
                f.append(index)
                if DEBUG:
                    fdebug.append(vertex)
            if DEBUG:
                osglog.log("true face {}".format(fdebug))
                osglog.log("face {}".format(f))
            collected_faces.append((face, f))

        if (len(collected_faces) == 0):
            osglog.log("object {} has no faces for sub material slot {}".format(self.object.name, material_index))
            end_title = '-' * len(title)
            osglog.log(end_title)
            return None

        # colors = {}
        # if mesh.vertex_colors:
        #     names = mesh.getColorLayerNames()
        #     backup_name = mesh.activeColorLayer
        #     for name in names:
        #         mesh.activeColorLayer = name
        #         mesh.update()
        #         color_array = []
        #         for face,f in collected_faces:
        #             for i in range(0, len(face.vertices)):
        #                 color_array.append(face.col[i])
        #         colors[name] = color_array
        #     mesh.activeColorLayer = backup_name
        #     mesh.update()
        colors = {}

        vertex_colors = None
        if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 63:
            vertex_colors = mesh.tessface_vertex_colors
        else:
            vertex_colors = mesh.vertex_colors

        if vertex_colors:
            # We only retrieve the active vertex color layer
            colorLayer = vertex_colors.active
            colorArray = []
            idx = 0
            # mesh.update()
            for data in colorLayer.data:
                colorArray.append(data.color1)
                colorArray.append(data.color2)
                colorArray.append(data.color3)
                # DW - how to tell if this is a tri or a quad?
                if len(faces[idx].vertices) > 3:
                    colorArray.append(data.color4)
                idx += 1
            colors = colorArray
            # mesh.update()

        # uvs = {}
        # if mesh.faceUV:
        #     names = mesh.getUVLayerNames()
        #     backup_name = mesh.activeUVLayer
        #     for name in names:
        #         mesh.activeUVLayer = name
        #         mesh.update()
        #         uv_array = []
        #         for face,f in collected_faces:
        #             for i in range(0, len(face.vertices)):
        #                 uv_array.append(face.uv[i])
        #         uvs[name] = uv_array
        #     mesh.activeUVLayer = backup_name
        #     mesh.update()

        uv_textures = None
        if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 63:
            uv_textures = mesh.tessface_uv_textures
        else:
            uv_textures = mesh.uv_textures

        uvs = {}
        if uv_textures:
            backup_texture = None
            for textureLayer in uv_textures:
                if textureLayer.active:
                    backup_texture = textureLayer

            for textureLayer in uv_textures:
                textureLayer.active = True
                # mesh.update()
                uv_array = []

                for face, f in collected_faces:
                    data = textureLayer.data[face.index]
                    uv_array.append(data.uv1)
                    uv_array.append(data.uv2)
                    uv_array.append(data.uv3)
                    if len(face.vertices) > 3:
                        uv_array.append(data.uv4)
                uvs[textureLayer.name] = uv_array
            backup_texture.active = True
            # mesh.update()

        normals = []
        for face, f in collected_faces:
            if face.use_smooth:
                for vert in face.vertices:
                    normals.append(mesh.vertices[vert].normal)
            else:
                for vert in face.vertices:
                    normals.append(face.normal)

        mapping_vertexes = []
        merged_vertexes = []
        tagged_vertexes = []
        for i in range(0, len(vertexes)):
            merged_vertexes.append(i)
            tagged_vertexes.append(False)

        def truncateFloat(value, digit=5):
            if math.isnan(value):
                return 0
            return round(value, digit)

        def truncateVector(vector, digit=5):
            for i in range(0, len(vector)):
                vector[i] = truncateFloat(vector[i], digit)
            return vector

        def get_vertex_key(index):
            return ((truncateFloat(vertexes[index].co[0]),
                     truncateFloat(vertexes[index].co[1]),
                     truncateFloat(vertexes[index].co[2])),
                    (truncateFloat(normals[index][0]),
                     truncateFloat(normals[index][1]),
                     truncateFloat(normals[index][2])),
                    tuple([tuple(truncateVector(uvs[x][index])) for x in uvs.keys()]),
                    tuple([tuple(colors[index]) if colors else ()]))


        # Build a dictionary of indexes to all the vertexes that
        # are equal.
        vertex_dict = {}
        for i in range(0, len(vertexes)):
            key = get_vertex_key(i)
            if DEBUG:
                osglog.log("key {}".format(key))
            if key in vertex_dict.keys():
                vertex_dict[key].append(i)
            else:
                vertex_dict[key] = [i]

        for i in range(0, len(vertexes)):
            if tagged_vertexes[i] is True:  # avoid processing more than one time a vertex
                continue
            index = len(mapping_vertexes)
            merged_vertexes[i] = index
            mapping_vertexes.append([i])
            if DEBUG:
                osglog.log("process vertex {}".format(i))
            vertex_indexes = vertex_dict[get_vertex_key(i)]
            for j in vertex_indexes:
                if j <= i:
                    continue
                if tagged_vertexes[j] is True:  # avoid processing more than one time a vertex
                    continue
                if DEBUG:
                    osglog.log("   vertex {} is the same".format(j))
                merged_vertexes[j] = index
                tagged_vertexes[j] = True
                mapping_vertexes[index].append(j)

        if DEBUG:
            for i in range(0, len(mapping_vertexes)):
                osglog.log("vertex {} contains {}".format(i, mapping_vertexes[i]))

        if len(mapping_vertexes) != len(vertexes):
            osglog.log("vertexes reduced from {} to {}".format(len(vertexes), len(mapping_vertexes)))
        else:
            osglog.log("vertexes {}".format(len(vertexes)))

        faces = []
        for (original, face) in collected_faces:
            f = []
            if DEBUG:
                fdebug = []
            for v in face:
                f.append(merged_vertexes[v])
                if DEBUG:
                    fdebug.append(vertexes[mapping_vertexes[merged_vertexes[v]][0]].index)
            faces.append(f)
            if DEBUG:
                osglog.log("new face {}".format(f))
                osglog.log("true face {}".format(fdebug))

        osglog.log("faces {}".format(len(faces)))

        vgroups = {}
        original_vertexes2optimized = {}
        for i in range(0, len(mapping_vertexes)):
            for k in mapping_vertexes[i]:
                index = vertexes[k].index
                if index not in original_vertexes2optimized.keys():
                    original_vertexes2optimized[index] = []
                original_vertexes2optimized[index].append(i)

        # for i in mesh.getVertGroupNames():
        #    verts = {}
        #    for idx, weight in mesh.getVertsFromGroup(i, 1):
        #        if weight < 0.001:
        #            log( "Warning: [[blender]] " + str(idx) + " to has a weight too small (" + str(weight) + "), skipping vertex")
        #            continue
        #        if idx in original_vertexes2optimized.keys():
        #            for v in original_vertexes2optimized[idx]:
        #                if not v in verts.keys():
        #                    verts[v] = weight
        #                #verts.append([v, weight])
        #    if len(verts) == 0:
        #        log( "Warning: [[blender]] " + str(i) + " has not vertices, skip it, if really unsued you should clean it")
        #    else:
        #        vertex_weight_list = [ list(e) for e in verts.items() ]
        #        vg = VertexGroup()
        #        vg.targetGroupName = i
        #        vg.vertexes = vertex_weight_list
        #        vgroups[i] = vg

        # blenObject = None
        # for obj in bpy.context.blend_data.objects:
        #     if obj.data == mesh:
        #         blenObject = obj

        for vertex_group in self.object.vertex_groups:
            # osglog.log("Look at vertex group: " + repr(vertex_group))
            verts = {}
            for idx, vertices in enumerate(mesh.vertices):
                weight = 0
                for vg in vertices.groups:
                    if vg.group == vertex_group.index:
                        weight = vg.weight
                if weight >= 0.001:
                    if idx in original_vertexes2optimized.keys():
                        for v in original_vertexes2optimized[idx]:
                            if v not in verts.keys():
                                verts[v] = weight

            if len(verts) == 0:
                osglog.log("Warning: [[blender]] The Group {} is skipped since it has no vertices".format(vertex_group.name))
            else:
                vertex_weight_list = [list(e) for e in verts.items()]
                vg = VertexGroup()
                vg.targetGroupName = vertex_group.name
                vg.vertexes = vertex_weight_list
                vgroups[vertex_group.name] = vg

        if (len(vgroups)):
            osglog.log("vertex groups {}".format(len(vgroups)))
        geom.groups = vgroups

        osg_vertexes = VertexArray()
        osg_normals = NormalArray()
        osg_uvs = {}

        # Get the first vertex color layer (only one supported for now)
        osg_colors = ColorArray() if colors else None

        for vertex in mapping_vertexes:
            vindex = vertex[0]
            coord = vertexes[vindex].co
            osg_vertexes.getArray().append([coord[0], coord[1], coord[2]])

            ncoord = normals[vindex]
            osg_normals.getArray().append([ncoord[0], ncoord[1], ncoord[2]])

            if osg_colors is not None:
                osg_colors.getArray().append(colors[vindex])

            for name in uvs.keys():
                if name not in osg_uvs.keys():
                    osg_uvs[name] = TexCoordArray()
                osg_uvs[name].getArray().append(uvs[name][vindex])

        if (len(osg_uvs)):
            osglog.log("uvs channels {} - {}".format(len(osg_uvs), osg_uvs.keys()))

        nlin = 0
        ntri = 0
        nquad = 0
        # counting number of lines, triangles and quads
        for face in faces:
            nv = len(face)
            if nv == 2:
                nlin = nlin + 1
            elif nv == 3:
                ntri = ntri + 1
            elif nv == 4:
                nquad = nquad + 1
            else:
                osglog.log("Warning: [[blender]] Faces with {} vertices are not supported".format(nv))

        # counting number of primitives (one for lines, one for triangles and one for quads)
        numprims = 0
        if (nlin > 0):
            numprims = numprims + 1
        if (ntri > 0):
            numprims = numprims + 1
        if (nquad > 0):
            numprims = numprims + 1

        # Now we write each primitive
        primitives = []
        if nlin > 0:
            lines = DrawElements()
            lines.type = "GL_LINES"
            nface = 0
            for face in faces:
                nv = len(face)
                if nv == 2:
                    lines.indexes.append(face[0])
                    lines.indexes.append(face[1])
                nface = nface + 1
            primitives.append(lines)

        if ntri > 0:
            triangles = DrawElements()
            triangles.type = "GL_TRIANGLES"
            nface = 0
            for face in faces:
                nv = len(face)
                if nv == 3:
                    triangles.indexes.append(face[0])
                    triangles.indexes.append(face[1])
                    triangles.indexes.append(face[2])
                nface = nface + 1
            primitives.append(triangles)

        if nquad > 0:
            quads = DrawElements()
            quads.type = "GL_QUADS"
            nface = 0
            for face in faces:
                nv = len(face)
                if nv == 4:
                    quads.indexes.append(face[0])
                    quads.indexes.append(face[1])
                    quads.indexes.append(face[2])
                    quads.indexes.append(face[3])
                nface = nface + 1
            primitives.append(quads)

        geom.uvs = osg_uvs
        geom.colors = osg_colors
        geom.vertexes = osg_vertexes
        geom.normals = osg_normals
        geom.primitives = primitives
        geom.setName(self.object.name)
        stateset = self.createStateSet(material_index, mesh)
        if stateset is not None:
            geom.stateset = stateset

        if len(mesh.materials) > 0 and mesh.materials[material_index] is not None:
            self.adjustUVLayerFromMaterial(geom, mesh.materials[material_index], uv_textures)

        end_title = '-' * len(title)
        osglog.log(end_title)
        return geom

    def process(self, mesh):
        if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 63:
            mesh.update(calc_tessface=True)

        geometry_list = []
        material_index = 0
        if len(mesh.materials) == 0:
            geom = self.createGeometryForMaterialIndex(0, mesh)
            if geom is not None:
                geometry_list.append(geom)
        else:
            for material in mesh.materials:
                geom = self.createGeometryForMaterialIndex(material_index, mesh)
                if geom is not None:
                    geometry_list.append(geom)
                material_index += 1
        return geometry_list

    def convert(self):
        # looks like this was dropped
        # if self.mesh.vertexUV:
        #     osglog.log("Warning: [[blender]] mesh %s use sticky UV and it's not supported" % self.object.name)

        return self.process(self.mesh)


class BlenderObjectToRigGeometry(BlenderObjectToGeometry):
    def __init__(self, *args, **kwargs):
        BlenderObjectToGeometry.__init__(self, *args, **kwargs)
        self.geom_type = RigGeometry


class BlenderAnimationToAnimation(object):
    def __init__(self, *args, **kwargs):
        self.config = kwargs["config"]
        self.object = kwargs.get("object", None)
        self.unique_objects = kwargs.get("unique_objects", UniqueObject())
        self.animations = None
        self.action = None
        self.action_name = None

    def handleAnimationBaking(self):
        need_bake = False
        if hasattr(self.object, "constraints") and (len(self.object.constraints) > 0) and self.config.bake_constraints:
            osglog.log("Baking constraints " + str(self.object.constraints))
            need_bake = True
        else:
            if hasattr(self.object, "animation_data") and hasattr(self.object.animation_data, "action"):
                self.action = self.object.animation_data.action
                for fcu in self.action.fcurves:
                    for kf in fcu.keyframe_points:
                        if kf.interpolation != 'LINEAR':
                            need_bake = True

        if self.config.bake_animations or need_bake:
            self.action = osgbake.bakeAnimation(self.config.scene, self.object, use_quaternions=self.config.use_quaternions)
            self.action_name = self.action.name

    def createAnimation(self, target=None):
        osglog.log("Exporting animation on object {}".format(self.object))
        if hasattr(self.object, "animation_data") and \
           hasattr(self.object.animation_data, "action") and \
           self.object.animation_data.action is not None:
            self.action_name = self.object.animation_data.action.name

        self.handleAnimationBaking()

        if target is None:
            target = self.object.name

        anim = self.createAnimationFromAction(target, self.action_name, self.action)
        self.unique_objects.registerAnimation(self.action, anim)
        return [anim]

    def createAnimationFromAction(self, target, name, action):
        animation = Animation()
        animation.setName(name)
        if self.object.type == "ARMATURE":
            for bone in self.object.data.bones:
                bname = bone.name
                osglog.log("{} processing channels for bone {}".format(name, bname))
                self.appendChannelsToAnimation(bname, animation, action, prefix=('pose.bones["{}"].'.format(bname)))
        else:
            self.appendChannelsToAnimation(target, animation, action)
        return animation

    def appendChannelsToAnimation(self, target, anim, action, prefix=""):
        channels = exportActionsToKeyframeSplitRotationTranslationScale(target, action, self.config.anim_fps, prefix)
        for channel in channels:
            anim.channels.append(channel)


def getChannel(target, action, fps, data_path, array_indexes):
    times = []
    duration = 0
    fcurves = []

    for array_index in array_indexes:
        for fcurve in action.fcurves:
            # osglog.log("fcurves {} {} matches {} {} ".format(fcurve.data_path,
            #                                                  fcurve.array_index,
            #                                                  data_path,
            #                                                  array_index))
            if fcurve.data_path == data_path and fcurve.array_index == array_index:
                fcurves.append(fcurve)
                # osglog.log("yes")

    if len(fcurves) == 0:
        return None

    for fcurve in fcurves:
        for keyframe in fcurve.keyframe_points:
            if times.count(keyframe.co[0]) == 0:
                times.append(keyframe.co[0])

    if len(times) == 0:
        return None

    channel = Channel()
    channel.target = target

    if len(array_indexes) == 1:
        channel.type = "FloatLinearChannel"
    if len(array_indexes) == 3:
        channel.type = "Vec3LinearChannel"
    if len(array_indexes) == 4:
        channel.type = "QuatSphericalLinearChannel"

    times.sort()

    for time in times:
        realtime = (time) / fps
        osglog.log("time {} {} {}".format(time, realtime, fps))

        # realtime = time
        if realtime > duration:
            duration = realtime

        value = [realtime]
        for fcurve in fcurves:
            value.append(fcurve.evaluate(time))
        channel.keys.append(value)

    return channel


# as for blender 2.49
def exportActionsToKeyframeSplitRotationTranslationScale(target, action, fps, prefix):
    channels = []

    translate = getChannel(target, action, fps, prefix + "location", [0, 1, 2])
    if translate:
        translate.setName("translate")
        channels.append(translate)

    eulerName = ["euler_x", "euler_y", "euler_z"]
    for i in range(0, 3):
        c = getChannel(target, action, fps, prefix + "rotation_euler", [i])
        if c:
            c.setName(eulerName[i])
            channels.append(c)

    quaternion = getChannel(target, action, fps, prefix + "rotation_quaternion", [1, 2, 3, 0])
    if quaternion:
        quaternion.setName("quaternion")
        channels.append(quaternion)

    axis_angle = getChannel(target, action, fps, prefix + "rotation_axis_angle", [1, 2, 3, 0])
    if axis_angle:
        axis_angle.setName("axis_angle")
        channels.append(axis_angle)

    scale = getChannel(target, action, fps, prefix + "scale", [0, 1, 2])
    if scale:
        scale.setName("scale")
        channels.append(scale)

    return channels
