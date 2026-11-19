"""Turn the stand-in into something shaped like a typical game rip, then save
it as .blend and .fbx for examples/model_tool.py:

- Bip001-style bone names ("Bip001 L Thigh", "Bip001 L Calf", "Bone_Skirt_..")
- skirt and legs merged into ONE mesh (common in rips)
- centimetre armature: geometry and bones x100, rig object scaled 0.01

    python examples/ripstyle_standin.py OUT_BASENAME [--scramble]

--scramble replaces every bone tail with a short random one (joints stay put),
the way many rip tools leave them, and drops the animation.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import bone_physics  # noqa: E402
import skirt_scene  # noqa: E402

RENAME = {"Hips": "Bip001 Pelvis", "Spine": "Bip001 Spine",
          "Thigh.L": "Bip001 L Thigh", "Shin.L": "Bip001 L Calf",
          "Thigh.R": "Bip001 R Thigh", "Shin.R": "Bip001 R Calf"}


def main():
    args = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else sys.argv[1:]
    scramble = "--scramble" in args
    out = [a for a in args if not a.startswith("--")][-1]
    bone_physics.register()
    rig, body, skirt = skirt_scene.build(80)

    # Bip001-style names (vertex groups follow bone renames).
    for pb in list(rig.pose.bones):
        if pb.name in RENAME:
            new = RENAME[pb.name]
        elif pb.name.startswith("Skirt_"):
            new = "Bone_" + pb.name
        else:
            continue
        old = pb.name
        rig.data.bones[old].name = new
        for mesh in (body, skirt):
            vg = mesh.vertex_groups.get(old)
            if vg is not None:
                vg.name = new

    # Rename the bone path in the action's F-curves to keep the animation.
    action = rig.animation_data.action
    for fc in getattr(action, "fcurves", []):
        for old, new in RENAME.items():
            fc.data_path = fc.data_path.replace(f'"{old}"', f'"{new}"')

    # Centimetre rig: scale geometry and bones x100, object 0.01.
    for mesh in (body, skirt):
        for v in mesh.data.vertices:
            v.co *= 100.0
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    # Read everything first: moving a connected child's head also moves its
    # parent's tail, so scaling in place would double-scale chains.
    rest = {eb.name: (eb.head * 100.0, eb.tail * 100.0) for eb in rig.data.edit_bones}
    for eb in rig.data.edit_bones:
        eb.head, eb.tail = rest[eb.name]
    if scramble:
        import random
        rng = random.Random(7)
        for eb in rig.data.edit_bones:
            eb.use_connect = False
        for eb in rig.data.edit_bones:
            d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized()
            eb.tail = eb.head + d * rng.uniform(2.0, 8.0)
            eb.roll = rng.uniform(-3.0, 3.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    if scramble:  # keyed rotations mean nothing on new bone axes
        rig.animation_data_clear()
        for pb in rig.pose.bones:
            pb.matrix_basis.identity()
    rig.scale = (0.01, 0.01, 0.01)

    # One mesh for body + skirt.
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    skirt.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = body.data.name = "Alice_Standin_Body"
    for m in [m for m in body.modifiers if m.type == 'ARMATURE'][1:]:
        body.modifiers.remove(m)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out + ".blend"))
    bpy.ops.export_scene.fbx(filepath=os.path.abspath(out + ".fbx"), bake_anim=True,
                             add_leaf_bones=False)
    print("saved", out)


if __name__ == "__main__":
    main()
