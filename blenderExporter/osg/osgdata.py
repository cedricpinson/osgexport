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
#  Cedric Pinson <mornifle@plopbyte.net>
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
import bpy
import sys
import math
from sys import exit

import osg
from osg import osgconf
import osglog
from osglog import log
from osgobject import *


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

def exportKeyframeSplitRotationTranslationScale(ipo, fps):
	SUPPORTED_IPOS = (
		'RotX', 'RotY', 'RotZ',
		'QuatW', 'QuatX', 'QuatY', 'QuatZ',
		'LocX', 'LocY', 'LocZ',
		'ScaleX', 'ScaleY', 'ScaleZ'
	)
        
	channels         = []
	channel_times    = {'Rotation': set(), 'Translation': set(), 'Scale': set()}
	channel_names    = {'Rotation': 'rotation', 'Translation': 'position', 'Scale': 'scale'}
	channel_samplers = {'Rotation': None, 'Translation': None, 'Scale': None}
	channel_ipos     = {'Rotation': [], 'Translation': [], 'Scale': []}

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

		#log(key)
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
	return channels

def getBakedIpos(obj, ori_ipo, anim_fps):

    ipo=Blender.Ipo.New('Object', ori_ipo.getName() + "_bake")
    ipo.addCurve('LocX')
    ipo.addCurve('LocY')
    ipo.addCurve('LocZ')
    ipo.addCurve('RotX')
    ipo.addCurve('RotY')
    ipo.addCurve('RotZ')
    ipo.addCurve('ScaleX')
    ipo.addCurve('ScaleY')
    ipo.addCurve('ScaleZ')

    ipos = [
        ipo[Ipo.OB_LOCX],
        ipo[Ipo.OB_LOCY],
        ipo[Ipo.OB_LOCZ],
        ipo[Ipo.OB_ROTX], #get the curves in this order
        ipo[Ipo.OB_ROTY],
        ipo[Ipo.OB_ROTZ],
        ipo[Ipo.OB_SCALEX], #get the curves in this order
        ipo[Ipo.OB_SCALEY],
        ipo[Ipo.OB_SCALEZ]
        ]

    start = 0
    end = start + 1
    for i in ipos:
        print i

    return new_ipo
    for frame in range(staframe, endframe+1):
        debug(80,'Baking Frame %i' % frame)
		#tell Blender to advace to frame
        Blender.Set(CURFRAME,frame) # computes the constrained location of the 'real' objects
        if not BATCH: Blender.Redraw() # no secrets, let user see what we are doing
        
		#using the constrained Loc Rot of the object, set the location of the unconstrained clone. Yea! Clones are FreeMen
        key = getLocRot(ob,usrCoord) #a key is a set of specifed exact channel values (LocRotScale) for a certain frame
        key = [a+b for a,b in zip(key, usrDelta)] #offset to the new location

        myframe= frame+myOffset
        Blender.Set(CURFRAME,myframe)
        
        time = Blender.Get('curtime') #for BezTriple
        ipos = addPoint(time,key,ipos) #add this data at this time to the ipos
        debug(100,'%s %i %.3f %.2f %.2f %.2f %.2f %.2f %.2f' % (myipoName, myframe, time, key[0], key[1], key[2], key[3], key[4], key[5]))
    

    new_ipo = animtion_bake_constraints.bakeFrames(obj, new_ipo)
    return new_ipo

def getBakedAction(ob_arm, action, sample_rate):
        #print "test ob action enter ", ob_arm.action
        blender_fps = 25
	if sample_rate > blender_fps:
		sample_rate = blender_fps

	step = blender_fps / sample_rate

	frames      = action.getFrameNumbers()
	start_frame = min(frames)
	end_frame   = max(frames)
	'''
	If you are currently getting IPO's this function can be used to
	return a list of frame aligned bone dictionary's
	
	The data in these can be swaped in for the IPO loc and quat
	
	If you want to bake an action, this is not as hard and the ipo hack can be removed.
	'''
	
	# --------------------------------- Dummy Action! Only for this functon
	backup_action     = ob_arm.action
	backup_frame      = Blender.Get('curframe')
	DUMMY_ACTION_NAME = action.name + "_baked"

	# Get the dummy action if it has no users
	try:
		new_action = bpy.data.actions[DUMMY_ACTION_NAME]
	except:
		new_action = None
	
	if not new_action:
		new_action          = bpy.data.actions.new(DUMMY_ACTION_NAME)
		new_action.fakeUser = False

	POSE_XFORM = [Blender.Object.Pose.LOC, Blender.Object.Pose.ROT, Blender.Object.Pose.SIZE ]
	
	# Each dict a frame
	bake_data = [{} for i in xrange(1+end_frame-start_frame)]
	pose          = ob_arm.getPose()
	armature_data = ob_arm.getData()
	pose_bones    = pose.bones
	
	# --------------------------------- Build a list of arma data for reuse
	armature_bone_data = []
	bones_index        = {}

	for bone_name, rest_bone in armature_data.bones.items():
		pose_bone       = pose_bones[bone_name]
		rest_matrix     = rest_bone.matrix['ARMATURESPACE']
		rest_matrix_inv = rest_matrix.copy().invert()

		armature_bone_data.append([len(bones_index), -1, bone_name, rest_bone, rest_matrix, rest_matrix_inv, pose_bone, None])
		
		bones_index[bone_name] = len(bones_index)
	
	# Set the parent ID's
	for bone_name, pose_bone in pose_bones.items():
		parent = pose_bone.parent

		if parent:
			bone_index   = bones_index[bone_name]
			parent_index = bones_index[parent.name]

			armature_bone_data[bone_index][1] = parent_index
	
	# --------------------------------- Main loop to collect IPO data
	frame_index = 0
	
	for current_frame in xrange(start_frame, end_frame + 1):
		ob_arm.action = action
		Blender.Set('curframe', current_frame)
		ob_arm.action = new_action
		
		for index, parent_index, bone_name, rest_bone, rest_matrix, rest_matrix_inv, pose_bone, ipo in armature_bone_data:
			matrix      = pose_bone.poseMatrix
			parent_bone = rest_bone.parent
			
			if parent_index != -1:
				parent_pose_matrix     = armature_bone_data[parent_index][6].poseMatrix
				parent_bone_matrix_inv = armature_bone_data[parent_index][5]
				matrix                 = matrix * parent_pose_matrix.copy().invert()
				rest_matrix            = rest_matrix * parent_bone_matrix_inv
			
			matrix=matrix * rest_matrix.copy().invert()
			
			pose_bone.quat = matrix.toQuat()
			pose_bone.loc  = matrix.translationPart()
			pose_bone.size  = matrix.scalePart()

			# create a full new action
			pose_bone.insertKey(ob_arm, int(frame_index + 1), POSE_XFORM)
			
		frame_index += step
	
	ob_arm.action = backup_action
	Blender.Set('curframe', backup_frame)

        # if no action was previously set
        # then we put the pose in a rest position to avoid bad matrix when exporting
        # object
        if ob_arm.action is None:
                for bone_name, rest_bone in ob_arm.getPose().bones.items():
                        rest_bone.quat = Quaternion()
                        rest_bone.loc = Vector(0,0,0)
                        rest_bone.size = Vector(1,1,1)
                ob_arm.getPose().update()
        
        #print "test ob action leave ", ob_arm.action
	return new_action

