# -*- python-indent: 4; coding: iso-8859-1; mode: python -*-
#
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
#  Cedric Pinson <cedric.pinson@plopbyte.net>
#
# Copyright (C) 2002-2006 Ruben Lopez <ryu@gpul.org>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# You can read the GNU General Public License at http://www.gnu.org
#
#######################################################################

import Blender
import Blender.Mathutils
from   Blender.Mathutils import *
from   Blender import Ipo
from   Blender import BezTriple
import bpy
import sys
import math
from sys import exit

import osg
from osg import osgconf
import osglog
from osgbake import BakeIpoForMaterial, BakeIpoForObject, BakeAction
from osglog import log
from osgobject import *
from osgconf import debug
from osgconf import DEBUG

Vector     = Blender.Mathutils.Vector
Quaternion = Blender.Mathutils.Quaternion
Matrix     = Blender.Mathutils.Matrix
Euler      = Blender.Mathutils.Euler

def getImageFilesFromStateSet(stateset):
    list = []
    if stateset is not None and len(stateset.texture_attributes) > 0:
        for unit, attributes in stateset.texture_attributes.items():
            for a in attributes:
                if a.className() == "Texture2D":
                    list.append(a.source_image)
    return list

def getRootBonesList(armature):
    bones = [bone for bone in armature.bones.values() if not bone.hasParent()]
    return bones

def getTransform(matrix):
    return (matrix.translationPart(), 
            matrix.scalePart(),
            matrix.toQuat())

def getDeltaMatrixFrom(parent, child):
        if parent is None:
                return child.getMatrix('worldspace')

        return getDeltaMatrixFromMatrix(parent.getMatrix('worldspace'), 
                                        child.getMatrix('worldspace'))

def getDeltaMatrixFromMatrix(parent, child):
        p = parent
        bi = p.copy().invert()
        return child * bi


def getChildrenOf(object):
        children = []
	for obj in bpy.data.scenes.active.objects:
                if obj.getParent() == object:
                        children.append(obj)
        return children

def findBoneInHierarchy(scene, bonename):
        if scene.name == bonename and type(scene) == type(Bone()):
                return scene

        #print scene.getName()
        if isinstance(scene, Group) is False:
                return None
        
        for child in scene.children:
                result = findBoneInHierarchy(child, bonename)
                if result is not None:
                        return result
        return None

def isActionLinkedToObject(action, objects_name):
	action_ipos_items = action.getAllChannelIpos().items()
	#log("action ipos " + str(action_ipos_items))
	for obj_name, ipo in action_ipos_items:
		#log("is " + str(obj_name) + " in "+ str(objects_name))
		if obj_name in objects_name:
			return True;
	return False


def findArmatureObjectForAction(action):
    for o in bpy.data.objects:
        if o.getType() == "Armature":
            a = o.getData()
            for bname, bone in a.bones.items():
                if isActionLinkedToObject(action, bname) is True:
                    return o
    return None

def findObjectForIpo(ipo):
    index = ipo.name.rfind('-')
    if index != -1:
        objname = ipo.name[index+1:]
        try:
            obj = bpy.data.scenes.active.objects[objname]
            log("bake ipo %s to object %s" % (ipo.name, objname))
            return obj
        except:
            return None

    for o in bpy.data.scenes.active.objects:
        if o.getIpo() == ipo:
            log("bake ipo %s to object %s" % (ipo.name, o.name))
            return o
    return None

