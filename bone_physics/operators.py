import bpy

from . import gn, runtime


class BP_OT_toggle_mesh(bpy.types.Operator):
    bl_idname = "bp.toggle_mesh"
    bl_label = "Enable / Disable Vertex Physics"
    bl_description = "Turn vertex-level simulation on or off for the active mesh"
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
        runtime.step(context.scene, obj)  # primes state and zeroes offsets
        return {'FINISHED'}


class BP_OT_reset(bpy.types.Operator):
    bl_idname = "bp.reset"
    bl_label = "Reset Simulation"
    bl_description = "Snap the simulated vertices back to the skinned pose"

    def execute(self, context):
        obj = context.active_object
        if obj is None or not obj.bp_mesh.enabled:
            return {'CANCELLED'}
        runtime.forget(obj.name)
        runtime.step(context.scene, obj)
        return {'FINISHED'}
