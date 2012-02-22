# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

import bpy
from . import osglog

def pose_frame_info(obj):
    info = {}
    for name, pbone in  obj.pose.bones.items():
        info[name] = pbone.matrix_basis.copy()
    return info

def obj_frame_info(obj):
    return obj.matrix_local.copy()

def bakedTransforms(scene,
         obj,
         frame_start,
         frame_end, 
         step=1,
         do_pose=True,
         do_object=True):

    frame_back = scene.frame_current

    pose_info = []
    obj_info = []

    frame_range = range(frame_start, frame_end + 1, step)
    
    if obj.type == "ARMATURE":
        original_pose_position = obj.data.pose_position
        obj.data.pose_position = 'POSE'

    # -------------------------------------------------------------------------
    # Collect transformations

    # could speed this up by applying steps here too...
    for f in frame_range:
        scene.frame_set(f)

        if do_pose:
            pose_info.append(pose_frame_info(obj))
        if do_object:
            obj_info.append(obj_frame_info(obj))
            
    scene.frame_set(frame_back)
    
    if obj.type == "ARMATURE":
        obj.data.pose_position = 'REST'
            
    return (frame_range, obj_info, pose_info)
    
def action_fcurve_ensure(action, data_path, array_index):
    for fcu in action.fcurves:
        if fcu.data_path == data_path and fcu.array_index == array_index:
            return fcu

    return action.fcurves.new(data_path=data_path, index=array_index)
    
def make_fcurves(action, rotation_mode, prefix=""):
    fc = {}
    fc["location_x"] = action.fcurves.new(prefix+"location", 0, "Location")
    fc["location_y"] = action.fcurves.new(prefix+"location", 1, "Location")
    fc["location_z"] = action.fcurves.new(prefix+"location", 2, "Location")
    
    if rotation_mode == 'QUATERNION':
        fc["rot_w"] = action.fcurves.new(prefix+"rotation_quaternion", 0, "Rotation")
        fc["rot_x"] = action.fcurves.new(prefix+"rotation_quaternion", 1, "Rotation")
        fc["rot_y"] = action.fcurves.new(prefix+"rotation_quaternion", 2, "Rotation")
        fc["rot_z"] = action.fcurves.new(prefix+"rotation_quaternion", 3, "Rotation")
    elif rotation_mode == 'AXIS_ANGLE':
        fc["rot_w"] = action.fcurves.new(prefix+"rotation_axis_angle", 0, "Rotation")
        fc["rot_x"] = action.fcurves.new(prefix+"rotation_axis_angle", 1, "Rotation")
        fc["rot_y"] = action.fcurves.new(prefix+"rotation_axis_angle", 2, "Rotation")
        fc["rot_z"] = action.fcurves.new(prefix+"rotation_axis_angle", 3, "Rotation")
    else:  # euler, XYZ, ZXY etc
        fc["rot_x"] = action.fcurves.new(prefix+"rotation_euler", 0, "Rotation")
        fc["rot_y"] = action.fcurves.new(prefix+"rotation_euler", 1, "Rotation")
        fc["rot_z"] = action.fcurves.new(prefix+"rotation_euler", 2, "Rotation")
    
    fc["scale_x"] = action.fcurves.new(prefix+"scale", 0, "Scale")
    fc["scale_y"] = action.fcurves.new(prefix+"scale", 1, "Scale")
    fc["scale_z"] = action.fcurves.new(prefix+"scale", 2, "Scale")
    
    return fc
    
def set_keys(fc, f, matrix, rotation_mode):
    opt = {'NEEDED'}
    trans = matrix.to_translation()
    fc["location_x"].keyframe_points.insert(f, trans[0], opt)
    fc["location_y"].keyframe_points.insert(f, trans[1], opt)
    fc["location_z"].keyframe_points.insert(f, trans[2], opt)

    if rotation_mode == 'QUATERNION':
        quat = matrix.to_quaternion()
        fc["rot_w"].keyframe_points.insert(f, quat[0], opt)
        fc["rot_x"].keyframe_points.insert(f, quat[1], opt)
        fc["rot_y"].keyframe_points.insert(f, quat[2], opt)
        fc["rot_z"].keyframe_points.insert(f, quat[3], opt)
    elif rotation_mode == 'AXIS_ANGLE':
        aa = matrix.to_quaternion().to_axis_angle()
        fc["rot_w"].keyframe_points.insert(f, aa[0], opt)
        fc["rot_x"].keyframe_points.insert(f, aa[1], opt)
        fc["rot_y"].keyframe_points.insert(f, aa[2], opt)
        fc["rot_z"].keyframe_points.insert(f, aa[3], opt)
    else:  # euler, XYZ, ZXY etc
        eu = matrix.to_euler(rotation_mode)
        fc["rot_x"].keyframe_points.insert(f, eu[0], opt)
        fc["rot_y"].keyframe_points.insert(f, eu[1], opt)
        fc["rot_z"].keyframe_points.insert(f, eu[2], opt)

    sc = matrix.to_scale()
    fc["scale_x"].keyframe_points.insert(f, sc[0], opt)
    fc["scale_y"].keyframe_points.insert(f, sc[1], opt)
    fc["scale_z"].keyframe_points.insert(f, sc[2], opt)