class Export(object):
    def __init__(self, config = None):
        object.__init__(self)
        self.items = {}
        self.config = config
        if self.config is None:
            self.config = osgconf.Config()
        self.rest_armatures = {}
        self.animations = {}
        self.images = set()
        self.lights = {}

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
            self.items[item.name] = item

    def createAnimationIpo(self, osg_node, obj):
        if self.config.export_anim is not True:
            return

        if obj.getIpo():
            anim = None
            anim = self.createAnimationFromIpo(obj.getIpo(), obj.getName())
            self.animations[anim.name] = anim

            update_callback = UpdateTransform()
            update_callback.setName(osg_node.name)
            osg_node.update_callbacks.append(update_callback)

    def exportChildrenRecursively(self, obj, parent, rootItem):
        if obj.getName() in self.config.exclude_objects:
            return None

        item = None
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
        else:
            return None


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
                    anim = self.createAnimationFromAction(action)
                    if anim is not None:
                        self.animations[anim.name] = anim
        return skeleton

    def createAnimationFromAction(self, action):
        # check if it's already a baked action (if yes we skip it)
        if action.getName().find("_baked",-len("_baked")) is not -1:
            return None

        action_name = action.getName()
        armature = findArmatureObjectForAction(action)
        if armature is not None and self.config.anim_bake.lower() == "force":
            action = getBakedAction(armature, action, self.config.anim_fps)

        animation = Animation()
        animation.setName(action_name)
        for obj_name, ipo in action.getAllChannelIpos().items():
            # TODO: I'm not sure what's going on here? :)
            # It means it's an solid object animation.
            if obj_name == 'Object':
                log("Warning dont support Object Action export (%s)" % action_name)
                return None

            self.convertIpoToAnimation(obj_name, animation, ipo)
        return animation

    def createAnimationsFromList(self, animation_list):
        animations_result = {}
        for anim in animation_list:
            res = None
            if len(list(bpy.data.ipos)) and type(anim) is type(list(bpy.data.ipos)[0]):
                res = self.createAnimationFromIpo(anim)
            elif len(list(bpy.data.actions)) and type(anim) is type(list(bpy.data.actions)[0]):
                res = self.createAnimationFromAction(anim)
            if res is not None:
                self.animations[res.name] = res
        

    def createAnimationFromIpo(self, ipo, name = None):
        if name is None:
            name = "unknown"
        ipos_baked = ipo
        if False is True and self.config.anim_bake.lower() == "force":
            ipos_baked = getBakedIpos(obj, ipo, self.config.anim_fps)
        animation = Animation()
        animation.setName(ipo.name + "_ipo")
        self.convertIpoToAnimation(name, animation, ipos_baked)
        return animation

    def convertIpoToAnimation(self, name, ani, ipo):
        if not ipo:
            ipo = []
        # Or we could call the other "type" here.
        channels = exportKeyframeSplitRotationTranslationScale(ipo, self.config.anim_fps)
        for i in channels:
            i.target = name
            ani.channels.append(i)


    def process(self):
        initReferenceCount()
        self.scene_name = bpy.data.scenes.active.name
        if self.config.validFilename() is False:
            self.config.filename += self.scene_name
        self.config.createLogfile()
        self.setArmatureInRestMode()
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
        if len(self.animations) > 0:
                self.root = AnimationManager()
                self.root.setName("Root")
                self.root.animations = self.animations.values()
                self.root.children = self.items.values()
        else:
                self.root = Group()
                self.root.setName("Root")
                self.root.children = self.items.values()

        # index light num for opengl use and enable them in a stateset
        if len(self.lights) > 0:
            st = StateSet()
            self.root.stateset = st
            if len(self.lights) > 8:
                log("warning more than 8 lights")

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
                st.modes.append(("GL_LIGHT%s" % light_num, "ON"))
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
                i.unpack(Blender.UnpackModes.USE_LOCAL)

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

        geometry = None
        if exportInfluence is False or hasVertexGroup is False:
            converter = BlenderObjectToGeometry(object = mesh)
            geometry = converter.convert()
        else:
            converter = BlenderObjectToRigGeometry(object = mesh)
            geometry = converter.convert()
        if geometry is not None:
            if geometry.stateset is not None: # register images to unpack them at the end
                images = getImageFilesFromStateSet(geometry.stateset)
                for i in images:
                    self.images.add(i)
            geode.drawables.append(geometry)
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
            light.spot_cutoff = self.lamp.getSpotSize()
            light.spot_exponent = 128.0 * self.lamp.getSpotBlend()

        return ls

