"""Run the skirt/thigh comparison on a real character (.blend or .fbx).

1) See what's in the file (armatures, bone names, meshes, actions):

    python examples/model_tool.py --file Alice.blend --list --grep "skirt|thigh|calf|leg"

2) Run it (picks the only armature if there is one):

    python examples/model_tool.py --file Alice.blend \\
        --skirt "skirt" --colliders "thigh" --render --out renders/alice

Uses the file's own animation if the rig has one, otherwise generates a
leg-lift test animation on the bones matching --thigh (defaults to the
collider pattern). Saves the configured scene with --save-blend so it can be
opened in Blender 5.2 with the add-on installed.
"""

import argparse
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import bone_physics  # noqa: E402
import bp_setup  # noqa: E402

LABELS = {"none": "No physics", "bones": "Bone physics only", "full": "Bones + vertex collision"}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help=".blend or .fbx")
    p.add_argument("--list", action="store_true")
    p.add_argument("--grep", default="", help="filter for --list bone names")
    p.add_argument("--rig", default=None, help="armature object name")
    p.add_argument("--skirt", default="skirt", help="regex for simulated (skirt) bones")
    p.add_argument("--colliders", default="thigh", help="regex for collider bones")
    p.add_argument("--thigh", default=None, help="regex for bones the test animation lifts")
    p.add_argument("--forward", default="-Y", choices=["-Y", "+Y", "-X", "+X"])
    p.add_argument("--test-anim", action="store_true", help="force the generated animation")
    p.add_argument("--modes", default="none,bones,full")
    p.add_argument("--frames", type=int, default=80)
    p.add_argument("--render", action="store_true")
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--out", default=os.path.join(ROOT, "renders", "model"))
    p.add_argument("--save-blend", default=None)
    return p.parse_args(argv)


def load(path):
    path = os.path.abspath(path)
    if path.lower().endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    elif path.lower().endswith(".fbx"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        raise SystemExit("unsupported file type (use .blend or .fbx)")


def deformed_by(rig):
    return [o for o in bpy.context.scene.objects if o.type == 'MESH'
            and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]


def list_contents(grep):
    rx = re.compile(grep, re.IGNORECASE) if grep else None
    scene = bpy.context.scene
    print(f"scene '{scene.name}' frames {scene.frame_start}-{scene.frame_end} fps {scene.render.fps}")
    for rig in [o for o in scene.objects if o.type == 'ARMATURE']:
        action = rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None
        print(f"\nARMATURE '{rig.name}' bones={len(rig.pose.bones)} scale={tuple(round(s, 4) for s in rig.scale)} action={action}")
        for pb in rig.pose.bones:
            if rx is None or rx.search(pb.name):
                parent = pb.parent.name if pb.parent else "-"
                print(f"  {pb.name:<40} parent={parent:<30} length={pb.bone.length:.4f}")
        for mesh in deformed_by(rig):
            print(f"  mesh '{mesh.name}': {len(mesh.data.vertices)} verts, "
                  f"{len(mesh.vertex_groups)} groups, modifiers={[m.type for m in mesh.modifiers]}")
    for action in bpy.data.actions:
        print(f"action '{action.name}' range={tuple(action.frame_range)}")


def pick_rig(name):
    rigs = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    if name:
        rig = bpy.context.scene.objects.get(name)
        if rig is None or rig.type != 'ARMATURE':
            raise SystemExit(f"no armature named {name!r}; armatures: {[r.name for r in rigs]}")
        return rig
    if len(rigs) != 1:
        raise SystemExit(f"pass --rig; armatures: {[r.name for r in rigs]}")
    return rigs[0]


def test_animation(rig, pattern, forward, frames):
    """Alternating leg lifts on bones matching `pattern`, toward `forward`."""
    axis = {"-Y": Vector((0, -1, 0)), "+Y": Vector((0, 1, 0)),
            "-X": Vector((-1, 0, 0)), "+X": Vector((1, 0, 0))}[forward]
    legs = bp_setup.match_bones(rig, pattern)
    if not legs:
        raise SystemExit(f"no bones match {pattern!r} for the test animation")
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = None

    def lift_sign(pb):
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.4, 0, 0)
        bpy.context.view_layer.update()
        tip = rig.matrix_world @ pb.tail
        pb.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        rest = rig.matrix_world @ pb.tail
        return 1.0 if (tip - rest).dot(axis) > 0 else -1.0

    # Split legs into two groups by side so they alternate.
    world = rig.matrix_world
    side_axis = Vector((1, 0, 0)) if forward in ("-Y", "+Y") else Vector((0, 1, 0))
    t = frames
    keys = [(1, 0, 0), (int(t * 0.18), 1.1, -0.3), (int(t * 0.35), 0, 0),
            (int(t * 0.53), -0.3, 1.1), (int(t * 0.7), 0, 0), (int(t * 0.82), 0.7, 0.7), (t, 0, 0)]
    for pb in legs:
        sign = lift_sign(pb)
        col = 1 if (world @ pb.head).dot(side_axis) >= 0 else 2
        pb.rotation_mode = 'XYZ'
        for key in keys:
            pb.rotation_euler = (sign * key[col], 0, 0)
            pb.keyframe_insert("rotation_euler", index=0, frame=key[0])
    print(f"test animation on: {[pb.name for pb in legs]}")