def bake(scene,
         obj,
         frame_start,
         frame_end, step=1,
         only_selected=False,
         do_pose=True,
         do_object=True,
         do_constraint_clear=False,
         to_quat=False):
         
    pose = obj.pose
    
    if pose is None:
        do_pose = False

    if do_pose is None and do_object is None:
        return None

    if to_quat:
        print("Change rotation to QUATERNION")
        obj.rotation_mode = 'QUATERNION'
        print("rotation " + obj.rotation_mode)

    # -------------------------------------------------------------------------
    # Collect transformations

    (frame_range, obj_info, pose_info) = bakedTransforms(scene, obj, frame_start, frame_end, step, do_pose, do_object)

    # -------------------------------------------------------------------------
    # Create action

    action = bpy.data.actions.new("Action")

    if do_pose:
        pose_items = pose.bones.items()
    else:
        pose_items = []  # skip

    # -------------------------------------------------------------------------
    # Apply transformations to action
    
    frame_back = scene.frame_current
    
    # pose
    for name, pbone in (pose_items if do_pose else ()):
        if only_selected and not pbone.bone.select:
            continue
            
        if do_constraint_clear:
            while pbone.constraints:
                pbone.constraints.remove(pbone.constraints[0])
            
        fc = make_fcurves(action, pbone.rotation_mode, "pose.bones[\"%s\"]." % (pbone.name))

        for f in frame_range:
            matrix = pose_info[(f - frame_start) // step][name]
            set_keys(fc, f, matrix, pbone.rotation_mode)

            # pbone.location = matrix.to_translation()
            # pbone.rotation_quaternion = matrix.to_quaternion()
            #pbone.matrix_basis = matrix
            #
            #pbone.keyframe_insert("location", -1, f, name)
            #
            #rotation_mode = pbone.rotation_mode
            #
            #if rotation_mode == 'QUATERNION':
            #    pbone.keyframe_insert("rotation_quaternion", -1, f, name)
            #elif rotation_mode == 'AXIS_ANGLE':
            #    pbone.keyframe_insert("rotation_axis_angle", -1, f, name)
            #else:  # euler, XYZ, ZXY etc
            #    pbone.keyframe_insert("rotation_euler", -1, f, name)
            #
            #pbone.keyframe_insert("scale", -1, f, name)

    # object.
    if do_object:
        if do_constraint_clear:
            while obj.constraints:
                obj.constraints.remove(obj.constraints[0])
                
        fc = make_fcurves(action, obj.rotation_mode)

        for f in frame_range:
            matrix = obj_info[(f - frame_start) // step]
            set_keys(fc, f, matrix, obj.rotation_mode)
            
    # Eliminate duplicate keyframe entries.
    for fcu in action.fcurves:
        keyframe_points = fcu.keyframe_points
        i = 1
        while i < len(fcu.keyframe_points) - 1:
            val_prev = keyframe_points[i - 1].co[1]
            val_next = keyframe_points[i + 1].co[1]
            val = keyframe_points[i].co[1]

            if abs(val - val_prev) + abs(val - val_next) < 0.0001:
                keyframe_points.remove(keyframe_points[i])
            else:
                i += 1

    scene.frame_set(frame_back)
    
    return action


from bpy.props import IntProperty, BoolProperty, EnumProperty


class BakeAction(bpy.types.Operator):
    '''Bake animation to an Action'''
    bl_idname = "osg.bake"
    bl_label = "Bake Action"
    bl_options = {'REGISTER', 'UNDO'}

    frame_start = IntProperty(
            name="Start Frame",
            description="Start frame for baking",
            min=0, max=300000,
            default=1,
            )
    frame_end = IntProperty(
            name="End Frame",
            description="End frame for baking",
            min=1, max=300000,
            default=250,
            )
    step = IntProperty(
            name="Frame Step",
            description="Frame Step",
            min=1, max=120,
            default=1,
            )
    only_selected = BoolProperty(
            name="Only Selected",
            default=True,
            )
    clear_consraints = BoolProperty(
            name="Clear Constraints",
            default=True,
            )
    bake_types = EnumProperty(
            name="Bake Data",
            options={'ENUM_FLAG'},
            items=(('POSE', "Pose", ""),
                   ('OBJECT', "Object", ""),
                   ),
            default={'POSE', 'OBJECT'},
            )
    to_quat = BoolProperty(
            name="To Quaternion",
            default=False,
            )

    def execute(self, context):

        action = bake(bpy.context.scene,
                      bpy.context.object,
                      self.frame_start,
                      self.frame_end,
                      self.step,
                      self.only_selected,
                      'POSE' in self.bake_types,
                      'OBJECT' in self.bake_types,
                      self.clear_consraints,
                      self.to_quat
                      )

        if action is None:
            self.report({'INFO'}, "Nothing to bake")
            return {'CANCELLED'}

        atd = bpy.context.object.animation_data_create()
        atd.action = action

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


bpy.utils.register_class(BakeAction)
