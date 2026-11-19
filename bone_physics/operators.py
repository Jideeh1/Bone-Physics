import bpy
from bpy.props import FloatProperty

from . import fit, gn, runtime


class BP_OT_toggle_mesh(bpy.types.Operator):
    bl_idname = "bp.toggle_mesh"
    bl_label = "Enable / Disable Vertex Physics"
    bl_description = "Turn vertex-level collision on or off for the active mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "Leave Edit Mode first")
            return {'CANCELLED'}

        s = obj.bp_mesh
        if s.enabled:
            s.enabled = False
            gn.remove(obj)
            runtime.forget(obj.name)
            return {'FINISHED'}

        if obj.data.users > 1:
            self.report({'ERROR'}, "Mesh data is shared. Make it single-user first")
            return {'CANCELLED'}

        gn.ensure(obj)
        s.enabled = True
        runtime.forget(obj.name)
        runtime.step(context.scene, obj)  # primes state and resolves collisions
        return {'FINISHED'}


class BP_OT_reset(bpy.types.Operator):
    bl_idname = "bp.reset"
    bl_label = "Reset Simulation"
    bl_description = "Snap all simulated bones and vertices back to the animated pose"

    def execute(self, context):
        runtime.reset_all()
        runtime.on_frame_change(context.scene)
        return {'FINISHED'}


def _selected_pose_bones(context):
    bones = list(context.selected_pose_bones or [])
    if not bones and context.active_pose_bone is not None:
        bones = [context.active_pose_bone]
    return bones


class BP_OT_bone_simulate(bpy.types.Operator):
    bl_idname = "bp.bone_simulate"
    bl_label = "Toggle Bone Simulation"
    bl_description = "Simulate the selected bones (e.g. skirt chains), or stop simulating them"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_pose_bone is not None

    def execute(self, context):
        bones = _selected_pose_bones(context)
        enable = not context.active_pose_bone.bp_bone.simulate
        arm = context.active_object
        for pb in bones:
            pb.bp_bone.simulate = enable
        if not enable:
            runtime.clear_bone_pose(arm, bones)
        runtime.forget(arm.name)
        return {'FINISHED'}


class BP_OT_bone_collider(bpy.types.Operator):
    bl_idname = "bp.bone_collider"
    bl_label = "Toggle Bone Collider"
    bl_description = "Use the selected bones (e.g. thighs) as capsule colliders, fitting radii to their skin"
    bl_options = {'REGISTER', 'UNDO'}

    percentile: FloatProperty(name="Fit Percentile", min=50.0, max=100.0, default=90.0)

    @classmethod
    def poll(cls, context):
        return context.active_pose_bone is not None

    def execute(self, context):
        arm = context.active_object
        enable = not context.active_pose_bone.bp_bone_collider.enabled
        missed = []
        for pb in _selected_pose_bones(context):
            pb.bp_bone_collider.enabled = enable
            if enable:
                radii = fit.fit_bone_radius(context, arm, pb, self.percentile)
                if radii is None:
                    missed.append(pb.name)
                else:
                    pb.bp_bone_collider.radius, pb.bp_bone_collider.radius_tail = radii
        if missed:
            self.report({'WARNING'}, "No skin found to fit: " + ", ".join(missed) + " (set radii by hand)")
        return {'FINISHED'}


class BP_OT_fit_bone_colliders(bpy.types.Operator):
    bl_idname = "bp.fit_bone_colliders"
    bl_label = "Fit Collider Radii"
    bl_description = "Re-fit the capsule radii of the selected collider bones to their skin"
    bl_options = {'REGISTER', 'UNDO'}

    percentile: FloatProperty(name="Fit Percentile", min=50.0, max=100.0, default=90.0)

    @classmethod
    def poll(cls, context):
        return context.active_pose_bone is not None

    def execute(self, context):
        arm = context.active_object
        for pb in _selected_pose_bones(context):
            if not pb.bp_bone_collider.enabled:
                continue
            radii = fit.fit_bone_radius(context, arm, pb, self.percentile)
            if radii is not None:
                pb.bp_bone_collider.radius, pb.bp_bone_collider.radius_tail = radii
        return {'FINISHED'}


class BP_OT_copy_bone_settings(bpy.types.Operator):
    bl_idname = "bp.copy_bone_settings"
    bl_label = "Copy to Selected"
    bl_description = "Copy the active bone's simulation settings to the selected bones"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_pose_bone is not None

    def execute(self, context):
        src = context.active_pose_bone.bp_bone
        for pb in _selected_pose_bones(context):
            for name in ("simulate", "stiffness", "damping", "gravity_scale", "radius", "iterations", "substeps"):
                setattr(pb.bp_bone, name, getattr(src, name))
        return {'FINISHED'}
