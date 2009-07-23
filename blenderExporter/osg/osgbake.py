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


import Blender
from   Blender import Ipo
from   Blender import BezTriple
import bpy
import osglog
from osg import osgconf
from osglog import log
from osgconf import debug
from osgconf import DEBUG

Vector     = Blender.Mathutils.Vector
Quaternion = Blender.Mathutils.Quaternion
Matrix     = Blender.Mathutils.Matrix
Euler      = Blender.Mathutils.Euler


COORDINATE_SYSTEMS = ['local','real']
COORD_LOCAL = 0
COORD_REAL = 1
usrCoord = COORD_LOCAL # what the user wants
usrDelta = [0,0,0,0,0,0,0,0,0] #order specific - Loc xyz Rot xyz
R2D = 18/3.1415  # radian to grad


def addPoint(time, key, ipos):
    for i in range(len(ipos)):
        if ipos[i] is None:
            continue
        point = BezTriple.New() #this was new with Blender 2.45 API
        point.pt = (time, key[i])
        point.handleTypes = [1,1]
        ipos[i].append(point)
    return ipos

def getRangeFromIpo(ipo):
    first_frame = 1
    last_frame = 1
    for channel in ipo:
        for key in channel.bezierPoints:
            if key.vec[1][0] > last_frame:
                last_frame = int(key.vec[1][0])
    debug("range of ipo %s : %s %s " % (ipo.name, first_frame,last_frame))
    return (first_frame, last_frame, first_frame)


class BakeIpoForObject(object):
    def __init__(self, *args, **kwargs):
        self.ipos = kwargs["ipo"]
        self.object = kwargs["object"]
        self.config = kwargs.get("config", None)
        self.result_ipos = None


    def getCurves(self, ipo):
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
	return ipos

    def getLocLocal(self, ob):
	key = [
            ob.LocX, 
            ob.LocY, 
            ob.LocZ,
            ob.RotX*R2D, #get the curves in this order
            ob.RotY*R2D, 
            ob.RotZ*R2D,
            ob.SizeX, 
            ob.SizeY, 
            ob.SizeZ,
            ]
	return key

    def getLocReal(self, ob):
        obMatrix = ob.matrixWorld #Thank you IdeasMan42
        loc = obMatrix.translationPart()
        rot = obMatrix.toEuler()
        scale = obMatrix.scalePart()
        key = [
            loc.x,
            loc.y,
            loc.z,
            rot.x/10,
            rot.y/10,
            rot.z/10,
            scale.x,
            scale.y,
            scale.z,
            ]
        return key

    def getLocRot(self, ob, space):
        if space in xrange(len(COORDINATE_SYSTEMS)):
            if space == COORD_LOCAL:
                key = self.getLocLocal(ob)
                return key
            elif space == COORD_REAL:
                key = self.getLocReal(ob)
                return key
            else: #hey, programmers make mistakes too.
                debug('Fatal Error: getLoc called with %i' % space)
        return

    def bakeFrames(self, myipo): #bakes an object in a scene, returning the IPO containing the curves
        myipoName = myipo.getName()
        debug('Baking frames for scene %s object %s to ipo %s' % (bpy.data.scenes.active.getName(),self.object.getName(),myipoName))
        ipos = self.getCurves(myipo)
            #TODO: Gui setup idea: myOffset
            # reset action to start at frame 1 or at location
        myOffset=0 #=1-staframe
            #loop through frames in the animation. Often, there is rollup and the mocap starts late
        staframe,endframe,curframe = getRangeFromIpo(self.object.getIpo())
        for frame in range(staframe, endframe+1):
                    #tell Blender to advace to frame
            Blender.Set('curframe',frame) # computes the constrained location of the 'real' objects

                    #using the constrained Loc Rot of the object, set the location of the unconstrained clone. Yea! Clones are FreeMen
            key = self.getLocRot(self.object,usrCoord) #a key is a set of specifed exact channel values (LocRotScale) for a certain frame
            key = [a+b for a,b in zip(key, usrDelta)] #offset to the new location
            myframe= frame+myOffset
            Blender.Set('curframe',myframe)

            time = Blender.Get('curtime') #for BezTriple
            ipos = addPoint(time,key,ipos) #add this data at this time to the ipos
            debug('%s %i %.3f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f' % (myipoName, myframe, time, key[0], key[1], key[2], key[3], key[4], key[5], key[6], key[7], key[8]))
        Blender.Set('curframe',staframe)
        return myipo

    def getBakedIpos(self):

        # Get the dummy action if it has no users
        dummy_ipos_name = self.ipos.getName() + "_bake"
        try:
            baked = bpy.data.ipos[dummy_ipos_name]
        except:
            baked = None

        if not baked:
            baked = bpy.data.ipos.new(dummy_ipos_name,'Object')
            baked.fakeUser = False
        else:
            baked[Ipo.OB_LOCX] = None
            baked[Ipo.OB_LOCY] = None
            baked[Ipo.OB_LOCZ] = None
            baked[Ipo.OB_ROTX] = None
            baked[Ipo.OB_ROTY] = None
            baked[Ipo.OB_ROTZ] = None
            baked[Ipo.OB_SCALEX] = None
            baked[Ipo.OB_SCALEY] = None
            baked[Ipo.OB_SCALEZ] = None

        baked.addCurve('LocX')
        baked.addCurve('LocY')
        baked.addCurve('LocZ')
        baked.addCurve('RotX')
        baked.addCurve('RotY')
        baked.addCurve('RotZ')
        baked.addCurve('ScaleX')
        baked.addCurve('ScaleY')
        baked.addCurve('ScaleZ')

        dummy_object = None
        if self.object is None:
            log('WARNING Bake ipo %s without object, it means that it will not be possible to bake constraint, use an name ipo that contains the object associated to him, like myipo-MyObject' % self.ipos.name)
            self.object = bpy.data.scenes.active.objects.new('Empty')
            dummy_object = self.object

        previous_ipo = self.object.getIpo()
        self.object.setIpo(self.ipos)
        self.bakeFrames( baked)
        self.object.setIpo(previous_ipo)

        if dummy_object:
            bpy.data.scenes.active.objects.unlink(dummy_object)

        self.result_ipos = baked
        return self.result_ipos

