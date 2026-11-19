"""Bone Physics: vertex-level secondary motion with collision for Blender.

The skinned mesh is the target. Each vertex is simulated as a particle that
follows the bones, and collision pushes it out of colliders. The resulting
offsets are applied after the Armature modifier through a Geometry Nodes
modifier that Bone Physics creates automatically.
"""

from . import props, operators, panel, runtime


_classes = (
    props.BP_MeshSettings,
    props.BP_ColliderSettings,
    operators.BP_OT_toggle_mesh,
    operators.BP_OT_reset,
    panel.BP_PT_main,
)


def register():
    from bpy.utils import register_class
    import bpy

    for cls in _classes:
        register_class(cls)

    bpy.types.Object.bp_mesh = bpy.props.PointerProperty(type=props.BP_MeshSettings)
    bpy.types.Object.bp_collider = bpy.props.PointerProperty(type=props.BP_ColliderSettings)

    runtime.install_handlers()


def unregister():
    from bpy.utils import unregister_class
    import bpy

    runtime.remove_handlers()
    runtime.reset_all()

    del bpy.types.Object.bp_collider
    del bpy.types.Object.bp_mesh

    for cls in reversed(_classes):
        unregister_class(cls)