class Export(object):
    def __init__(self, config = None):
        object.__init__(self)
        self.items = []
        self.config = config
        if self.config is None:
            self.config = osgconf.Config()
        self.rest_armatures = {}
        self.animations = {}
        self.images = set()
        self.lights = {}
        self.root = None
        self.uniq_objects = {}

    def setArmatureInRestMode(self):
        for arm in bpy.data.objects:
            if arm.getType() == "Armature":
                self.rest_armatures[arm] = arm.action
                arm.action = None
                for bone_name, rest_bone in arm.getPose().bones.items():
                    rest_bone.quat = Quaternion()
                    rest_bone.loc = Vector(0,0,0)
                    rest_bone.size = Vector(1,1,1)
                arm.getPose().update()

    def restoreArmatureRestMode(self):
        for arm in self.rest_armatures.keys():
            arm.action = self.rest_armatures[arm]
            arm.getPose().update()

    def exportItemAndChildren(self, obj):
        item = self.exportChildrenRecursively(obj, None, None)
        if item is not None:
            self.items.append(item)

    def createAnimationIpo(self, osg_node, obj):
        if self.config.export_anim is not True:
            return

        if obj.getIpo():
            anim = None
            ipo2animation = BlenderIpoOrActionToAnimation(ipo = obj.getIpo(), config = self.config)
            anim = ipo2animation.createAnimationFromIpo(obj.getName())
            self.animations[anim.name] = anim

            update_callback = UpdateTransform()
            update_callback.setName(osg_node.name)
            osg_node.update_callbacks.append(update_callback)

    def evaluateGroup(self, obj, item, rootItem):
        if obj.enableDupGroup is False or obj.DupGroup is None:
            return
        log(str("resolving " + obj.DupGroup.name + " for " + obj.getName()))
        for o in obj.DupGroup.objects:
            log(str("object " + str(o)))
            self.exportChildrenRecursively( o, item, rootItem)

    def exportChildrenRecursively(self, obj, parent, rootItem):
        if obj.getName() in self.config.exclude_objects:
            return None

        item = None
        if self.uniq_objects.has_key(obj):
            log(str("use referenced item for " + obj.getName() + " " + obj.getType()))
            item = ShadowObject(self.uniq_objects[obj])
        else:
            if obj.getType() == "Armature":
                item = self.createSkeletonAndAnimations(obj)
                self.createAnimationIpo(item, obj)
            elif obj.getType() == "Mesh":
                # because it blender can insert inverse matrix, we have to recompute the parent child
                # matrix for our use. Not if an armature we force it to be in rest position to compute
                # matrix in the good space
                matrix = getDeltaMatrixFrom(obj.getParent(), obj)
                item = MatrixTransform()
                item.setName(obj.getName())
                item.matrix = matrix
                objectItem = self.createMesh(obj)
                self.createAnimationIpo(item, obj)
                item.children.append(objectItem)
            elif obj.getType() == "Lamp":
                # because it blender can insert inverse matrix, we have to recompute the parent child
                # matrix for our use. Not if an armature we force it to be in rest position to compute
                # matrix in the good space
                matrix = getDeltaMatrixFrom(obj.getParent(), obj)
                item = MatrixTransform()
                item.setName(obj.getName())
                item.matrix = matrix
                lightItem = self.createLight(obj)
                self.createAnimationIpo(item, obj)
                item.children.append(lightItem)
            elif obj.getType() == "Empty":
                # because it blender can insert inverse matrix, we have to recompute the parent child
                # matrix for our use. Not if an armature we force it to be in rest position to compute
                # matrix in the good space
                matrix = getDeltaMatrixFrom(obj.getParent(), obj)
                item = MatrixTransform()
                item.setName(obj.getName())
                item.matrix = matrix
                self.createAnimationIpo(item, obj)
                self.evaluateGroup(obj, item, rootItem)
            else:
                log(str("WARNING " + obj.getName() + " " + obj.getType() + " not exported"))
                return None
            self.uniq_objects[obj] = item


        if rootItem is None:
            rootItem = item


        if obj.getParentBoneName() is not None:
            bone = findBoneInHierarchy(rootItem, obj.getParentBoneName())
            if bone is None:
                log(str("WARNING " + obj.getParentBoneName() + " not found"))
            else:
                # if parent is a bone we need to compute correctly the matrix from
                # parent bone to object bone
                armature = obj.getParent()
                matrixArmatureInWorldSpace = armature.getMatrix('worldspace')
                matrixBoneinArmatureSpace = bone.matrix['ARMATURESPACE']
                boneInWorldSpace = matrixBoneinArmatureSpace * matrixArmatureInWorldSpace
                matrix = getDeltaMatrixFromMatrix(boneInWorldSpace, obj.getMatrix('worldspace'))
                item.matrix = matrix
                bone.children.append(item)
        elif parent:
            parent.children.append(item)

        children = getChildrenOf(obj)
        for child in children:
            self.exportChildrenRecursively(child, item, rootItem)
        return item


    def createSkeletonAndAnimations(self, obj):
        log("processing Armature " + obj.getName())
        posbones = {}

        for pbone in obj.getPose().bones.values():
            posbones[pbone.name] = pbone

        roots = getRootBonesList(obj.getData())

        matrix = getDeltaMatrixFrom(obj.getParent(), obj)
        skeleton = Skeleton(obj.getName(), matrix)
        for bone in roots:
            b = Bone( obj, bone)
            b.buildBoneChildren()
            skeleton.children.append(b)
        skeleton.collectBones()

        if self.config.export_anim is True:
            for action in bpy.data.actions:
                # check if it's already a baked action (if yes we skip it)
                if action.getName().find("_baked",-len("_baked")) is not -1:
                        continue
                if isActionLinkedToObject(action, posbones.keys()) is True:
                    action2animation = BlenderIpoOrActionToAnimation(action = action, config = self.config)
                    anim = action2animation.createAnimationFromAction()
                    if anim is not None:
                        self.animations[anim.name] = anim
        return skeleton

    def createAnimationsFromList(self, animation_list):
        if DEBUG: debug("create animation from list %s" % (str(animation_list)))
        animations_result = {}
        for anim in animation_list:
            res = None
            if len(list(bpy.data.ipos)) and type(anim) is type(list(bpy.data.ipos)[0]):
                ipo2animation = BlenderIpoOrActionToAnimation(ipo = anim, config = self.config)
                res = ipo2animation.createAnimationFromIpo()

            elif len(list(bpy.data.actions)) and type(anim) is type(list(bpy.data.actions)[0]):
                action2animation = BlenderIpoOrActionToAnimation(action = anim, config = self.config)
                res = action2animation.createAnimationFromAction()
            if res is not None:
                if DEBUG: debug("animation \"%s\" created" % (res.name))
                self.animations[res.name] = res
            else:
                log("WARNING can't create animation from %s" % anim)
                
    def process(self):
        initReferenceCount()
        self.scene_name = bpy.data.scenes.active.name
        if self.config.validFilename() is False:
            self.config.filename += self.scene_name
        self.config.createLogfile()
        self.setArmatureInRestMode()
        if self.config.object_selected != None:
            o = bpy.data.objects[self.config.object_selected]
            bpy.data.scenes.active.objects.active = o
            bpy.data.scenes.active.objects.selected = [o]
        for obj in bpy.data.scenes.active.objects:
            if self.config.selected == "SELECTED_ONLY_WITH_CHILDREN":
                if obj.isSelected():
                    self.exportItemAndChildren(obj)
            else:
                parent = obj.getParent()
                if parent == None or parent not in bpy.data.scenes.active.objects:
                    self.exportItemAndChildren(obj)

        self.restoreArmatureRestMode()
        self.postProcess()

    def postProcess(self):
        # set only one root to the scene
        self.root = None
        self.root = Group()
        self.root.setName("Root")
        self.root.children = self.items
        if len(self.animations) > 0:
            animation_manager = BasicAnimationManager()
            animation_manager.animations = self.animations.values()
            self.root.update_callbacks.append(animation_manager)


        # index light num for opengl use and enable them in a stateset
        if len(self.lights) > 0:
            st = StateSet()
            self.root.stateset = st
            if len(self.lights) > 8:
                log("WARNING more than 8 lights")

            # retrieve world to global ambient
            lm = LightModel()
            lm.ambient = (0.0, 0.0, 0.0, 1.0)
            if bpy.data.scenes.active.world is not None:
                amb = bpy.data.scenes.active.world.getAmb()
                lm.ambient = (amb[0], amb[1], amb[2], 1.0)

            st.attributes.append(lm)
            #st.attributes.append(Material()) # not sure to add a default material with color mode off
            light_num = 0
            for name, ls in self.lights.items():
                ls.light.light_num = light_num
                key = "GL_LIGHT%s" % light_num
                st.modes[key] = "ON"
                light_num += 1
        

    def write(self):
        if len(self.items) == 0:
            if self.config.log_file is not None:
                self.config.closeLogfile()
            return

        filename = self.config.getFullName("osg")
        log("write file to " + filename)
        sfile = file(filename, "wb")
        print >> sfile, self.root

        for i in self.images:
            if i is not None:
                log("unpack file to " + i.getFilename())
                try:
                    i.unpack(Blender.UnpackModes.USE_LOCAL)
                except:
                    log("error while trying to unpack file " + i.getFilename())

        if self.config.log_file is not None:
            self.config.closeLogfile()


    def createMesh(self, mesh, skeleton = None):
        mesh_object  = mesh.getData()
        log("exporting mesh " + mesh.getName())

        geode = Geode()
        geode.setName(mesh.getName())

        # check if the mesh has a armature modifier
        # if no we don't write influence
        exportInfluence = False
        if mesh.parentType is Blender.Object.ParentTypes["ARMATURE"]:
            exportInfluence = True
        if exportInfluence is False:
                #print mesh.getName(), " Modifiers ", len(mesh.modifiers)
            for mod in mesh.modifiers:
                if mod.type == Blender.Modifier.Types["ARMATURE"]:
                    exportInfluence = True
                    break

	hasVertexGroup = len(mesh.getData(False, True).getVertGroupNames()) != 0

        geometries = []
        if exportInfluence is False or hasVertexGroup is False:
            converter = BlenderObjectToGeometry(object = mesh)
            geometries = converter.convert()
        else:
            converter = BlenderObjectToRigGeometry(object = mesh)
            geometries = converter.convert()
        if len(geometries) > 0:
            for geom in geometries:
                if geom.stateset is not None: # register images to unpack them at the end
                    images = getImageFilesFromStateSet(geom.stateset)
                    for i in images:
                        self.images.add(i)
                geode.drawables.append(geom)
        return geode

    def createLight(self, obj):
        converter = BlenderLightToLightSource(lamp=obj)
        lightsource = converter.convert()
        self.lights[lightsource.name] = lightsource # will be used to index lightnum at the end
        return lightsource