class BakeAction(object):
    def __init__(self, *args, **kwargs):
        self.armature = kwargs["armature"]
        self.action = kwargs["action"]
        self.config = kwargs["config"]
        self.result_action = None


    def getBakedAction(self, sample_rate = 25):
        """
            Bakes supplied action for supplied armature.
            Returns baked action.
        """
        pose = self.armature.getPose()
        armature_data = self.armature.getData();
        pose_bones = pose.bones.values()
        rest_bones = armature_data.bones

        POSE_XFORM = [Blender.Object.Pose.LOC, Blender.Object.Pose.ROT, Blender.Object.Pose.SIZE ]
        #POSE_XFORM= [Object.Pose.LOC,Object.Pose.ROT,Object.Pose.SIZE]

        blender_fps = 25
        if sample_rate > blender_fps:
            sample_rate = blender_fps
        step = blender_fps / sample_rate

        startFrame= min(self.action.getFrameNumbers());
        endFrame= max(self.action.getFrameNumbers());


        dummy_action_name = "_" + self.action.name
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

        self.action.setActive(self.armature)
        frames = range(startFrame, endFrame+1, int(step))
        if frames[-1:] != endFrame :
            frames.append(endFrame)

        for current_frame in frames:

            Blender.Set('curframe', current_frame)
            time = Blender.Get('curtime') #for BezTriple
            debug('%s %i %.3f' % (self.action.name, current_frame, time))

            for i in range(len(pose_bones)):

                bone_name=pose_bones[i].name

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

            baked_action.setActive(self.armature)
            Blender.Set('curframe', current_frame)
            for i in range(len(pose_bones)):
                pose_bones[i].quat = baked_quats[pose_bones[i].name]
                pose_bones[i].loc = baked_locs[pose_bones[i].name]
                pose_bones[i].size = baked_sizes[pose_bones[i].name]
                pose_bones[i].insertKey(self.armature, current_frame, POSE_XFORM)

            self.action.setActive(self.armature)
            Blender.Set('curframe', current_frame)

            for name, quat in old_quats.iteritems():
                pose.bones[name].quat=quat

            for name, loc in old_locs.iteritems():
                pose.bones[name].loc=loc

        pose.update()
        self.result_action = baked_action
        return baked_action