class BlenderObjectToGeometry(object):
    def __init__(self, *args, **kwargs):
        self.object = kwargs["object"]
        self.mesh = self.object.getData()
        self.vertexes = None
        self.faceVertexes2Index = None
        self.geometry = None
        self.uvs = {}

    def hasTexture(self):
        return self.getTextureImage() != None

    def getTextureImage(self):
        texture = None    
        for f in self.mesh.faces:
            if f.image != None:
                texture = f.image; break
                #texture = f.image.getFilename().replace(" ","_");break #access to the full pathnam
                #texture = Blender.sys.expandpath(f.image.filename).replace(" ","_");break #access to the full pathnam
        return texture

    def createStateSet(self):
        s = StateSet()
        image_object = self.getTextureImage()
        if image_object is not None:
            texture = Texture2D()
            #filename = image_object.getFilename().replace(" ","_")
            filename = "//" + Blender.sys.basename(image_object.getFilename().replace(" ","_"))
            texture.file = filename.replace("//","textures/")
            if image_object.getDepth() > 24: # there is an alpha
                s.modes.append(("GL_BLEND","ON"))
            texture.source_image = image_object
            s.texture_attributes['0'].append(texture)
        if len(self.mesh.materials) > 0:
            # support only one material by mesh right now
            mat_source = self.mesh.materials[0]
            m = Material()
            refl = mat_source.getRef()
            m.diffuse = (mat_source.R * refl, mat_source.G * refl, mat_source.B * refl, mat_source.alpha)

            ambient_factor = mat_source.getAmb()
            m.ambient = (mat_source.R * ambient_factor, mat_source.G * ambient_factor, mat_source.B * ambient_factor, 1)

            spec = mat_source.getSpec()
            m.specular = (mat_source.specR * spec, mat_source.specG * spec, mat_source.specB * spec, 1)

            emissive_factor = mat_source.getEmit()
            m.emission = (mat_source.R * emissive_factor, mat_source.G * emissive_factor, mat_source.B * emissive_factor, 1)
            m.shininess = (mat_source.getHardness() / 512.0) * 128.0

            s.attributes.append(m)
        return s

    def compVertices(self, face1, vert1, face2, vert2):
        if (not face1.smooth) or (not face2.smooth): return 0
        if (len(face1.uv) != len(face2.uv)): return 0
        if (len(face1.col) != len(face2.col)): return 0

        if (len(face1.uv) == len(face1.v)):
            if face1.uv[vert1][0] != face2.uv[vert2][0]: return 0
            if face1.uv[vert1][1] != face2.uv[vert2][1]: return 0
        if (len(face1.col) == len(face1.v)):
            if face1.col[vert1].r != face2.col[vert2].r: return 0
            if face1.col[vert1].g != face2.col[vert2].g: return 0
            if face1.col[vert1].b != face2.col[vert2].b: return 0
            if face1.col[vert1].a != face2.col[vert2].a: return 0
        return 1

    def calcVertices(self, faces, vertices, hasTcoords):
        result=[] # list of osg vertices, contains the vertex index and a normal
        mapping=[] # internal map, to find duplicates
        mapping_result=[] # resulting mapping [face][vertex] -> osg_vertex index
        for v in vertices:
            mapping.append([])

        curf=0
        vreal=0
        for face in faces:
            curv=0
            local_map = [] # osg indexes for each vertex
            for vertex in face.v:
                vindex = vertex.index
                found=0
                for f in mapping[vindex]:
                    if self.compVertices(face, curv, faces[f[0]], f[1]) == 1:
                        found=1
                        mapping[vindex].append([curf, curv, f[2]])
                        local_map.append(f[2])
                        break
                if found == 0:
                    mapping[vindex].append([curf, curv, vreal])
                    local_map.append(vreal)
                    if face.smooth: result.append([vindex, vertices[vindex].no])
                    else: result.append([vindex, face.no])
                    vreal = vreal + 1
                curv = curv + 1
            curf = curf + 1
            mapping_result.append(local_map)
        self.faceVertexes2Index = mapping_result
        return [result,mapping_result]


    def makeVertices(self, vertices, osg_vertices):
        vec3array = VertexArray()
        normalarray = NormalArray()
        for vertex in osg_vertices:
            coord=vertices[vertex[0]].co
            vec3array.array.append([coord[0], coord[1], coord[2] ])

        for vertex_normal in osg_vertices:
            ncoord=vertex_normal[1]
            normalarray.array.append([ncoord[0], ncoord[1], ncoord[2]])

        self.vertexes = vec3array
        self.normals = normalarray


    def convert(self):
        geom = Geometry()
        [result, mapping] = self.calcVertices(self.mesh.faces, self.mesh.verts, self.hasTexture() )
        self.vertexMapping = (result, mapping)
        self.makeVertices(self.mesh.verts, result)
        ok = self.makeFaces(self.mesh.faces, result, mapping, self.hasTexture())
        if not ok:
                return None
        geom.vertexes = self.vertexes
        geom.normals = self.normals
        geom.uvs = self.uvs
        geom.primitives = self.primitives
        geom.setName(self.object.getName())
        geom.stateset = self.createStateSet()
        self.geometry = geom
        return geom

    def makeFaces(self, faces, vertices_osg, mapping, hasTcoords):
        if (len(faces) == 0):
            log("objest %s has no faces" % self.object.getName())
            return False

        nlin = 0
        ntri = 0
        nquad = 0
        # counting number of lines, triangles and quads
        for face in faces:
            nv = len(face.v)
            if nv == 2:
                nlin = nlin + 1
            elif nv == 3:
                ntri = ntri + 1
            elif nv == 4:
                nquad = nquad + 1
            else:
                print "Can't manage faces with %s vertices" % nv

        # counting number of primitives (one for lines, one for triangles and one for quads)
        numprims = 0
        if (nlin > 0):
            numprims = numprims + 1
        if (ntri > 0):
            numprims = numprims + 1
        if (nquad > 0):
            numprims = numprims + 1

        # Now we write each primitive
        self.primitives = []
        if nlin > 0:
            lines = DrawElements()
            lines.type = "LINES"
            nface=0
            for face in faces:
                vlist=face.v
                nv=len(vlist)
                if nv == 2:
                    lines.indexes.append(mapping[nface][0])
                    lines.indexes.append(mapping[nface][1])
                nface = nface + 1

            self.primitives.append(lines)

        if ntri > 0:
            triangles = DrawElements()
            triangles.type = "TRIANGLES"
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 3:
                    triangles.indexes.append(mapping[nface][0])
                    triangles.indexes.append(mapping[nface][1])
                    triangles.indexes.append(mapping[nface][2])
              nface = nface + 1

            self.primitives.append(triangles)

        if nquad > 0:
            quads = DrawElements()
            quads.type = "QUADS"
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 4:
                    quads.indexes.append(mapping[nface][0])
                    quads.indexes.append(mapping[nface][1])
                    quads.indexes.append(mapping[nface][2])
                    quads.indexes.append(mapping[nface][3])
              nface = nface + 1

            self.primitives.append(quads)

        if hasTcoords:
            self.uvs['0'] = TexCoordArray()

            # Calculating per-vertex texture coordinates
            tc = self.uvs['0']
            for v in vertices_osg:
              tc.array.append( (0,0) )

            curface=0
            for face in faces:
                curv=0
                if (len(face.uv) == len(face.v)):
                    for vertex in face.v:
                        if (curv < 4):
                            tc.array[ mapping[curface][curv] ] = face.uv[curv]
                        curv = curv + 1
                curface = curface + 1

        if faces[0].col:
            self.colors = []
            # Calculating per-vertex colors
            vc = self.colors
            for v in vertices_osg:
              vc.append( (0,0,0,0) )

            curface=0
            for face in faces:
                curv=0
                if (len(face.col) >= len(face.v)):
                    for vertex in face.v:
                        if (curv < 4):
                            vc[ mapping[curface][curv] ] = (face.col[curv].r/255.0, face.col[curv].g/255.0, face.col[curv].b/255.0, face.col[curv].a/255.0)
                        curv = curv + 1
                else:
                    log( str(len(face.col)) + " aren't enough colors for " + str(len(face.v)) + " vertices in one face!")
                curface = curface + 1

        return True