class BlenderLightToLightSource(object):
    def __init__(self, *args, **kwargs):
        self.object = kwargs["lamp"]
        self.lamp = self.object.getData()

    def convert(self):
        ls = LightSource()
        ls.setName(self.object.getName())
        light = ls.light
        light.diffuse = (self.lamp.R * self.lamp.getEnergy(), self.lamp.G* self.lamp.getEnergy(), self.lamp.B * self.lamp.getEnergy(),1.0) # put light to 0 it will inherit the position from parent transform
#        light.specular = light.diffuse

        # Lamp', 'Sun', 'Spot', 'Hemi', 'Area', or 'Photon
        if self.lamp.getType() == Blender.Lamp.Types['Lamp'] or self.lamp.getType() == Blender.Lamp.Types['Spot']:
            # position light
            light.position = (0,0,0,1) # put light to 0 it will inherit the position from parent transform
            light.linear_attenuation = self.lamp.quad1 / self.lamp.getDist()
            light.quadratic_attenuation = self.lamp.quad2 / ( self.lamp.getDist() * self.lamp.getDist() )

        elif self.lamp.getType() == Blender.Lamp.Types['Sun']:
            light.position = (0,0,1,0) # put light to 0 it will inherit the position from parent transform

        if self.lamp.getType() == Blender.Lamp.Types['Spot']:
            light.spot_cutoff = self.lamp.getSpotSize() * .5
            if light.spot_cutoff > 90:
                light.spot_cutoff = 180
            light.spot_exponent = 128.0 * self.lamp.getSpotBlend()

        return ls

