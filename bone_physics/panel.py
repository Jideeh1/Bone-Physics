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

        layout.operator("bp.reset", icon='FILE_REFRESH')

        pb = context.active_pose_bone
        if obj.type == 'ARMATURE' and pb is not None:
            self._draw_bone(layout, pb)

        if obj.type == 'MESH':
            self._draw_mesh(layout, obj)

        c = obj.bp_collider
        box = layout.box()
        box.label(text="Object Collider", icon='MOD_PHYSICS')
        box.prop(c, "enabled")
        if c.enabled:
            box.prop(c, "shape")
            box.prop(c, "radius")
            if c.shape == 'CAPSULE':
                box.prop(c, "length")

    def _draw_bone(self, layout, pb):
        s = pb.bp_bone
        box = layout.box()
        box.label(text=f"Bone: {pb.name}", icon='BONE_DATA')
        box.operator("bp.bone_simulate",
                     text="Stop Simulating Selected" if s.simulate else "Simulate Selected",
                     icon='PAUSE' if s.simulate else 'PLAY')
        if s.simulate:
            col = box.column()
            col.prop(s, "stiffness")
            col.prop(s, "damping")
            col.prop(s, "gravity_scale")
            col.prop(s, "radius")
            col.prop(s, "iterations")
            box.operator("bp.copy_bone_settings")

        c = pb.bp_bone_collider
        box = layout.box()
        box.label(text="Bone Collider", icon='MOD_PHYSICS')
        box.operator("bp.bone_collider",
                     text="Remove Collider from Selected" if c.enabled else "Make Selected Colliders")
        if c.enabled:
            box.prop(c, "radius")
            box.prop(c, "radius_tail")
            box.operator("bp.fit_bone_colliders", icon='FULLSCREEN_EXIT')

    def _draw_mesh(self, layout, obj):
        s = obj.bp_mesh
        box = layout.box()
        box.label(text="Vertex Collision", icon='MESH_DATA')
        box.operator("bp.toggle_mesh",
                     text="Disable" if s.enabled else "Enable",
                     icon='PAUSE' if s.enabled else 'PLAY')
        col = box.column()
        col.prop_search(s, "mask_group", obj, "vertex_groups")
        col.prop(s, "stiffness")
        col.prop(s, "damping")
        col.prop(s, "gravity_scale")
        col.prop(s, "edge_stiffness")
        col.prop(s, "iterations")
        col.prop(s, "substeps")
        col.prop(s, "thickness")
        col.prop(s, "max_offset")
        col.prop(s, "ignore_weight")
