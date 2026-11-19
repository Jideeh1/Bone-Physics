"""Shared setup / measurement for the demo runners and the real-model tool.

Modes:
  none   no physics (bones follow animation only)
  bones  skirt bones simulated + bone colliders (classic bone physics)
  full   bones + vertex collision on the skirt mesh (this add-on's fix)
"""

import os
import re
import shutil
import subprocess

import bpy
import numpy as np

from bone_physics import fit, gn, runtime
from bone_physics.vertex_sim import segment_depth
from bone_physics.weights import dense, sparse_groups

MASK_GROUP = "BP_SkirtMask"

BONE_DEFAULTS = dict(stiffness=0.08, damping=0.85, gravity_scale=1.0, radius=0.02, iterations=6, substeps=4)
MESH_DEFAULTS = dict(stiffness=0.35, damping=0.7, gravity_scale=0.0, edge_stiffness=0.6,
                     iterations=10, substeps=4, thickness=0.02, max_offset=0.25)


def match_bones(rig, pattern):
    rx = re.compile(pattern, re.IGNORECASE)
    return [pb for pb in rig.pose.bones if rx.search(pb.name)]


def build_mask(obj, bone_names):
    """Vertex group = summed weights of the given bones (clamped to 1)."""
    groups = sparse_groups(obj)
    n = len(obj.data.vertices)
    total = np.zeros(n)
    for name in bone_names:
        total += dense(groups.get(name), n)
    total = np.clip(total, 0.0, 1.0)
    vg = obj.vertex_groups.get(MASK_GROUP) or obj.vertex_groups.new(name=MASK_GROUP)
    idx = np.nonzero(total > 0)[0]
    vg.remove(list(range(n)))
    for i in idx:
        vg.add([int(i)], float(total[i]), 'REPLACE')
    return total


def setup(context, rig, meshes, skirt_pattern, collider_pattern, mode,
          bone_params=None, mesh_params=None, percentile=98.0):
    """Configure physics. Returns dict with skirt bones, collider bones, masks."""
    bone_params = {**BONE_DEFAULTS, **(bone_params or {})}
    mesh_params = {**MESH_DEFAULTS, **(mesh_params or {})}
    skirt = match_bones(rig, skirt_pattern)
    colliders = match_bones(rig, collider_pattern)
    if not skirt:
        raise SystemExit(f"no bones match skirt pattern {skirt_pattern!r}")
    if not colliders:
        raise SystemExit(f"no bones match collider pattern {collider_pattern!r}")

    # Colliders are configured in every mode so measurements use the same capsules.
    fitted = {}
    for pb in colliders:
        pb.bp_bone_collider.enabled = True
        radii = fit.fit_bone_radius(context, rig, pb, percentile)
        if radii is not None:
            pb.bp_bone_collider.radius, pb.bp_bone_collider.radius_tail = radii
        fitted[pb.name] = (pb.bp_bone_collider.radius, pb.bp_bone_collider.radius_tail)

    for pb in skirt:
        pb.bp_bone.simulate = mode in ("bones", "full")
        for k, v in bone_params.items():
            setattr(pb.bp_bone, k, v)

    skirt_names = [pb.name for pb in skirt]
    masks = {}
    for obj in meshes:
        masks[obj.name] = build_mask(obj, skirt_names)
        if mode == "full" and masks[obj.name].any():
            s = obj.bp_mesh
            s.mask_group = MASK_GROUP
            for k, v in mesh_params.items():
                setattr(s, k, v)
            gn.ensure(obj)
            s.enabled = True

    runtime.reset_all()
    return {"skirt": skirt_names, "colliders": fitted, "masks": masks}


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


def measure(rig, meshes, info, ignore_weight=0.5, tolerance=0.003):
    """Skirt edges (both ends in the mask) that cut into any collider-bone
    capsule. Counting edges, not vertices, catches cloth stretched across a
    limb even when every vertex sits outside it. Returns (edges, max depth)."""
    capsules = [runtime.bone_capsule_world(rig, rig.pose.bones[name]).capsule()
                for name in info["colliders"]]
    names = list(info["colliders"])
    count, deepest = 0, 0.0
    for obj in meshes:
        mask = info["masks"][obj.name] >= 0.5
        if not mask.any():
            continue
        cache = info.setdefault("_cache", {}).setdefault(obj.name, {})
        if "edges" not in cache:
            n = len(obj.data.vertices)
            flat = np.empty(len(obj.data.edges) * 2, dtype=np.int32)
            obj.data.edges.foreach_get("vertices", flat)
            edges = flat.reshape(-1, 2)
            cache["edges"] = edges[mask[edges].all(axis=1)]
            groups = sparse_groups(obj)
            cache["own"] = {name: dense(groups.get(name), n) >= ignore_weight for name in names}
        edges = cache["edges"]
        pts = world_positions(obj)
        crossing = np.zeros(len(edges), dtype=bool)
        for name, cap in zip(names, capsules):
            own = cache["own"][name]
            depth = segment_depth(pts[edges[:, 0]], pts[edges[:, 1]], cap)
            depth[own[edges].any(axis=1)] = -1.0
            crossing |= depth > tolerance
            deepest = max(deepest, float(depth.max()) if len(depth) else 0.0)
        count += int(crossing.sum())
    return count, deepest


def run_frames(scene, rig, meshes, info, render_dir=None, label=""):
    rows = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        runtime.on_frame_change(scene)
        n_in, depth = measure(rig, meshes, info)
        rows.append((frame, n_in, depth))
        if render_dir:
            scene.render.filepath = os.path.join(render_dir, f"frame_{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
        print(f"[{label}] frame {frame}: {n_in} skirt edges cutting into legs, max depth {depth:.4f}", flush=True)
    return rows


def encode(frames_dir, out_mp4, fps=24):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg not found; skipping", out_mp4)
        return None
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", os.path.join(frames_dir, "frame_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4], check=True)
    return out_mp4


def side_by_side(dirs_labels, out_mp4, fps=24):
    """Stack several frame sequences horizontally with a label on each."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    inputs, filters = [], []
    for i, (d, label) in enumerate(dirs_labels):
        inputs += ["-framerate", str(fps), "-i", os.path.join(d, "frame_%04d.png")]
        text = label.replace(":", r"\:")
        filters.append(f"[{i}:v]drawtext=text='{text}':x=14:y=14:fontsize=26:"
                       f"fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8[v{i}]")
    stack = "".join(f"[v{i}]" for i in range(len(dirs_labels)))
    filters.append(f"{stack}hstack=inputs={len(dirs_labels)}[out]")
    cmd = [ffmpeg, "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[out]", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4]
    result = subprocess.run(cmd)
    if result.returncode != 0:  # drawtext unavailable: stack without labels
        filters = [f"{''.join(f'[{i}:v]' for i in range(len(dirs_labels)))}"
                   f"hstack=inputs={len(dirs_labels)}[out]"]
        cmd = [ffmpeg, "-y", "-loglevel", "error", *inputs, "-filter_complex", filters[0],
               "-map", "[out]", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4]
        subprocess.run(cmd, check=True)
    return out_mp4