class BlenderObjectToGeometry(object):
    def __init__(self, *args, **kwargs):
        self.object = kwargs["object"]
        self.geom_type = Geometry
        self.mesh = self.object.getData(False, True)

    def createTexture2D(self, mtex):
        image_object = mtex.tex.getImage()
        if image_object is None:
            log("WARNING the texture %s has not Image, skip it" % mtex.tex.getName())
            return None
        texture = Texture2D()
        texture.name = mtex.tex.getName()
        filename = "//" + Blender.sys.basename(image_object.getFilename().replace(" ","_"))
        texture.file = filename.replace("//","textures/")
        texture.source_image = image_object
        return texture

    def createStateSet(self, index_material, mesh, geom):
        s = StateSet()
        uvs = geom.uvs
        if DEBUG: debug("geometry uvs %s" % (str(uvs)))
        geom.uvs = {}
        if len(mesh.materials) > 0:
            mat_source = mesh.materials[index_material]
            if mat_source is not None:
                m = Material()
                s.setName(mat_source.getName())

                mode = mat_source.getMode()
                if mode & Blender.Material.Modes['SHADELESS']:
                    s.modes["GL_LIGHTING"] = "OFF"

                refl = mat_source.getRef()
                m.diffuse = (mat_source.R * refl, mat_source.G * refl, mat_source.B * refl, mat_source.alpha)

                # if alpha not 1 then we set the blending mode on
                if DEBUG: debug("state material alpha %s" % str(mat_source.alpha))
                if mat_source.alpha != 1.0:
                    s.modes["GL_BLEND"] = "ON"

                ambient_factor = mat_source.getAmb()
                m.ambient = (mat_source.R * ambient_factor, mat_source.G * ambient_factor, mat_source.B * ambient_factor, 1)

                spec = mat_source.getSpec()
                m.specular = (mat_source.specR * spec, mat_source.specG * spec, mat_source.specB * spec, 1)

                emissive_factor = mat_source.getEmit()
                m.emission = (mat_source.R * emissive_factor, mat_source.G * emissive_factor, mat_source.B * emissive_factor, 1)
                m.shininess = (mat_source.getHardness() / 512.0) * 128.0

                s.attributes.append(m)

                texture_list = mat_source.getTextures()
                if DEBUG: debug("texture list %s" % str(texture_list))

                # find a default channel if exist uv
                default_uv = None
                default_uv_key = None
                if (len(uvs)) == 1:
                    default_uv_key = uvs.keys()[0]
                    default_uv = uvs[default_uv_key]
                
                for i in range(0, len(texture_list)):
                    if texture_list[i] is not None:
                        t = self.createTexture2D(texture_list[i])
                        if DEBUG: debug("texture %s %s" % (i, texture_list[i]))
                        if t is not None:
                            if not s.texture_attributes.has_key(i):
                                s.texture_attributes[i] = []
                            uv_layer =  texture_list[i].uvlayer
                            if len(uv_layer) > 0 and not uvs.has_key(uv_layer):
                                log("WARNING your material '%s' with texture '%s' use an uv layer '%s' that does not exist on the mesh '%s', use the first uv channel as fallback" % (mat_source.getName(), t.name, uv_layer, geom.name))
                            if len(uv_layer) > 0 and uvs.has_key(uv_layer):
                                if DEBUG: debug("texture %s use uv layer %s" % (i, uv_layer))
                                geom.uvs[i] = TexCoordArray()
                                geom.uvs[i].array = uvs[uv_layer].array
                                geom.uvs[i].index = i
                            elif default_uv:
                                if DEBUG: debug("texture %s use default uv layer %s" % (i, default_uv_key))
                                geom.uvs[i] = TexCoordArray()
                                geom.uvs[i].index = i
                                geom.uvs[i].array = default_uv.array
                                
                            s.texture_attributes[i].append(t)
                            try:
                                if t.source_image.getDepth() > 24: # there is an alpha
                                    s.modes["GL_BLEND"] = "ON"
                            except:
                                log("can't read the source image file for texture %s" % t)
                if DEBUG: debug("state set %s" % str(s))

        # adjust uvs channels if no textures assigned
        if len(geom.uvs.keys()) == 0:
            if DEBUG: debug("no texture set, adjust uvs channels, in arbitrary order")
            index = 0
            for k in uvs.keys():
                uvs[k].index = index
                index += 1
            geom.uvs = uvs
        return s

    def equalVertices(self, vert1, vert2, vertexes, normals, colors, uvs):
        for i in range(0,3):
            if vertexes[vert1].co[i] > vertexes[vert2].co[i]:
                return 1
            elif vertexes[vert1].co[i] < vertexes[vert2].co[i]:
                return 1

        for i in range(0,3):
            if normals[vert1][i] > normals[vert2][i]:
                return 1
            elif normals[vert1][i] < normals[vert2][i]:
                return 1

        for n in uvs.keys():
            for i in range(0,2):
                if uvs[n][vert1][i] > uvs[n][vert2][i]:
                    return 1
                elif uvs[n][vert1][i] < uvs[n][vert2][i]:
                    return 1

        for n in colors.keys():
            for i in range(0,4):
                if colors[n][vert1][i] > colors[n][vert2][i]:
                    return 1
                elif colors[n][vert1][i] < colors[n][vert2][i]:
                    return 1
        return 0

    def createGeomForMaterialIndex(self, material_index, mesh):
        geom = self.geom_type()
        if (len(mesh.faces) == 0):
            log("object %s has no faces, so no materials" % self.object.getName())
            return None
        if len(mesh.materials):
            title = "mesh %s with material %s" % (self.object.getName(), mesh.materials[material_index])
        else:
            title = "mesh %s without material" % (self.object.getName())
        log(title)

        vertexes = []
        collected_faces = []
        for face in mesh.faces:
            if face.mat != material_index:
                continue
            f = []
            if DEBUG: fdebug = []
            for vertex in face.verts:
                index = len(vertexes)
                vertexes.append(vertex)
                f.append(index)
                if DEBUG: fdebug.append(vertex.index)
            if DEBUG: debug("true face %s" % str(fdebug))
            if DEBUG: debug("face %s" % str(f))
            collected_faces.append((face,f))

        if (len(collected_faces) == 0):
            log("object %s has no faces for sub material slot %s" % (self.object.getName(), str(material_index)))
            end_title = '-' * len(title)
            log(end_title)
            return None

        colors = {}
        if mesh.vertexColors:
            names = mesh.getColorLayerNames()
            backup_name = mesh.activeColorLayer
            for name in names:
                mesh.activeColorLayer = name
                mesh.update()
                color_array = []
                for face,f in collected_faces:
                    for i in range(0, len(face.verts)):
                        color_array.append(face.col[i])
                colors[name] = color_array
            mesh.activeColorLayer = backup_name
            mesh.update()

        uvs = {}
        if mesh.faceUV:
            names = mesh.getUVLayerNames()
            backup_name = mesh.activeUVLayer
            for name in names:
                mesh.activeUVLayer = name
                mesh.update()
                uv_array = []
                for face,f in collected_faces:
                    for i in range(0, len(face.verts)):
                        uv_array.append(face.uv[i])
                uvs[name] = uv_array
            mesh.activeUVLayer = backup_name
            mesh.update()

        normals = []
        for face,f in collected_faces:
            if face.smooth:
                for vert in face.verts:
                    normals.append(vert.no)
            else:
                for vert in face.verts:
                    normals.append(face.no)

        mapping_vertexes = []
        merged_vertexes = []
        tagged_vertexes = []
        for i in range(0,len(vertexes)):
            merged_vertexes.append(i)
            tagged_vertexes.append(False)

        for i in range(0, len(vertexes)):
            if tagged_vertexes[i] is True: # avoid processing more than one time a vertex
                continue
            index = len(mapping_vertexes)
            merged_vertexes[i] = index
            mapping_vertexes.append([i])
            if DEBUG: debug("process vertex %s" % i)
            for j in range(i+1, len(vertexes)):
                if tagged_vertexes[j] is True: # avoid processing more than one time a vertex
                    continue
                different = self.equalVertices(i, j, vertexes, normals, colors, uvs)
                if not different:
                    if DEBUG: debug("   vertex %s is the same" % j)
                    merged_vertexes[j] = index
                    tagged_vertexes[j] = True
                    mapping_vertexes[index].append(j)


        if DEBUG:
            for i in range(0, len(mapping_vertexes)):
                debug("vertex %s contains %s" % (str(i), str(mapping_vertexes[i])))

        if len(mapping_vertexes) != len(vertexes):
            log("vertexes reduced from %s to %s" % (str(len(vertexes)),len(mapping_vertexes)))
        else:
            log("vertexes %s" % str(len(vertexes)))

        faces = []
        for (original, face) in collected_faces:
            f = []
            if DEBUG: fdebug = []
            for v in face:
                f.append(merged_vertexes[v])
                if DEBUG: fdebug.append(vertexes[mapping_vertexes[merged_vertexes[v]][0]].index)
            faces.append(f)
            if DEBUG: debug("new face %s" % str(f))
            if DEBUG: debug("true face %s" % str(fdebug))
            
        log("faces %s" % str(len(faces)))

	vgroups = {}
        original_vertexes2optimized = {}
        for i in range(0, len(mapping_vertexes)):
            for k in mapping_vertexes[i]:
                index = vertexes[k].index
                if not original_vertexes2optimized.has_key(index):
                    original_vertexes2optimized[index] = []
                original_vertexes2optimized[index].append(i)

	for i in mesh.getVertGroupNames():
            verts = {}
            for idx, weight in mesh.getVertsFromGroup(i, 1):
                if weight < 0.001:
                    log( "WARNING " + str(idx) + " to has a weight too small (" + str(weight) + "), skipping vertex")
                    continue
                if original_vertexes2optimized.has_key(idx):
                    for v in original_vertexes2optimized[idx]:
                        if not verts.has_key(v):
                            verts[v] = weight
                        #verts.append([v, weight])
            if len(verts) == 0:
                log( "WARNING " + str(i) + " has not vertexes, skip it, if really unsued you should clean it")
            else:
                vertex_weight_list = [ list(e) for e in verts.items() ]
                vg = VertexGroup()
                vg.targetGroupName = i
                vg.vertexes = vertex_weight_list
                vgroups[i] = vg

        if (len(vgroups)):
            log("vertex groups %s" % str(len(vgroups)))
        geom.groups = vgroups
        
        osg_vertexes = VertexArray()
        osg_normals = NormalArray()
        osg_uvs = {}
        osg_colors = {}
        for vertex in mapping_vertexes:
            vindex = vertex[0]
            coord = vertexes[vindex].co
            osg_vertexes.array.append([coord[0], coord[1], coord[2] ])

            ncoord = normals[vindex]
            osg_normals.array.append([ncoord[0], ncoord[1], ncoord[2]])

            for name in uvs.keys():
                if not osg_uvs.has_key(name):
                    osg_uvs[name] = TexCoordArray()
                osg_uvs[name].array.append(uvs[name][vindex])

        if (len(osg_uvs)):
            log("uvs channels %s - %s" % (len(osg_uvs), str(osg_uvs.keys())))

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
                log("WARNING can't manage faces with %s vertices" % nv)

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
            lines.type = "LINES"
            nface=0
            for face in faces:
                nv = len(face)
                if nv == 2:
                    lines.indexes.append(face[0])
                    lines.indexes.append(face[1])
                nface = nface + 1
            primitives.append(lines)

        if ntri > 0:
            triangles = DrawElements()
            triangles.type = "TRIANGLES"
            nface=0
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
            quads.type = "QUADS"
            nface=0
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
        geom.vertexes = osg_vertexes
        geom.normals = osg_normals
        geom.primitives = primitives
        geom.setName(self.object.getName())
        geom.stateset = self.createStateSet(material_index, mesh, geom)

        end_title = '-' * len(title)
        log(end_title)
        return geom

    def process(self, mesh):
        geometry_list = []
        material_index = 0
        if len(mesh.materials) == 0:
            geom = self.createGeomForMaterialIndex(0, mesh)
            if geom is not None:
                geometry_list.append(geom)
        else:
            for material in mesh.materials:
                geom = self.createGeomForMaterialIndex(material_index, mesh)
                if geom is not None:
                    geometry_list.append(geom)
                material_index += 1
        return geometry_list

    def convert(self):
        if self.mesh.vertexUV:
            log("WARNING mesh %s use sticky UV and it's not supported" % self.object.getName())

        list = self.process(self.mesh)
        return list

