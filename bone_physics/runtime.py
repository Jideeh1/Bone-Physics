"""Blender-side driver: gathers skinned positions and colliders, runs the
vertex layer once per frame, and writes offsets back to the mesh."""

import bpy
import numpy as np
from bpy.app.handlers import persistent
from mathutils import Vector

from . import gn
from .vertex_sim import Capsule, SimParams, VertexLayer


# object name -> VertexLayer. Simulation state lives here, not in the file.
_layers = {}
_last_frame = {}


def reset_all():
    _layers.clear()
    _last_frame.clear()


def forget(obj_name):
    _layers.pop(obj_name, None)
    _last_frame.pop(obj_name, None)


def _avg_scale(matrix):
    return sum(abs(s) for s in matrix.to_scale()) / 3.0


def _mesh_edges(mesh):
    count = len(mesh.edges)
    flat = np.empty(count * 2, dtype=np.int32)
    if count:
        mesh.edges.foreach_get("vertices", flat)
    return flat.reshape(-1, 2)


def _mask_weights(obj, n, group_name):
    if not group_name:
        return np.ones(n)
    group = obj.vertex_groups.get(group_name)
    if group is None:
        return np.ones(n)
    weights = np.zeros(n)
    index = group.index
    for vert in obj.data.vertices:
        for g in vert.groups:
            if g.group == index:
                weights[vert.index] = g.weight
                break
    return weights


def _colliders_local(scene, obj):
    """Enabled colliders in the mesh's local space."""
    to_local = obj.matrix_world.inverted()
    mesh_scale = max(_avg_scale(obj.matrix_world), 1e-9)
    out = []
    for other in scene.objects:
        setting = other.bp_collider
        if not setting.enabled or other == obj:
            continue
        world = other.matrix_world
        radius = setting.radius * _avg_scale(world) / mesh_scale
        if setting.shape == 'SPHERE':
            center = np.array(to_local @ world.translation)
            out.append(Capsule(center, center.copy(), radius))
        else:
            half = setting.length * 0.5
            a = np.array(to_local @ (world @ Vector((0.0, 0.0, -half))))
            b = np.array(to_local @ (world @ Vector((0.0, 0.0, half))))
            out.append(Capsule(a, b, radius))
    return out


def _params(s):
    return SimParams(
        stiffness=s.stiffness,
        damping=s.damping,
        gravity_scale=s.gravity_scale,
        thickness=s.thickness,
        max_offset=s.max_offset,
        edge_stiffness=s.edge_stiffness,
        iterations=s.iterations,
    )


def _evaluated_positions(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    try:
        n = len(eval_mesh.vertices)
        flat = np.empty(n * 3, dtype=np.float32)
        eval_mesh.vertices.foreach_get("co", flat)
    finally:
        eval_obj.to_mesh_clear()
    return flat.reshape(n, 3).astype(np.float64)


def step(scene, obj):
    """Advance one frame for one mesh object. Safe to call repeatedly per frame."""
    s = obj.bp_mesh
    frame = scene.frame_current
    name = obj.name
    layer = _layers.get(name)

    # Already simulated this frame (e.g. both frame-change and render-pre fired).
    if layer is not None and _last_frame.get(name) == frame:
        return

    evaluated = _evaluated_positions(obj)
    n = len(evaluated)
    # The evaluated mesh includes our offset modifier; remove it to get the
    # pure skinned pose the bones produce.
    skin = evaluated - gn.read_offsets(obj)

    continuous = layer is not None and _last_frame.get(name) == frame - 1
    weights = _mask_weights(obj, n, s.mask_group)
    colliders = _colliders_local(scene, obj)
    to_local = obj.matrix_world.inverted().to_3x3()
    gravity = np.array(to_local @ Vector(scene.gravity))
    params = _params(s)

    if layer is None or not continuous or layer.count != n:
        # Fresh start (or a jump). dt=0 means no motion, but collisions still
        # resolve, so the first frame is already clean.
        layer = VertexLayer()
        layer.reset(skin)
        _layers[name] = layer
        offset = layer.step(skin, weights, _mesh_edges(obj.data), colliders,
                            gravity, 0.0, params)
    else:
        substeps = max(1, int(s.substeps))
        dt = (1.0 / (scene.render.fps / scene.render.fps_base)) / substeps
        offset = None
        for _ in range(substeps):
            offset = layer.step(skin, weights, _mesh_edges(obj.data), colliders,
                                gravity, dt, params)

    gn.write_offsets(obj, offset)
    _last_frame[name] = frame


def sim_objects(scene):
    return [o for o in scene.objects if o.type == 'MESH' and o.bp_mesh.enabled]


@persistent
def on_frame_change(scene, *_args):
    for obj in sim_objects(scene):
        step(scene, obj)


@persistent
def on_render_pre(scene, *_args):
    on_frame_change(scene)


def install_handlers():
    if on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(on_frame_change)
    if on_render_pre not in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.append(on_render_pre)


def remove_handlers():
    for handlers, fn in (
        (bpy.app.handlers.frame_change_post, on_frame_change),
        (bpy.app.handlers.render_pre, on_render_pre),
    ):
        if fn in handlers:
            handlers.remove(fn)