def frame_camera(points, forward):
    scene = bpy.context.scene
    lo, hi = points.min(axis=0), points.max(axis=0)
    center = Vector(((lo + hi) / 2).tolist())
    size = float(np.max(hi - lo))
    fwd = {"-Y": Vector((0, -1, 0)), "+Y": Vector((0, 1, 0)),
           "-X": Vector((-1, 0, 0)), "+X": Vector((1, 0, 0))}[forward]
    side = fwd.cross(Vector((0, 0, 1)))
    direction = (fwd * 1.0 + side * -0.55 + Vector((0, 0, 0.15))).normalized()
    cam = bpy.data.objects.new("BP_Cam", bpy.data.cameras.new("BP_Cam"))
    scene.collection.objects.link(cam)
    cam.location = center + direction * size * 2.6
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_start = size * 0.01
    cam.data.clip_end = size * 100
    scene.camera = cam
    if not any(o.type == 'LIGHT' for o in scene.objects):
        sun = bpy.data.objects.new("BP_Sun", bpy.data.lights.new("BP_Sun", 'SUN'))
        sun.data.energy = 3.0
        sun.rotation_euler = (0.85, 0.15, 0.4)
        scene.collection.objects.link(sun)


def main():
    args = parse_args()
    bone_physics.register()
    load(args.file)
    if args.list:
        list_contents(args.grep)
        return

    modes = args.modes.split(",")
    os.makedirs(args.out, exist_ok=True)
    results = {}
    for mode in modes:
        load(args.file)  # fresh copy per mode
        scene = bpy.context.scene
        rig = pick_rig(args.rig)
        has_action = bool(rig.animation_data and rig.animation_data.action)
        if args.test_anim or not has_action:
            test_animation(rig, args.thigh or args.colliders, args.forward, args.frames)
            scene.frame_start, scene.frame_end = 1, args.frames
        scene.frame_set(scene.frame_start)

        meshes = deformed_by(rig)
        info = bp_setup.setup(bpy.context, rig, meshes, args.skirt, args.colliders, mode)
        meshes = [m for m in meshes if info["masks"][m.name].any()]
        if not meshes:
            raise SystemExit("no mesh has vertices weighted to the skirt bones")
        if mode == modes[0]:
            print("skirt bones:", info["skirt"])
            print("collider radii (head, tail):", info["colliders"])
            print("skirt meshes:", [m.name for m in meshes])

        if args.render:
            pts = np.concatenate([bp_setup.world_positions(m)[info["masks"][m.name] > 0] for m in meshes])
            frame_camera(pts, args.forward)
            scene.render.engine = 'CYCLES'
            scene.cycles.device = 'CPU'
            scene.cycles.samples = args.samples
            scene.render.resolution_x, scene.render.resolution_y = 560, 640
            scene.render.resolution_percentage = 100
            scene.render.image_settings.file_format = 'PNG'

        if args.save_blend and mode == modes[-1]:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend), copy=True)

        frames_dir = os.path.join(args.out, mode) if args.render else None
        if frames_dir:
            os.makedirs(frames_dir, exist_ok=True)
        results[mode] = bp_setup.run_frames(scene, rig, meshes, info, frames_dir, mode)
        if frames_dir:
            bp_setup.encode(frames_dir, os.path.join(args.out, f"{mode}.mp4"))

    print("\nsummary:")
    for m in modes:
        rows = results[m]
        print(f"  {m:<6} edge-frames crossing={sum(r[1] for r in rows):>6} "
              f"frames with penetration={sum(1 for r in rows if r[1] > 0):>4} "
              f"max depth={max(r[2] for r in rows):.4f}")
    if args.render and len(modes) > 1:
        print("wrote", bp_setup.side_by_side(
            [(os.path.join(args.out, m), LABELS.get(m, m)) for m in modes],
            os.path.join(args.out, "comparison.mp4")))


if __name__ == "__main__":
    main()