class BlenderObjectToRigGeometry(BlenderObjectToGeometry):
    def __init__(self, *args, **kwargs):
        BlenderObjectToGeometry.__init__(self, *args, **kwargs)
        self.geom_type = RigGeometry


class BlenderIpoOrActionToAnimation(object):

    def __init__(self, *args, **kwargs):
        self.ipos = kwargs.get("ipo", None)
        self.action = kwargs.get("action", None)
        self.config = kwargs["config"]
        self.animation = None

    def getTypeOfIpo(self, ipo):
        try:
            ipo.curveConsts['MAT_R']
            return "Material"
        except:
            pass

        try:
            ipo.curveConsts['OB_LOCX']
            return "Object"
        except:
            pass
        return None

    def createAnimationFromIpo(self, name = None):
        ipo = self.ipos
        if name is None:
            name = "unknown"
        ipos_baked = ipo
        if self.config.anim_bake.lower() == "force":
            ipotype = self.getTypeOfIpo(ipo)
            if ipotype == "Object":
                obj = findObjectForIpo(ipo)
                baker = BakeIpoForObject(object = obj, ipo = ipo, config = None)
                ipos_baked = baker.getBakedIpos()
            elif ipotype == "Material":
                mat = findMaterialForIpo(ipo)
                baker = BakeIpoForMaterial(material = mat, ipo = ipo, config = None)
                ipos_baked = baker.getBakedIpos()
            else:
                log("WARNING dont know ipo type %s" % ipo.getName())
        animation = Animation()
        animation.setName(ipo.name + "_ipo")
        self.convertIpoToAnimation(name, animation, ipos_baked)
        self.animation = animation
        return animation

    def createAnimationFromAction(self):
        action = self.action
        # check if it's already a baked action (if yes we skip it)
        if action.getName().find("_baked",-len("_baked")) is not -1:
            return None

        action_name = action.getName()
        armature = findArmatureObjectForAction(action)
        if armature is not None and self.config.anim_bake.lower() == "force":
            baker = BakeAction(armature = armature, action = action, config = self.config)
            action = baker.getBakedAction()

        animation = Animation()
        animation.setName(action_name)
        for obj_name, ipo in action.getAllChannelIpos().items():
            # TODO: I'm not sure what's going on here? :)
            # It means it's an solid object animation.
            if obj_name == 'Object':
                log("WARNING dont support Object Action export (%s)" % action_name)
                return None

            self.convertIpoToAnimation(obj_name, animation, ipo)
        self.animation = animation
        return animation

    def convertIpoToAnimation(self, name, ani, ipo):
        if not ipo:
            ipo = []
        # Or we could call the other "type" here.
        channels = self.exportKeyframeSplitRotationTranslationScale(ipo, self.config.anim_fps)
        for i in channels:
            i.target = name
            ani.channels.append(i)

    def exportKeyframeSplitRotationTranslationScale(self, ipo, fps):
        SUPPORTED_IPOS = (
            'RotX', 'RotY', 'RotZ',
            'QuatW', 'QuatX', 'QuatY', 'QuatZ',
            'LocX', 'LocY', 'LocZ',
            'ScaleX', 'ScaleY', 'ScaleZ'
            'R', 'G', 'B', 'Alpha'
            )

        channels         = []
        channel_times    = {'Rotation': set(), 'Translation': set(), 'Scale': set(), 'Color' : set() }
        channel_names    = {'Rotation': 'rotation', 'Translation': 'position', 'Scale': 'scale', 'Color' : 'color'}
        channel_samplers = {'Rotation': None, 'Translation': None, 'Scale': None, 'Color' : None}
        channel_ipos     = {'Rotation': [], 'Translation': [], 'Scale': [], 'Color': []}
        duration = 0

        for curve in ipo:
            if curve.name not in SUPPORTED_IPOS:
                continue

            elif curve.name[ : 3] == "Rot" or curve.name[ : 4] == "Quat":
                times = channel_times['Rotation']
                channel_ipos['Rotation'].append(curve)

            elif curve.name[ : 3] == "Loc":
                times = channel_times['Translation']
                channel_ipos['Translation'].append(curve)

            elif curve.name[ : 5] == "Scale":
                times = channel_times['Scale']
                channel_ipos['Scale'].append(curve)

            for p in curve.bezierPoints:
                times.add(p.pt[0])

        for key in channel_times.iterkeys():
            time = list(channel_times[key])
            time.sort()
            channel_times[key] = time

            if len(time) > 0:
                channel_samplers[key] = Channel()

        for key in channel_times.iterkeys():
            if channel_samplers[key] is None:
                continue

            times = channel_times[key]

            for time in times:
                realtime = (time - 1) / fps

                if realtime > duration:
                    duration = realtime

                trans = Vector()
                quat  = Quaternion()
                scale = Vector()
                rot   = Euler()
                rtype = None

                            # I know this can be cleaned up...
                for curve in channel_ipos[key]:
                    val       = curve[time]
                    bezPoints = curve.bezierPoints

                    if curve.name == 'LocX':
                        trans[0] = val
                    elif curve.name == 'LocY':
                        trans[1] = val
                    elif curve.name == 'LocZ':
                        trans[2] = val
                    elif curve.name == 'QuatW':
                        quat.w = val
                        rtype  = "Quat"
                    elif curve.name == 'QuatX':
                        quat.x = val
                        rtype  = "Quat"
                    elif curve.name == 'QuatY':
                        quat.y = val
                        rtype  = "Quat"
                    elif curve.name == 'QuatZ':
                        quat.z = val
                        rtype  = "Quat"
                    elif curve.name == 'ScaleX':
                        scale[0] = val
                    elif curve.name == 'ScaleY':
                        scale[1] = val
                    elif curve.name == 'ScaleZ':
                        scale[2] = val
                    elif curve.name == 'RotX':
                        rot.x = val * 10
                        rtype = "Euler"
                    elif curve.name == 'RotY':
                        rot.y = val * 10
                        rtype = "Euler"
                    elif curve.name == 'RotZ':
                        rot.z = val * 10
                        rtype = "Euler"
                    else:
                        continue

                if key == 'Scale':
                    channel_samplers[key].keys.append((realtime, scale[0], scale[1], scale[2]))
                    channel_samplers[key].type = "Vec3"
                    channel_samplers[key].setName("scale")

                elif key == 'Rotation':
                    if rtype == "Quat":
                        quat.normalize()
                        channel_samplers[key].keys.append((realtime, quat.x, quat.y, quat.z, quat.w))
                        channel_samplers[key].type = "Quat"
                        channel_samplers[key].setName("quaternion")

                    elif rtype == "Euler":
                        channel_samplers[key].keys.append((realtime, math.radians(rot.x)  , math.radians(rot.y), math.radians(rot.z) ))
                        channel_samplers[key].type = "Vec3"
                        channel_samplers[key].setName("euler")

                elif key == 'Translation':
                    channel_samplers[key].keys.append((realtime, trans[0], trans[1], trans[2]))
                    channel_samplers[key].type = "Vec3"
                    channel_samplers[key].setName("position")

            channels.append(channel_samplers[key])
            #print channel_samplers[key]
        return channels
