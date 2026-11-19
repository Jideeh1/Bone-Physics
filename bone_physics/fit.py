"""Fit bone collider radii to the skin the bone actually deforms."""

import numpy as np

from . import gn
from .weights import sparse_groups


def deform_meshes(scene, arm):
    return [o for o in scene.objects
            if o.type == 'MESH'
            and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]


def _skinned_world(obj, depsgraph):
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    try:
        n = len(mesh.vertices)
        flat = np.empty(n * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", flat)
    finally:
        eval_obj.to_mesh_clear()
    local = flat.reshape(n, 3).astype(np.float64)
    if n == len(obj.data.vertices):
        local -= gn.read_offsets(obj)
    m = np.array(obj.matrix_world)
    return local @ m[:3, :3].T + m[:3, 3]


def fit_bone_radius(context, arm, pb, percentile=90.0, min_weight=0.5):
    """Returns (head_radius, tail_radius) in world units, or None.

    Uses the skinned vertices weighted to this bone (weight >= min_weight):
    their distance from the bone axis, split into the head and tail thirds.
    """
    depsgraph = context.evaluated_depsgraph_get()
    world = arm.matrix_world
    a = np.array(world @ pb.head)
    b = np.array(world @ pb.tail)
    ab = b - a
    denom = float(ab @ ab)
    if denom < 1e-12:
        return None

    ts, ds = [], []
    for obj in deform_meshes(context.scene, arm):
        if obj.vertex_groups.get(pb.name) is None:
            continue
        idx, w = sparse_groups(obj).get(pb.name, (np.zeros(0, int), np.zeros(0)))
        sel = idx[w >= min_weight]
        if not len(sel):
            continue
        pts = _skinned_world(obj, depsgraph)[sel]
        t = (pts - a) @ ab / denom
        keep = (t >= -0.05) & (t <= 1.05)
        q = a + np.clip(t, 0.0, 1.0)[:, None] * ab
        ts.append(t[keep])
        ds.append(np.linalg.norm(pts - q, axis=1)[keep])

    if not ts:
        return None
    t = np.concatenate(ts)
    d = np.concatenate(ds)
    if not len(d):
        return None

    overall = np.percentile(d, percentile)
    head = d[t < 0.4]
    tail = d[t > 0.6]
    r_head = np.percentile(head, percentile) if len(head) >= 4 else overall
    r_tail = np.percentile(tail, percentile) if len(tail) >= 4 else overall
    return float(r_head), float(r_tail)