class BlenderObjectToRigGeometry(BlenderObjectToGeometry):
    def __init__(self, *args, **kwargs):
        BlenderObjectToGeometry.__init__(self, *args, **kwargs)
        self.groups = None

    def convert(self):
        geom = RigGeometry()
        [result, mapping] = self.calcVertices(self.mesh.faces, self.mesh.verts, self.hasTexture() )
        self.vertexMapping = (result, mapping)
        self.makeVertices(self.mesh.verts, result)
        self.makeInluence(result)
        ok = self.makeFaces(self.mesh.faces, result, mapping, self.hasTexture())
        if ok is False:
            return None
        geom.vertexes = self.vertexes
        geom.normals = self.normals
        geom.primitives = self.primitives
        geom.uvs = self.uvs
        geom.groups = self.groups
        geom.setName(self.object.getName())
        geom.stateset = self.createStateSet()
        self.geometry = geom
        return geom

    def makeInluence(self, resultVertexes):
	mesh = self.object.getData(False, True)
	groups = mesh.getVertGroupNames()

	skin = {}
	blender2osg = {}
        
	for i in range(0,len(resultVertexes)):
		osgIndex     = i
		blenderIndex = resultVertexes[i][0]
                if not blender2osg.has_key(blenderIndex):
                        blender2osg[blenderIndex] = []
		blender2osg[blenderIndex].append(osgIndex)
        
	for i in groups:
		#log(i)
		vertexes = []
		for idx, weight in mesh.getVertsFromGroup(i, 1):
			if weight < 0.001:
				log( "warning " + str(idx) + " to has a weight too small (" + str(weight) + "), skipping vertex")
				continue
                        for v in blender2osg[idx]:
                                vertexes.append([v, weight])
                if len(vertexes) == 0:
                        log( "warning " + str(i) + " has not vertexes, skip it, if really unsued you should clean it")
                else:
                        vg = VertexGroup()
                        vg.targetGroupName = i
                        vg.vertexes = vertexes
                        skin[i] = vg
        self.groups = skin


    

#######################################################################
######### Class OSG: Allows creating the different OSG nodes ##########
#######################################################################
class OSG:

    def __init__(self, *args, **kwargs):
        self.registry = kwargs.get("osg",defaultKeyRegistryOSG())


    def makeRef(self, refUniqueID):
        return ["  Use %s" % refUniqueID.replace(" ","_")]

