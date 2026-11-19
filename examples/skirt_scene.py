"""Stand-in for a game character's lower body: hips, thigh and shin bones,
and a flared skirt driven by bone chains, the way skirts are usually rigged.

The legs kick up into the skirt, so thighs and shins sweep through it. Bone
names follow a "Skirt_<chain>_<segment>" / "Thigh.L" / "Shin.L" pattern.
"""

import math

import bpy
from mathutils import Vector

from demo_scene import _material, clear_scene

CHAINS = 10
SEGMENTS = 2
WAIST_Z, HEM_Z = 1.02, 0.60
WAIST_R, HEM_R = 0.19, 0.36
HIP_X, HIP_Z, KNEE_Z, ANKLE_Z = 0.095, 0.93, 0.50, 0.08
ANGLE_OFFSET = math.pi / CHAINS  # no chain sits exactly on a thigh


def _skirt_point(theta, s):
    r = WAIST_R + (HEM_R - WAIST_R) * s
    return Vector((r * math.cos(theta), r * math.sin(theta), WAIST_Z + (HEM_Z - WAIST_Z) * s))


def chain_angle(k):
    return ANGLE_OFFSET + 2.0 * math.pi * k / CHAINS


def skirt_bone_name(k, seg):
    return f"Skirt_{k:02d}_{seg}"


