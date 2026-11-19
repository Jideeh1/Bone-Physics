"""Bone Physics: bone-chain physics plus vertex-level collision for Blender.

Bones marked "Simulate" (e.g. skirt chains) swing with inertia and gravity and
collide with colliders. Bones marked as colliders (e.g. thighs) become tapered
capsules fitted to their skin. Because the mesh between simulated bones can
still pass through colliders, meshes with Vertex Collision enabled are then
corrected per vertex, after skinning, through a Geometry Nodes modifier.
"""

from . import operators, panel, props, runtime


_classes = (
    props.BP_MeshSettings,
    props.BP_ColliderSettings,
    props.BP_BoneSettings,
    props.BP_BoneColliderSettings,
    operators.BP_OT_toggle_mesh,
    operators.BP_OT_reset,
    operators.BP_OT_bone_simulate,
    operators.BP_OT_bone_collider,
    operators.BP_OT_fit_bone_colliders,
    operators.BP_OT_copy_bone_settings,
    panel.BP_PT_main,
)


def register():
    import bpy
    from bpy.utils import register_class

    for cls in _classes:
        register_class(cls)

    bpy.types.Object.bp_mesh = bpy.props.PointerProperty(type=props.BP_MeshSettings)
    bpy.types.Object.bp_collider = bpy.props.PointerProperty(type=props.BP_ColliderSettings)
    bpy.types.PoseBone.bp_bone = bpy.props.PointerProperty(type=props.BP_BoneSettings)
    bpy.types.PoseBone.bp_bone_collider = bpy.props.PointerProperty(type=props.BP_BoneColliderSettings)

    runtime.install_handlers()


def unregister():
    import bpy
    from bpy.utils import unregister_class

    runtime.remove_handlers()
    runtime.reset_all()

    del bpy.types.PoseBone.bp_bone_collider
    del bpy.types.PoseBone.bp_bone
    del bpy.types.Object.bp_collider
    del bpy.types.Object.bp_mesh

    for cls in reversed(_classes):
        unregister_class(cls)