#######################################################################
    def makeNodeContents(self, name, uniqueID):
        text = ["  UniqueID \"%s\"" % (uniqueID.replace(" ","_")),
                "  DataVariance DYNAMIC",
                "  name \"%s\"" % (name),
                "  cullingActive TRUE"]
        return text

#######################################################################
    def makeGroupContents(self, name, uniqueID, children):
        text = self.makeNodeContents(name, uniqueID)
        text.append("  num_children %d" % (len(children)))
        for child in children:
            text = text + child
        return text

#######################################################################
    def makeGroup(self, name, uniqueID, children):
        text = ["Group {"]
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeSwitch(self, name, uniqueID, children, values):
        text = ["Switch {",
                "  ValueList {"]
        text = text + values
        text.append("  }")
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeSequence(self, name, uniqueID, children, times, loopMode):
        text = ["Sequence {",
                "  frameTime {"]
        text = text + times
        text.append("  }")

        text.append("  interval %s 0 %s" % (loopMode, (len(children)-1)))
        text.append("  duration 1 -1")
        text.append("  mode START")

        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeMatrixTransform(self, name, uniqueID, children, matrix):
        text = ["MatrixTransform {",
                "  StateSet { 0xba1 ON }",
                "  Matrix {",
                "    DataVariance DYNAMIC",
                "    %s %s %s %s" % (matrix[0][0], matrix[0][1],
                                     matrix[0][2], matrix[0][3]),
                "    %s %s %s %s" % (matrix[1][0], matrix[1][1],
                                     matrix[1][2], matrix[1][3]),
                "    %s %s %s %s" % (matrix[2][0], matrix[2][1],
                                     matrix[2][2], matrix[2][3]),
                "    %s %s %s %s" % (matrix[3][0], matrix[3][1],
                                     matrix[3][2], matrix[3][3]),
                "  }"]
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text
#######################################################################
    def makeAnimationPathTransform(self, name, uniqueID, children, animCallback):
        text = ["MatrixTransform {",
                "  StateSet { 0xba1 ON }",
                "  UpdateCallbacks {"]
        text = text + animCallback
        text.append("  }")
        text = text + self.makeGroupContents(name, uniqueID, children)
        text.append("}")
        return text

#######################################################################
    def makeMaterial(self, material):
        text=[]
        text.append("      Material {")
        text.append("        DataVariance STATIC")
        text.append("        ColorMode OFF")
        text.append("        diffuseColor %s %s %s %s" % (material.R,\
                                                          material.G,\
                                                          material.B,\
                                                          material.alpha))
        # Blender doesn't have a concept of Ambient color in its lighting model
        # or user interface, but it's often important for OSG/OpenGL rendering.
        # If we just omit it, OSG will use default Ambient (grey).  This gives the
        # user a chance to assume that Ambient is a reduced brightness version of Diffuse.
        if self.registry['do_ambient'] == 1:
            ratio = d['ambient_ratio']
            text.append("        ambientColor %s %s %s %s" % (material.R * ratio,\
                                                                material.G * ratio,\
                                                                material.B * ratio,\
                                                                1))
        text.append("        specularColor %s %s %s %s" % (material.specCol[0],\
                                                                 material.specCol[1],\
                                                                 material.specCol[2],\
                                                                 1))
        text.append("        emissionColor %s %s %s %s" % (material.R*material.emit,\
                                                                 material.G*material.emit,\
                                                                 material.B*material.emit,\
                                                                 1))
        text.append("        shininess %s" % str((material.getHardness()-1) / 255.0 * 128))
        text.append("      }")
        return text

#######################################################################
    def makeTexture(self, texture):
        text=["      textureUnit 0 {",
              "        GL_TEXTURE_2D ON",
              "        Texture2D {",
              "          DataVariance STATIC",
              "          file \"%s\"" % texture,
              "          wrap_s REPEAT",
              "          wrap_t REPEAT",
              "          wrap_r CLAMP",
              "          min_filter LINEAR_MIPMAP_LINEAR",
              "          mag_filter LINEAR",
              "          maxAnisotropy 1",
              "          internalFormatMode USE_IMAGE_DATA_FORMAT",
              "        }",
              "      }"]
        # Textured surfaces also need a material, so that they can be lit.
        # Without a material, OpenGL can't know how to light it.  These values
        # are exposed in the exporter UI to let the user choose what works best
        # for their needs.
        if self.registry['do_texmat'] == 1:
            text.append("      Material {")
            text.append("        DataVariance STATIC")
            text.append("        ColorMode OFF")
            text.append("        diffuseColor %.3f %.3f %.3f 1" % self.registry['color1'])
            text.append("        ambientColor %.3f %.3f %.3f 1" % self.registry['color2'])
            text.append("      }")
        return text

#######################################################################
    def makeStateSet(self, uniqueID, texture, materials):
        if (len(materials) and materials[0].alpha < 1.0):
            hint="TRANSPARENT_BIN"
            blend="ON"
        else:
            hint="OPAQUE_BIN"
            blend="OFF"

        text = ["    StateSet {",
                "      UniqueID %s" % uniqueID.replace(" ","_"),
                "      DataVariance STATIC",
                "      rendering_hint %s" % hint,
                "      GL_BLEND %s" % blend]
        if len(materials):
            text = text + self.makeMaterial(materials[0])
        if texture:
            text = text + self.makeTexture(texture)
        text.append("    }")
        return text

#######################################################################
    def makeGeode(self, name, uniqueID, vertices, faces, stateSet, hasTcoords):
        text=["Geode {"];
        text = text + self.makeNodeContents(name, uniqueID)
        text.append("  num_drawables 1")
        text.append("  Geometry {")
        text = text + stateSet

        [result,mapping] = self.calcVertices(faces,vertices,hasTcoords)
        self.vertexMapping = (result, mapping)
        text = text + self.makeVertices(vertices, result)
        text = text + self.makeFaces(faces, result, mapping, hasTcoords)
        text.append("  }")
        text.append("}")
        return text

