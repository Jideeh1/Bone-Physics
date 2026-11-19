"""Applies per-vertex offsets after the Armature modifier.

Offsets are stored in a POINT / FLOAT_VECTOR attribute on the mesh. A Geometry
Nodes modifier, placed last in the stack, reads that attribute and adds it to
the already-skinned positions. Because it runs after the armature, the
offsets are in the same space the simulation computes them in.
"""

import bpy
import numpy as np


ATTR_NAME = "bp_offset"
MOD_NAME = "Bone Physics Offset"
GROUP_NAME = "BP_OffsetGN"


def _build_group():
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is not None:
        return group

    group = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
    group.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = group.nodes
    links = group.links

    group_in = nodes.new('NodeGroupInput')
    group_out = nodes.new('NodeGroupOutput')
    set_pos = nodes.new('GeometryNodeSetPosition')
    attr = nodes.new('GeometryNodeInputNamedAttribute')

    attr.data_type = 'FLOAT_VECTOR'
    attr.inputs["Name"].default_value = ATTR_NAME

    links.new(group_in.outputs["Geometry"], set_pos.inputs["Geometry"])
    links.new(attr.outputs["Attribute"], set_pos.inputs["Offset"])
    links.new(set_pos.outputs["Geometry"], group_out.inputs["Geometry"])
    return group


def ensure(obj):
    """Create the attribute and modifier on a mesh object (idempotent)."""
    mesh = obj.data
    if mesh.attributes.get(ATTR_NAME) is None:
        mesh.attributes.new(ATTR_NAME, 'FLOAT_VECTOR', 'POINT')
        write_offsets(obj, np.zeros((len(mesh.vertices), 3)))

    mod = obj.modifiers.get(MOD_NAME)
    if mod is None:
        mod = obj.modifiers.new(MOD_NAME, 'NODES')
    mod.node_group = _build_group()

    # Must come after the armature (and any other deformer) to be correct.
    index = len(obj.modifiers) - 1
    current = obj.modifiers.find(MOD_NAME)
    if current != index:
        obj.modifiers.move(current, index)
    return mod


def remove(obj):
    mod = obj.modifiers.get(MOD_NAME)
    if mod is not None:
        obj.modifiers.remove(mod)
    if obj.data.attributes.get(ATTR_NAME) is not None:
        obj.data.attributes.remove(obj.data.attributes[ATTR_NAME])
    obj.data.update_tag()


def write_offsets(obj, offsets):
    mesh = obj.data
    attr = mesh.attributes.get(ATTR_NAME)
    if attr is None:
        attr = mesh.attributes.new(ATTR_NAME, 'FLOAT_VECTOR', 'POINT')
    flat = np.ascontiguousarray(offsets, dtype=np.float32).ravel()
    attr.data.foreach_set("vector", flat)
    mesh.update_tag()


def read_offsets(obj):
    """Offsets currently on the base mesh, (N, 3) float64."""
    mesh = obj.data
    n = len(mesh.vertices)
    attr = mesh.attributes.get(ATTR_NAME)
    if attr is None or len(attr.data) != n:
        return np.zeros((n, 3))
    flat = np.empty(n * 3, dtype=np.float32)
    attr.data.foreach_get("vector", flat)
    return flat.reshape(n, 3).astype(np.float64)