class BakeIpoForMaterial(object):
    def __init__(self, *args, **kwargs):
        self.ipos = kwargs["ipo"]
        self.material = kwargs["material"]
        self.config = kwargs.get("config", None)
        self.result_ipos = None

    def getCurves(self, ipo):
	ipos = [
            ipo[Ipo.MA_R],
            ipo[Ipo.MA_G],
            ipo[Ipo.MA_B],
            ipo[Ipo.MA_ALPHA]
            ]
	return ipos

    def getColor(self, mat):
        key = [
            mat.R, 
            mat.G, 
            mat.B, 
            mat.alpha
            ]
        return key

    def bakeFrames(self, tobake):
	myipoName = tobake.getName()
	debug('Baking frames for scene %s material %s to ipo %s' % (bpy.data.scenes.active.getName(),self.material.getName(),myipoName))
	ipos = self.getCurves(tobake)
	#TODO: Gui setup idea: myOffset
	# reset action to start at frame 1 or at location
	myOffset=0 #=1-staframe
	#loop through frames in the animation. Often, there is rollup and the mocap starts late
	staframe,endframe,curframe = getRangeFromIpo(self.material.getIpo())
	for frame in range(staframe, endframe+1):
		#tell Blender to advace to frame
		Blender.Set('curframe',frame) # computes the constrained location of the 'real' objects
                
		#using the constrained Loc Rot of the object, set the location of the unconstrained clone. Yea! Clones are FreeMen
		key = self.getColor(self.material) #a key is a set of specifed exact channel values (LocRotScale) for a certain frame
		myframe= frame+myOffset
		Blender.Set('curframe',myframe)
		
		time = Blender.Get('curtime') #for BezTriple
		ipos = addPoint(time, key, ipos) #add this data at this time to the ipos
		debug('%s %i %.3f %.2f %.2f %.2f %.2f' % (myipoName, myframe, time, key[0], key[1], key[2], key[3]))
	Blender.Set('curframe',staframe)
        return tobake

    def getBakedIpos(self):
        # Get the dummy action if it has no users
        dummy_ipos_name = self.ipos.getName() + "_bake"
        try:
            baked = bpy.data.ipos[dummy_ipos_name]
        except:
            baked = None

        if not baked:
            baked = bpy.data.ipos.new(dummy_ipos_name,'Material')
            baked.fakeUser = False
        else:
            baked[Ipo.MA_R] = None
            baked[Ipo.MA_G] = None
            baked[Ipo.MA_B] = None
            baked[Ipo.MA_ALPHA] = None

        baked.addCurve('R')
        baked.addCurve('G')
        baked.addCurve('B')
        baked.addCurve('Alpha')

        dummy_mat = None
        if self.material is None:
            log('WARNING Bake ipo %s without material, it means that it will not be possible to bake constraint, use an name ipo that contains the material associated to him, like myipo-MyMaterial' % self.ipos.name)
            self.material = bpy.data.materials.new('Material')
            dummy_mat = self.material

        previous_ipo = self.material.getIpo()
        self.material.setIpo(self.ipos)
        self.bakeFrames(baked)
        self.material.setIpo(previous_ipo)

        if dummy_mat:
            bpy.data.materials.unlink(dummy_mat)

        self.result_ipo = baked
        return self.result_ipo
