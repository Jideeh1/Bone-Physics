"""Skirt + thighs comparison on the stand-in rig.

    python examples/run_skirt.py                 # metrics only
    python examples/run_skirt.py --render        # + frames, per-mode MP4, side-by-side MP4
    python examples/run_skirt.py --save-blend renders/skirt_full.blend --modes full

Modes: none, bones (classic bone physics), full (bones + vertex collision).
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import bone_physics  # noqa: E402
import bp_setup  # noqa: E402
import skirt_scene  # noqa: E402

LABELS = {"none": "No physics", "bones": "Bone physics only", "full": "Bones + vertex collision"}
SKIRT = r"^Skirt_"
COLLIDERS = r"^(Thigh|Shin)\."


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--modes", default="none,bones,full")
    p.add_argument("--frames", type=int, default=80)
    p.add_argument("--render", action="store_true")
    p.add_argument("--out", default=os.path.join(ROOT, "renders", "skirt"))
    p.add_argument("--save-blend", default=None, help="save the scene after setup (last mode)")
    return p.parse_args(argv)


def main():
    args = parse_args()
    modes = args.modes.split(",")
    bone_physics.register()
    os.makedirs(args.out, exist_ok=True)

    results = {}
    for mode in modes:
        rig, body, skirt = skirt_scene.build(frames=args.frames)
        info = bp_setup.setup(bpy.context, rig, [skirt], SKIRT, COLLIDERS, mode)
        if mode == modes[0]:
            print("fitted collider radii (head, tail):", json.dumps(info["colliders"], indent=1))
        if args.save_blend and mode == modes[-1]:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
        frames_dir = os.path.join(args.out, mode) if args.render else None
        if frames_dir:
            os.makedirs(frames_dir, exist_ok=True)
        rows = bp_setup.run_frames(bpy.context.scene, rig, [skirt], info, frames_dir, mode)
        results[mode] = rows
        if frames_dir:
            bp_setup.encode(frames_dir, os.path.join(args.out, f"{mode}.mp4"))

    print()
    header = "frame " + " ".join(f"{m + ' edges':>11} {'depth':>7}" for m in modes)
    print(header)
    for i in range(args.frames):
        cells = " ".join(f"{results[m][i][1]:>11} {results[m][i][2]:>7.3f}" for m in modes)
        print(f"{i + 1:>5} {cells}")
    summary = {m: {"edge_frames_crossing": sum(r[1] for r in results[m]),
                   "frames_with_penetration": sum(1 for r in results[m] if r[1] > 0),
                   "max_depth": max(r[2] for r in results[m])} for m in modes}
    print("\nsummary:", json.dumps(summary, indent=1))
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    if args.render and len(modes) > 1:
        out = bp_setup.side_by_side([(os.path.join(args.out, m), LABELS.get(m, m)) for m in modes],
                                    os.path.join(args.out, "comparison.mp4"))
        print("wrote", out)


if __name__ == "__main__":
    main()
