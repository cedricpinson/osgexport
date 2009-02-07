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

DEBUG = False
def debug(str):
    if DEBUG:
        log(str)

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


def getBakedAction(armatureObject, action , sample_rate = 25):
    """
        Bakes supplied action for supplied armature.
        Returns baked action.
    """
    pose = armatureObject.getPose()
    armature_data = armatureObject.getData();
    pose_bones = pose.bones.values()
    rest_bones = armature_data.bones

    POSE_XFORM = [Blender.Object.Pose.LOC, Blender.Object.Pose.ROT, Blender.Object.Pose.SIZE ]
    #POSE_XFORM= [Object.Pose.LOC,Object.Pose.ROT,Object.Pose.SIZE]
 
    blender_fps = 25
    if sample_rate > blender_fps:
        sample_rate = blender_fps
    step = blender_fps / sample_rate
    
    startFrame= min(action.getFrameNumbers());
    endFrame= max(action.getFrameNumbers());
 
       
    dummy_action_name = "_" + action.name
    # Get the dummy action if it has no users
    try:
        baked_action = bpy.data.actions[dummy_action_name]
    except:
        baked_action = None
    
    if not baked_action:
        baked_action          = bpy.data.actions.new(dummy_action_name)
        baked_action.fakeUser = False
    for channel in baked_action.getChannelNames():
        baked_action.removeChannel(channel)
    
    old_quats={}
    old_locs={}
    old_sizes={}
    
    baked_locs={}
    baked_quats={}
    baked_sizes={}
    
    action.setActive(armatureObject)
    frames = range(startFrame, endFrame+1, int(step))
    if frames[-1:] != endFrame :
        frames.append(endFrame)
    for current_frame in frames:

        Blender.Set('curframe', current_frame)
        for i in range(len(pose_bones)):
            
            bone_name=pose_bones[i].name;

            rest_bone=rest_bones[bone_name]
            matrix = Matrix(pose_bones[i].poseMatrix)
            rest_matrix= Matrix(rest_bone.matrix['ARMATURESPACE'])
            
            parent_bone=rest_bone.parent

            if parent_bone:
                parent_pose_bone=pose.bones[parent_bone.name]
                matrix=matrix * Matrix(parent_pose_bone.poseMatrix).invert()
                rest_matrix=rest_matrix * Matrix(parent_bone.matrix['ARMATURESPACE']).invert()
            
            #print "before\n", matrix
            #print "before quat\n", pose_bones[i].quat;
                
            #print "localised pose matrix\n", matrix
            #print "localised rest matrix\n", rest_matrix
            matrix=matrix * Matrix(rest_matrix).invert()
                
                
            old_quats[bone_name] = Quaternion(pose_bones[i].quat);
            old_locs[bone_name] = Vector(pose_bones[i].loc);
            old_sizes[bone_name] = Vector(pose_bones[i].size);
            
            baked_locs[bone_name] = Vector(matrix.translationPart())
            baked_quats[bone_name] = Quaternion(matrix.toQuat())
            baked_sizes[bone_name] = Vector(matrix.scalePart())

        baked_action.setActive(armatureObject)
        Blender.Set('curframe', current_frame)
        for i in range(len(pose_bones)):
            pose_bones[i].quat = baked_quats[pose_bones[i].name]
            pose_bones[i].loc = baked_locs[pose_bones[i].name]
            pose_bones[i].size = baked_sizes[pose_bones[i].name]
            pose_bones[i].insertKey(armatureObject, current_frame, POSE_XFORM)
            
        action.setActive(armatureObject)
        Blender.Set('curframe', current_frame)

        for name, quat in old_quats.iteritems():
            pose.bones[name].quat=quat
            
        for name, loc in old_locs.iteritems():
            pose.bones[name].loc=loc
            
        
    pose.update()
    return baked_action

def getBakedAction3(ob_arm, action, sample_rate):
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
            anim = self.createAnimationFromIpo(obj.getIpo(), obj.getName())
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
            light.spot_cutoff = self.lamp.getSpotSize() * .5
            if light.spot_cutoff > 90:
                light.spot_cutoff = 180
            light.spot_exponent = 128.0 * self.lamp.getSpotBlend()

        return ls