#######################################################################
    def compVertices(self, face1, vert1, face2, vert2):
        if (not face1.smooth) or (not face2.smooth): return 0
        if (len(face1.uv) != len(face2.uv)): return 0
        if (len(face1.col) != len(face2.col)): return 0

        if (len(face1.uv) == len(face1.v)):
            if face1.uv[vert1][0] != face2.uv[vert2][0]: return 0
            if face1.uv[vert1][1] != face2.uv[vert2][1]: return 0
        if (len(face1.col) == len(face1.v)):
            if face1.col[vert1].r != face2.col[vert2].r: return 0
            if face1.col[vert1].g != face2.col[vert2].g: return 0
            if face1.col[vert1].b != face2.col[vert2].b: return 0
            if face1.col[vert1].a != face2.col[vert2].a: return 0
        return 1

    # Calculates OSG vertices based on blender vertices and blender faces.
    # duplicates vertices that have different per-face properties
#######################################################################
    def calcVertices(self, faces, vertices, hasTcoords):
        result=[] # list of osg vertices
        mapping=[] # internal map, to find duplicates
        mapping_result=[] # resulting mapping [face][vertex] -> osg_vertex index
        for v in vertices:
            mapping.append([])

        curf=0
        vreal=0
        for face in faces:
            curv=0
            local_map = [] # osg indexes for each vertex
            for vertex in face.v:
                vindex = vertex.index
                found=0
                for f in mapping[vindex]:
                    if self.compVertices(face, curv, faces[f[0]], f[1]) == 1:
                        found=1
                        mapping[vindex].append([curf, curv, f[2]])
                        local_map.append(f[2])
                        break
                if found == 0:
                    mapping[vindex].append([curf, curv, vreal])
                    local_map.append(vreal)
                    if face.smooth: result.append([vindex, vertices[vindex].no])
                    else: result.append([vindex, face.no])
                    vreal = vreal + 1
                curv = curv + 1
            curf = curf + 1
            mapping_result.append(local_map)
        return [result,mapping_result]

#######################################################################
    def makeVertices(self, vertices, osg_vertices_normals):
        text=[]
        text.append("    VertexArray %s {" % len(osg_vertices_normals))
        for vertex_normal in osg_vertices_normals:
            coord=vertices[vertex_normal[0]].co
            text.append("      %s %s %s" %
                            (coord[0], coord[1], coord[2]))
        text.append("    }")
        text.append("    NormalBinding PER_VERTEX")
        text.append("    NormalArray %s {" % len(osg_vertices_normals))
        for vertex_normal in osg_vertices_normals:
            ncoord=vertex_normal[1]
            text.append("      %s %s %s" %
                            (ncoord[0], ncoord[1], ncoord[2]))
        text.append("    }")
        return text

#######################################################################
    def makeFaces(self, faces, vertices_osg, mapping, hasTcoords):
        if (len(faces) == 0):
            print "Probabily you were in edit mode when running the script, some object will be missing"
            return []
        text=[]
        nlin=0
        ntri=0
        nquad=0
        # counting number of lines, triangles and quads
        for face in faces:
            nv=len(face.v)
            if nv == 2:
                nlin = nlin + 1
            elif nv == 3:
                ntri = ntri + 1
            elif nv == 4:
                nquad = nquad + 1
            else:
                print "Se ignora una cara de %s vertices" % nv

        # counting number of primitives (one for lines, one for triangles and one for quads)
        numprims=0
        if (nlin > 0):
            numprims = numprims + 1
        if (ntri > 0):
            numprims = numprims + 1
        if (nquad > 0):
            numprims = numprims + 1

        # Now we write each primitive
        text.append("    PrimitiveSets %s {" % numprims)
        if nlin > 0:
            text.append("      DrawElementsUInt LINES %s {" % nlin)
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 2:
                  text.append("        %s %s" % (mapping[nface][0],mapping[nface][1]))
              nface = nface + 1
            text.append("      }")
        if ntri > 0:
            text.append("      DrawElementsUInt TRIANGLES %s {" % ntri)
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 3:
                  text.append("        %s %s %s" % (mapping[nface][0],mapping[nface][1],mapping[nface][2]))
              nface = nface + 1
            text.append("      }")
        if nquad > 0:
            text.append("      DrawElementsUInt QUADS %s {" % nquad)
            nface=0
            for face in faces:
              vlist=face.v
              nv=len(vlist)
              if nv == 4:
                  text.append("        %s %s %s %s" % (mapping[nface][0],mapping[nface][1],mapping[nface][2],mapping[nface][3]))
              nface = nface + 1
            text.append("      }")
        text.append("    }")

        if hasTcoords:
            text.append("    TexCoordArray 0 Vec2Array %s {" % len(vertices_osg))
            # Calculating per-vertex texture coordinates
            tc=[]
            for v in vertices_osg:
              tc.append( (0,0) )

            curface=0
            for face in faces:
                curv=0
                if (len(face.uv) == len(face.v)):
                    for vertex in face.v:
                        if (curv < 4):
                            tc[ mapping[curface][curv] ] = face.uv[curv]
                        curv = curv + 1
                curface = curface + 1

            for t in tc:
                text.append("      %s %s" % (t[0], t[1]))
            text.append("    }")

        if faces[0].col:
            text.append("    ColorBinding PER_VERTEX")
            text.append("    ColorArray Vec4Array %s {" % len(vertices_osg))
            # Calculating per-vertex colors
            vc=[]
            for v in vertices_osg:
              vc.append( NMesh.Col(0,0,0,0) )

            curface=0
            for face in faces:
                curv=0
                if (len(face.col) >= len(face.v)):
                    for vertex in face.v:
                        if (curv < 4):
                            vc[ mapping[curface][curv] ] = face.col[curv]
                        curv = curv + 1
                else:
                    print "%s aren't enough colors for %s vertices in one face!" % (len(face.col), len(face.v))
                curface = curface + 1

            for c in vc:
                text.append("      %s %s %s %s" %
                                    (c.r/255.0, c.g/255.0, c.b/255.0, c.a/255.0))
            text.append("    }")
        return text

