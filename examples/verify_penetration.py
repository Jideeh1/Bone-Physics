"""Headless check: how many mesh vertices sit inside the collider, per frame,
with physics off vs on.

    python examples/verify_penetration.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import bone_physics  # noqa: E402
import demo_scene  # noqa: E402
from bone_physics import runtime  # noqa: E402

TOLERANCE = 0.005  # metres of allowed overlap


def world_positions(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    try:
        n = len(mesh.vertices)
        flat = np.empty(n * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", flat)
    finally:
        eval_obj.to_mesh_clear()
    local = flat.reshape(n, 3).astype(np.float64)
    m = np.array(obj.matrix_world)
    return local @ m[:3, :3].T + m[:3, 3]


def run(sim_on, frames):
    tube, collider = demo_scene.build(frames=frames)
    scene = bpy.context.scene
    center = np.array(collider.matrix_world.translation)
    radius = collider.bp_collider.radius

    if sim_on:
        bpy.context.view_layer.objects.active = tube
        scene.frame_set(1)
        bpy.ops.bp.toggle_mesh()

    results = []
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        if sim_on:
            runtime.on_frame_change(scene)
        pts = world_positions(tube)
        depth = radius - np.linalg.norm(pts - center, axis=1)
        inside = depth > TOLERANCE
        results.append((frame, int(inside.sum()), float(max(depth.max(), 0.0))))

    runtime.reset_all()
    return results


def main():
    frames = 72
    bone_physics.register()
    off = run(False, frames)
    on = run(True, frames)

    print(f"{'frame':>5} {'off: verts in':>14} {'max depth':>10} | {'on: verts in':>13} {'max depth':>10}")
    for (f, n_off, d_off), (_, n_on, d_on) in zip(off, on):
        print(f"{f:>5} {n_off:>14} {d_off:>10.4f} | {n_on:>13} {d_on:>10.4f}")

    total_off = sum(n for _, n, _ in off)
    total_on = sum(n for _, n, _ in on)
    print(f"\nvertex-frames inside collider: off={total_off}  on={total_on}")


if __name__ == "__main__":
    main()
