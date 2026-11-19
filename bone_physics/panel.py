import bpy


class BP_PT_main(bpy.types.Panel):
    bl_label = "Bone Physics"
    bl_idname = "BP_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bone Physics"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if obj is None:
            layout.label(text="Select an object")
            return

        if obj.type == 'MESH':
            s = obj.bp_mesh
            box = layout.box()
            box.label(text="Vertex Physics", icon='MESH_DATA')
            if s.enabled:
                row = box.row(align=True)
                row.operator("bp.toggle_mesh", text="Disable", icon='PAUSE')
                row.operator("bp.reset", text="", icon='FILE_REFRESH')
            else:
                box.operator("bp.toggle_mesh", text="Enable", icon='PLAY')

            col = box.column()
            col.enabled = not s.enabled or True
            col.prop_search(s, "mask_group", obj, "vertex_groups")
            col.prop(s, "stiffness")
            col.prop(s, "damping")
            col.prop(s, "gravity_scale")
            col.prop(s, "edge_stiffness")
            col.prop(s, "iterations")
            col.prop(s, "substeps")
            col.prop(s, "thickness")
            col.prop(s, "max_offset")

        c = obj.bp_collider
        box = layout.box()
        box.label(text="Collider", icon='MOD_PHYSICS')
        box.prop(c, "enabled")
        if c.enabled:
            box.prop(c, "shape")
            box.prop(c, "radius")
            if c.shape == 'CAPSULE':
                box.prop(c, "length")