#######################################################################
    def writeNode(self, node, file):
        for i in node:
            file.write("%s\n"%i)

#######################################################################
#######################################################################
#######################################################################
class OSGAnimation:
    def __init__(self, defpos, defrot, defscale, fps):
        self.points = {}
        self.defpoint=[defpos[0], defpos[1], defpos[2], defrot[0], defrot[1], defrot[2], defscale[0], defscale[1], defscale[2]]
        self.fps = fps

#######################################################################
    def add(self, type, tval, val):
        if self.points.has_key(tval):
            cpoint=self.points[tval]
        else:
            cpoint=[0,0,0,0,0,0,0,0,0]
            cpoint[0:9]=self.defpoint
        cpoint[type]=val
        self.points[tval]=cpoint
#######################################################################
    def makeCallback(self):
        text=[]
        text.append("        AnimationPathCallback {")
        text.append("            DataVariance DYNAMIC")
        text.append("            AnimationPath {")
        text.append("                DataVariance DYNAMIC")
        text.append("                LoopMode LOOP")
        text.append("                ControlPoints {")

        for p in self.points.keys():
            # Calculating euler -> quaternion
            # Blender has one unit for each 10 degrees
            heading=self.points[p][5]*pi/18
            pitch=self.points[p][4]*pi/18
            roll=self.points[p][3]*pi/18
            c1=cos(heading/2)
            c2=cos(pitch/2)
            c3=cos(roll/2)
            s1=sin(heading/2)
            s2=sin(pitch/2)
            s3=sin(roll/2)
            w=c1*c2*c3+s1*s2*s3
            x=c1*c2*s3-s1*s2*c3
            y=c1*s2*c3+s1*c2*s3
            z=s1*c2*c3-c1*s2*s3
            text.append("                    %s %s %s %s %s %s %s %s %s %s %s" %
                (p/self.fps,self.points[p][0], self.points[p][1], self.points[p][2],
                 x,y,z,w,
                 self.points[p][6], self.points[p][7], self.points[p][8]))

        text.append("                }")
        text.append("            }")
        text.append("        }")
        return text

#######################################################################
#######################################################################
#######################################################################
class OSGExport:
    scene = None
    strLoopMode = None

#######################################################################
    def __init__(self, filename, daScene, loopMode, meshAnim, fps, objects, **kwargs):
        self.file = open(filename, "w")
        self.scene = daScene
        self.doStaticAnimation = 0
        self.doMeshAnimation = 0
        self.doAnimationPath = 0
        self.gui = False
        self.mFrameStart = daScene.getRenderingContext().startFrame()
        self.mFrameEnd = daScene.getRenderingContext().endFrame()
        self.mFrameCount = self.mFrameEnd - self.mFrameStart + 1
        self.objects = []
        self.fps = fps
        self.osg = OSG( **kwargs)
        # Use only meshes
        for object in objects:
            if (object.getType() == 'Mesh') or (object.getType() == 'Empty'):
                self.objects.append(object)

        if loopMode == 2:
            self.strLoopMode = "SWING"
        else:
            self.strLoopMode = "LOOP"

        if meshAnim == 1:
            self.doAnimationPath = 1
        if meshAnim == 2:
            self.doStaticAnimation = 1
        if meshAnim == 3:
            self.doMeshAnimation = 1

# A Function to indicate whether the specified object
# should (1) use a per-frame mesh object, or (0) a single mesh
# for the entire animation.
#######################################################################
    def doMeshAnim(self, object):
        if self.doMeshAnimation == 0:
            return 0
        if object.getType() != "Mesh":
            return 0
        parent = object.getParent()
        if not parent:
            return 0
        if not parent.getType() == "Armature":
            return 0
        return 1
        
    

#######################################################################
    def isSupported(self, object):
        return (object.getType() == 'Mesh' or object.getType() == 'Empty')

#######################################################################
    def export(self):
        if self.doAnimationPath:
            root = self.exportPaths()
        else:
            root = self.exportFrames()
        if self.gui:
            Window.DrawProgressBar( 0.0, "Writing file")
        self.osg.writeNode(root,self.file)
        self.file.close()

#######################################################################
    def exportPaths(self):
        roots = []
	curObj = 1
        if self.gui:
            Window.DrawProgressBar( 0.0, "Exporting scene")

        for object in self.objects:
            if self.gui:
                Window.DrawProgressBar( curObj*(1.0/len(self.objects)), "Exporting objects %d/%d" % (curObj,len(self.objects)))

            if (not object.getParent()) or (not self.isSupported(object.getParent())):
                roots.append(self.recursePaths(object))
	    curObj+=1
        return self.osg.makeGroup("Blender root", "BlenderRoot", roots)

#######################################################################
    def createGeode(self, object, uniqueID):
        mesh=object.getData()
        # Find a texture and create the stateset
        texture = None
        for f in mesh.faces:
            if f.image != None:
                #texture = f.image.name;brea
                texture = Blender.sys.expandpath(f.image.filename).replace(" ","_");break #access to the full pathnam
                #texture = Blender.sys.basename(f.image.filename);break #access to the filenam
        stateSet = self.osg.makeStateSet(object.getName()+"_stateset", texture, mesh.materials)
        # Create the geode
        return self.osg.makeGeode(object.getName()+"_geode",
                                  uniqueID,
                                  mesh.verts, mesh.faces,
                                  stateSet, (texture != None))

