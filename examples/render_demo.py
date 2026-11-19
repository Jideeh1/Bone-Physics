"""Render the demo scene to PNG frames, with physics on or off.

    python examples/render_demo.py --sim off --out renders/off
    python examples/render_demo.py --sim on  --out renders/on

Add --video to also encode an MP4 (needs ffmpeg on PATH).
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import bone_physics  # noqa: E402
import demo_scene  # noqa: E402
from bone_physics import runtime  # noqa: E402


def parse_args():
    # Works both as `python examples/render_demo.py ...` and as `blender -b -P ... -- ...`.
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--sim", choices=["on", "off"], default="on")
    p.add_argument("--out", default=os.path.join(ROOT, "renders", "out"))
    p.add_argument("--frames", type=int, default=72)
    p.add_argument("--video", action="store_true")
    return p.parse_args(argv)


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    bone_physics.register()
    tube, _collider = demo_scene.build(frames=args.frames)
    scene = bpy.context.scene

    if args.sim == "on":
        bpy.context.view_layer.objects.active = tube
        scene.frame_set(scene.frame_start)
        bpy.ops.bp.toggle_mesh()

    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        if args.sim == "on":
            runtime.on_frame_change(scene)
        scene.render.filepath = os.path.join(args.out, f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"rendered {frame}/{scene.frame_end}", flush=True)

    if args.video:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            print("ffmpeg not found; skipping video")
        else:
            out_mp4 = os.path.join(args.out, "demo.mp4")
            subprocess.run([
                ffmpeg, "-y", "-framerate", str(scene.render.fps),
                "-i", os.path.join(args.out, "frame_%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4,
            ], check=True)
            print("wrote", out_mp4)


if __name__ == "__main__":
    main()