def _build_rig():
    arm = bpy.data.armatures.new("CharacterRig")
    rig = bpy.data.objects.new("CharacterRig", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones

    hips = eb.new("Hips")
    hips.head, hips.tail = (0, 0, HIP_Z), (0, 0, 1.20)
    spine = eb.new("Spine")
    spine.head, spine.tail = (0, 0, 1.20), (0, 0, 1.45)
    spine.parent, spine.use_connect = hips, True

    for side, x in (("L", HIP_X), ("R", -HIP_X)):
        thigh = eb.new(f"Thigh.{side}")
        thigh.head, thigh.tail = (x, 0, HIP_Z), (x, 0, KNEE_Z)
        thigh.parent = hips
        shin = eb.new(f"Shin.{side}")
        shin.head, shin.tail = (x, 0, KNEE_Z), (x, 0, ANKLE_Z)
        shin.parent, shin.use_connect = thigh, True

    for k in range(CHAINS):
        theta = chain_angle(k)
        parent = hips
        for seg in range(SEGMENTS):
            b = eb.new(skirt_bone_name(k, seg))
            b.head = _skirt_point(theta, seg / SEGMENTS)
            b.tail = _skirt_point(theta, (seg + 1) / SEGMENTS)
            b.parent = parent
            b.use_connect = seg > 0
            parent = b

    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def _forward_sign(rig, bone_name):
    """Sign of local-X rotation that swings this leg bone toward -Y (forward)."""
    pb = rig.pose.bones[bone_name]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (0.5, 0, 0)
    bpy.context.view_layer.update()
    tail_y = (rig.matrix_world @ pb.tail).y
    pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    return 1.0 if tail_y < 0 else -1.0


def _animate(rig):
    # (frame, left lift, right lift) in radians; positive = leg forward/up.
    keys = [(1, 0.0, 0.0), (14, 1.15, -0.30), (28, 0.0, 0.0),
            (42, -0.30, 1.15), (56, 0.0, 0.0), (66, 0.75, 0.0), (80, 0.0, 0.0)]
    for side, col in (("L", 1), ("R", 2)):
        thigh = rig.pose.bones[f"Thigh.{side}"]
        shin = rig.pose.bones[f"Shin.{side}"]
        sign = _forward_sign(rig, f"Thigh.{side}")
        thigh.rotation_mode = shin.rotation_mode = 'XYZ'
        for key in keys:
            frame, lift = key[0], key[col]
            thigh.rotation_euler = (sign * lift, 0, 0)
            thigh.keyframe_insert("rotation_euler", index=0, frame=frame)
            # Knee bends back as the thigh lifts.
            shin.rotation_euler = (-sign * max(lift, 0.0) * 1.2, 0, 0)
            shin.keyframe_insert("rotation_euler", index=0, frame=frame)

    hips = rig.pose.bones["Hips"]
    hips.rotation_mode = 'XYZ'
    for frame, yaw in ((1, 0.0), (20, 0.18), (40, -0.18), (60, 0.12), (80, 0.0)):
        hips.rotation_euler = (0, 0, yaw)
        hips.keyframe_insert("rotation_euler", index=2, frame=frame)


def _tube(verts, faces, start, end, r0, r1, rings, segs):
    """Append a tapered open tube from start to end. Returns new vertex range."""
    axis = (end - start)
    length = axis.length
    axis.normalize()
    ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u)
    first = len(verts)
    for i in range(rings + 1):
        t = i / rings
        center = start + axis * (length * t)
        r = r0 + (r1 - r0) * t
        for j in range(segs):
            a = 2 * math.pi * j / segs
            verts.append(center + (u * math.cos(a) + v * math.sin(a)) * r)
    for i in range(rings):
        for j in range(segs):
            a = first + i * segs + j
            b = first + i * segs + (j + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    return first, len(verts)


def _build_body(rig):
    verts, faces = [], []
    parts = []  # (start, end, weight function)
    torso = _tube(verts, faces, Vector((0, 0, 0.90)), Vector((0, 0, 1.45)), 0.165, 0.13, 12, 32)
    parts.append((torso, lambda p: {"Hips": 1.0} if p.z < 1.2 else {"Spine": 1.0}))
    for side, x in (("L", HIP_X), ("R", -HIP_X)):
        thigh = _tube(verts, faces, Vector((x, 0, 0.97)), Vector((x, 0, KNEE_Z)), 0.078, 0.052, 16, 24)
        shin = _tube(verts, faces, Vector((x, 0, KNEE_Z)), Vector((x, 0, ANKLE_Z)), 0.052, 0.034, 16, 24)

        def thigh_w(p, side=side):
            t = min(1.0, max(0.0, (p.z - (KNEE_Z - 0.04)) / 0.08))
            return {f"Thigh.{side}": t, f"Shin.{side}": 1.0 - t}

        parts.append((thigh, thigh_w))
        parts.append((shin, thigh_w))

    me = bpy.data.meshes.new("Body")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    body = bpy.data.objects.new("Body", me)
    bpy.context.collection.objects.link(body)
    body.data.materials.append(_material("Skin", (0.86, 0.66, 0.56)))

    groups = {}
    for (lo, hi), fn in parts:
        for i in range(lo, hi):
            for name, w in fn(verts[i]).items():
                if w <= 0:
                    continue
                g = groups.get(name) or body.vertex_groups.new(name=name)
                groups[name] = g
                g.add([i], w, 'REPLACE')

    body.parent = rig
    body.modifiers.new("Armature", 'ARMATURE').object = rig
    return body


def _build_skirt(rig, rings=18, segs=80):
    verts, faces = [], []
    params = []
    for i in range(rings + 1):
        s = i / rings
        for j in range(segs):
            theta = 2 * math.pi * j / segs
            verts.append(tuple(_skirt_point(theta, s)))
            params.append((theta, s))
    for i in range(rings):
        for j in range(segs):
            a = i * segs + j
            b = i * segs + (j + 1) % segs
            faces.append((a, b, b + segs, a + segs))

    me = bpy.data.meshes.new("Skirt")
    me.from_pydata(verts, [], faces)
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    skirt = bpy.data.objects.new("Skirt", me)
    bpy.context.collection.objects.link(skirt)
    skirt.data.materials.append(_material("Cloth", (0.10, 0.11, 0.17)))

    groups = {}

    def add(name, i, w):
        if w <= 0:
            return
        g = groups.get(name) or skirt.vertex_groups.new(name=name)
        groups[name] = g
        g.add([i], w, 'ADD')

    step = 2 * math.pi / CHAINS
    for i, (theta, s) in enumerate(params):
        u = ((theta - ANGLE_OFFSET) % (2 * math.pi)) / step
        k0 = int(math.floor(u)) % CHAINS
        k1 = (k0 + 1) % CHAINS
        f = u - math.floor(u)
        lower = min(1.0, max(0.0, (s - 0.35) / 0.3))
        for k, wk in ((k0, 1.0 - f), (k1, f)):
            add(skirt_bone_name(k, 0), i, wk * (1.0 - lower))
            add(skirt_bone_name(k, 1), i, wk * lower)

    skirt.parent = rig
    skirt.modifiers.new("Armature", 'ARMATURE').object = rig
    return skirt


def _camera_light_world(scene):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    bpy.context.collection.objects.link(cam)
    cam.location = (1.25, -2.05, 1.0)
    target = Vector((0.0, 0.0, 0.76))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3.5
    sun.rotation_euler = (0.85, 0.15, 0.4)
    bpy.context.collection.objects.link(sun)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = (0.32, 0.34, 0.38, 1.0)
    scene.world = world


def build(frames=80):
    """Returns (rig, body, skirt)."""
    clear_scene()
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)
    rig = _build_rig()
    _animate(rig)
    body = _build_body(rig)
    skirt = _build_skirt(rig)

    scene = bpy.context.scene
    _camera_light_world(scene)
    scene.frame_start, scene.frame_end = 1, frames
    scene.render.fps = 24
    scene.render.resolution_x, scene.render.resolution_y = 560, 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.frame_set(1)
    return rig, body, skirt