class BlenderObjectToGeometry(object):
    def __init__(self, *args, **kwargs):
        self.object = kwargs["object"]
        self.geometry = Geometry()
        self.mesh = self.object.getData(False, True)
        self.vertexes = None
        self.uvs = {}

    def hasTexture(self):
        if len(self.mesh.materials) > 0:
            # support only one material by mesh right now
            mat_source = self.mesh.materials[0]
            if mat_source is None:
                return False
            texture_list = mat_source.getTextures()
            for i in range(0, len(texture_list)):
                if texture_list[i] is not None:
                    return True
        return False

    def createTexture2D(self, mtex):
        image_object = mtex.tex.getImage()
        if image_object is None:
            log("Warning the texture % has not Image, skip it" % mtex.tex.getName())
            return None
        texture = Texture2D()
        filename = "//" + Blender.sys.basename(image_object.getFilename().replace(" ","_"))
        texture.file = filename.replace("//","textures/")
        texture.source_image = image_object
        return texture

    def createStateSet(self):
        s = StateSet()
        uvs = self.uvs
        self.uvs = {}
        if len(self.mesh.materials) > 0:
            # support only one material by mesh right now
            mat_source = self.mesh.materials[0]
            if mat_source is not None:
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

                texture_list = mat_source.getTextures()
                debug("texture list %s" % str(texture_list))

                # find a default channel if exist uv
                default_uv = None
                default_uv_key = None
                if (len(uvs)) == 1:
                    default_uv_key = uvs.keys()[0]
                    default_uv = uvs[default_uv_key]
                
                for i in range(0, len(texture_list)):
                    if texture_list[i] is not None:
                        t = self.createTexture2D(texture_list[i])
                        debug("texture %s %s" % (i, texture_list[i]))
                        if t is not None:
                            if not s.texture_attributes.has_key(i):
                                s.texture_attributes[i] = []
                            uv_layer =  texture_list[i].uvlayer
                            if len(uv_layer) > 0:
                                debug("texture %s use uv layer %s" % (i, uv_layer))
                                self.uvs[i] = TexCoordArray()
                                self.uvs[i].array = uvs[uv_layer].array
                                self.uvs[i].index = i
                            elif default_uv:
                                debug("texture %s use default uv layer %s" % (i, default_uv_key))
                                self.uvs[i] = TexCoordArray()
                                self.uvs[i].index = i
                                self.uvs[i].array = default_uv.array
                                
                            s.texture_attributes[i].append(t)
                            if t.source_image.getDepth() > 24: # there is an alpha
                                s.modes.append(("GL_BLEND","ON"))

                debug("state set %s" % str(s))

        # adjust uvs channels if no textures assigned
        print "result uvs ", self.uvs.keys()
        if len(self.uvs.keys()) == 0:
            debug("no texture set, adjust uvs channels, in arbitrary order")
            index = 0
            for k in uvs.keys():
                uvs[k].index = index
                index += 1
            self.uvs = uvs
        return s


    def compVertices(self, face1, vert1, face2, vert2):
        if (not face1.smooth) or (not face2.smooth): return 0
        if self.mesh.faceUV:
            if (len(face1.uv) != len(face2.uv)): return 0
        if self.mesh.vertexColors:
            if (len(face1.col) != len(face2.col)): return 0

        if self.mesh.faceUV:
            if (len(face1.uv) == len(face1.v)):
                if face1.uv[vert1][0] != face2.uv[vert2][0]: return 0
                if face1.uv[vert1][1] != face2.uv[vert2][1]: return 0

        if self.mesh.vertexColors:
            if (len(face1.col) == len(face1.v)):
                if face1.col[vert1].r != face2.col[vert2].r: return 0
                if face1.col[vert1].g != face2.col[vert2].g: return 0
                if face1.col[vert1].b != face2.col[vert2].b: return 0
                if face1.col[vert1].a != face2.col[vert2].a: return 0
        return 1

    def compVertices2(self, vert1, vert2, vertexes, normals, colors, uvs):
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

    def calcVertices(self, faces, vertices):
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


    def calcVertices2(self, mesh):

        if (len(mesh.faces) == 0):
            log("objest %s has no faces" % self.object.getName())
            return False
        log("mesh %s" % self.object.getName())

        vertexes = []
        collected_faces = []
        for face in mesh.faces:
            f = []
            for vertex in face.verts:
                index = len(vertexes)
                vertexes.append(vertex)
                f.append(index)
            debug("face %s" % str(f))
            collected_faces.append((face,f))

        colors = {}
        if self.mesh.vertexColors:
            names = self.mesh.getColorLayerNames()
            backup_name = self.mesh.activeColorLayer
            for name in names:
                self.mesh.activeColorLayer = name
                self.mesh.update()
                color_array = []
                for face in mesh.faces:
                    for i in range(0, len(face.verts)):
                        color_array.append(face.col[i])
                colors[name] = color_array
            self.mesh.activeColorLayer = backup_name
            self.mesh.update()

        uvs = {}
        if self.mesh.faceUV:
            names = self.mesh.getUVLayerNames()
            backup_name = self.mesh.activeUVLayer
            for name in names:
                self.mesh.activeUVLayer = name
                self.mesh.update()
                uv_array = []
                for face in mesh.faces:
                    for i in range(0, len(face.verts)):
                        uv_array.append(face.uv[i])
                uvs[name] = uv_array
            self.mesh.activeUVLayer = backup_name
            self.mesh.update()

        normals = []
        for face in mesh.faces:
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
            debug("process vertex %s" % i)
            for j in range(i+1, len(vertexes)):
                if tagged_vertexes[j] is True: # avoid processing more than one time a vertex
                    continue
                different = self.compVertices2(i, j, vertexes, normals, colors, uvs)
                if not different:
                    debug("   vertex %s is the same" % j)
                    merged_vertexes[j] = index
                    tagged_vertexes[j] = True
                    mapping_vertexes[index].append(j)

        for i in range(0, len(mapping_vertexes)):
            debug("vertex %s contains %s" % (str(i), str(mapping_vertexes[i])))

        if len(mapping_vertexes) != len(vertexes):
            log("vertexes reduced from %s to %s" % (str(len(vertexes)),len(mapping_vertexes)))
        else:
            log("vertexes %s" % str(len(vertexes)))

        faces = []
        for (original, face) in collected_faces:
            f = []
            for v in face:
                f.append(merged_vertexes[v])
            faces.append(f)
            debug("new face %s" % str(f))
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
            verts = []
            for idx, weight in mesh.getVertsFromGroup(i, 1):
                if weight < 0.001:
                    log( "warning " + str(idx) + " to has a weight too small (" + str(weight) + "), skipping vertex")
                    continue
                if original_vertexes2optimized.has_key(idx):
                    for v in original_vertexes2optimized[idx]:
                        verts.append([v, weight])
            if len(verts) == 0:
                log( "warning " + str(i) + " has not vertexes, skip it, if really unsued you should clean it")
            else:
                vg = VertexGroup()
                vg.targetGroupName = i
                vg.vertexes = verts
                vgroups[i] = vg

        if (len(vgroups)):
            log("vertex groups %s" % str(len(vgroups)))
        self.groups = vgroups
        
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
            log("uvs channels %s" % len(osg_uvs))

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
                log("Warning can't manage faces with %s vertices" % nv)

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

        self.uvs = osg_uvs
        self.vertexes = osg_vertexes
        self.normals = osg_normals
        self.primitives = primitives
        s = "mesh %s" % self.object.getName()
        s = '-' * len(s)
        log(s)
        return True

    def convert(self):
        geom = self.geometry
        if self.mesh.vertexUV:
            log("Warning mesh %s use sticky UV and it's not supported" % self.object.getName())

        if self.calcVertices2(self.mesh) is False:
            return None

        geom.vertexes = self.vertexes
        geom.normals = self.normals
        geom.primitives = self.primitives
        geom.setName(self.object.getName())
        geom.uvs = self.uvs
        geom.stateset = self.createStateSet()
        geom.uvs = self.uvs
        geom.groups = self.groups
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

        if self.mesh.vertexColors:
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
        self.geometry = RigGeometry()

    def convert4(self):
        geom = RigGeometry()
        [result, mapping] = self.calcVertices(self.mesh.faces, self.mesh.verts)
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