#######################################################################
    def recursePaths(self, object):
        # Calculate the matrix of this object
        if not object.getParent():
            matrix = object.getMatrix()
        else:
            parentInverse = object.getParent().getInverseMatrix()
            accumulated = object.getMatrix()
            # Trick to create a new Matrix
            matrix = object.getInverseMatrix()
            self.multMatrixes(parentInverse, accumulated, matrix)

        # Create my children
        children=[]
        if object.getType() == 'Mesh':
            children.append(self.createGeode(object,object.getName()+"_geode"))
        for ob in self.objects:
            if ob.getParent():
                if (ob.getParent().getName() == object.getName()):
                    #then ob is a child of this object.
                    children.append(self.recursePaths(ob))
        # Create an animation or a plain matrix transform depending on IPO
        if object.ipo:
            animation = self.processAnimation(object.ipo, object.loc, object.rot, object.size)
            return self.osg.makeAnimationPathTransform(object.getName(), object.getName(), children, animation)
        else:
            return self.osg.makeMatrixTransform(object.getName(), object.getName(), children, matrix)

#######################################################################
    def exportFrames(self):
        children=[]
        times=[]
        if self.fps==1:
            delay="1"
        else:
            delay = "0.%03d" % (1000/self.fps)
        i = self.scene.getRenderingContext().startFrame()
        frameCount = self.scene.getRenderingContext().endFrame() - i + 1
        #self.writeSequenceHeader(frameCount, self.fps)
	Window.DrawProgressBar( 0.0, "Exporting frames")
        while i<=self.scene.getRenderingContext().endFrame():
	    Window.DrawProgressBar( (i-self.scene.getRenderingContext().startFrame())*(1.0/frameCount), "Exporting frame %d" % i)
            self.scene.getRenderingContext().currentFrame(i)
            self.scene.update(1)
            Window.RedrawAll()
            children.append(self.composeFrame(i))
            times.append(delay)
            i = i + 1
        return self.osg.makeSequence("Frames",
                                     "__Frames_sequence",
                                     children,
                                     times,
                                     self.strLoopMode)

#######################################################################
    def composeFrame(self, frame):
        children=[]
        for object in self.objects:
            if (not object.getParent()) or (not self.isSupported(object.getParent())):
                children.append(self.recurseFrame(object, frame))
        return self.osg.makeGroup("frame%d"%frame, "frame%d"%frame,children)

#######################################################################
    def recurseFrame(self, object, frame):
        # Calculate the matrix of this object
        if not object.getParent():
            matrix = object.getMatrix()
        else:
            parentInverse = object.getParent().getInverseMatrix()
            accumulated = object.getMatrix()
            # Trick to create a new Matrix
            matrix = object.getInverseMatrix()
            self.multMatrixes(parentInverse, accumulated, matrix)

        children=[]
        # My mesh
        if object.getType() == 'Mesh':
            if self.doMeshAnim(object):
                children.append(self.createGeode(object, "%s.%s" % (object.getName(), frame)))
            else:
                if frame > 1:
                    children.append(self.osg.makeRef(object.getName()+"_geode"))
                else:
                    children.append(self.createGeode(object, object.getName()+"_geode"))
        # My children
        for ob in self.objects:
            if ob.getParent():
                if (ob.getParent().getName() == object.getName()):
                    #then ob is a child of this object.
                    children.append(self.recurseFrame(ob,frame))
        return self.osg.makeMatrixTransform(object.getName(), object.getName(), children, matrix)

#######################################################################
    def multMatrixes(self, matrixA, matrixB, matrixR):
        for y in (0,1,2,3):
            for x in (0,1,2,3):
                matrixR[y][x] =( matrixA[0][x] * matrixB[y][0] +
                                 matrixA[1][x] * matrixB[y][1] +
                                 matrixA[2][x] * matrixB[y][2] +
                                 matrixA[3][x] * matrixB[y][3]
                               )
        
#######################################################################
    def processAnimation(self, ipo, defpos, defrot, defscale):
        anim=Animation(defpos,defrot,defscale, self.fps)
        curves = ipo.getCurves()
        for curve in curves:
          if curve.getName() == "LocX":
            for bp in curve.getPoints():
              anim.add(0,bp.pt[0],bp.pt[1])
          elif curve.getName() == "LocY":
            for bp in curve.getPoints():
              anim.add(1,bp.pt[0],bp.pt[1])
          elif curve.getName() == "LocZ":
            for bp in curve.getPoints():
              anim.add(2,bp.pt[0],bp.pt[1])
          elif curve.getName() == "RotX":
            for bp in curve.getPoints():
              anim.add(3,bp.pt[0],bp.pt[1])
          elif curve.getName() == "RotY":
            for bp in curve.getPoints():
              anim.add(4,bp.pt[0],bp.pt[1])
          elif curve.getName() == "RotZ":
            for bp in curve.getPoints():
              anim.add(5,bp.pt[0],bp.pt[1])
          elif curve.getName() == "SizeX":
            for bp in curve.getPoints():
              anim.add(6,bp.pt[0],bp.pt[1])
          elif curve.getName() == "SizeY":
            for bp in curve.getPoints():
              anim.add(7,bp.pt[0],bp.pt[1])
          elif curve.getName() == "SizeZ":
            for bp in curve.getPoints():
              anim.add(8,bp.pt[0],bp.pt[1])
        return anim.makeCallback()

