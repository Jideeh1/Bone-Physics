"""Builds the demo scene used for renders and verification.

A tube with a flared top, rigged to two bones. The top bone swings back and
forth, so the flare sweeps into a sphere collider. Run only inside Blender
(or the bpy module).
"""

import math

import bpy
from mathutils import Vector


def clear_scene():
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures,
                       bpy.data.lights, bpy.data.cameras, bpy.data.materials):
        for item in list(collection):
            collection.remove(item)


def _material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def _flared_tube(rings=32, segs=28, height=1.6):
    verts, faces = [], []
    zs = [height * i / rings for i in range(rings + 1)]
    for z in zs:
        t = max(0.0, (z - 0.6) / 1.0)
        r = 0.15 + 0.6 * t * t
        for s in range(segs):
            a = 2.0 * math.pi * s / segs
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(rings):
        for s in range(segs):
            a = i * segs + s
            b = i * segs + (s + 1) % segs
            c = (i + 1) * segs + (s + 1) % segs
            d = (i + 1) * segs + s
            faces.append((a, b, c, d))

    me = bpy.data.meshes.new("FlareTube")
    me.from_pydata(verts, [], faces)
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new("FlareTube", me)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(_material("Tube", (0.8, 0.75, 0.6)))
    return obj, verts


def _rig():
    arm = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", arm)
    bpy.context.collection.objects.link(rig)

    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    base = arm.edit_bones.new("Base")
    base.head = (0, 0, 0)
    base.tail = (0, 0, 0.8)
    upper = arm.edit_bones.new("Upper")
    upper.head = (0, 0, 0.8)
    upper.tail = (0, 0, 1.6)
    upper.parent = base
    upper.use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')

    # Animate the upper bone swinging about Y (so the tip swings along X).
    pb = rig.pose.bones["Upper"]
    pb.rotation_mode = 'XYZ'
    keys = [(1, 0.0), (18, 0.55), (36, -0.55), (54, 0.55), (72, -0.2)]
    for frame, angle in keys:
        pb.rotation_euler.y = angle
        pb.keyframe_insert("rotation_euler", index=1, frame=frame)
    return rig


def _attach(mesh_obj, rig, verts):
    mesh_obj.parent = rig
    mod = mesh_obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = rig

    base = mesh_obj.vertex_groups.new(name="Base")
    upper = mesh_obj.vertex_groups.new(name="Upper")
    for i, (x, y, z) in enumerate(verts):
        t = min(1.0, max(0.0, (z - 0.5) / 0.3))
        w_upper = t * t * (3 - 2 * t)  # smoothstep blend between bones
        upper.add([i], w_upper, 'REPLACE')
        base.add([i], 1.0 - w_upper, 'REPLACE')


def _sphere(name, center, radius):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=center, segments=32, ring_count=16)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(_material("Collider", (0.2, 0.5, 0.9)))
    obj.bp_collider.enabled = True
    obj.bp_collider.shape = 'SPHERE'
    obj.bp_collider.radius = radius
    return obj


def _camera_and_light():
    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (3.4, -3.6, 1.5)
    target = (0.25, 0.0, 0.95)
    direction = (target[0] - cam.location.x, target[1] - cam.location.y, target[2] - cam.location.z)
    cam.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam

    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (0.9, 0.2, 0.6)


def _render_settings(scene, frames):
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.fps = 24
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True


def build(frames=72):
    """Create the demo scene. Returns (mesh_object, collider_object)."""
    clear_scene()
    tube, verts = _flared_tube()
    rig = _rig()
    _attach(tube, rig, verts)
    collider = _sphere("Collider", (0.75, 0.0, 1.25), 0.3)
    _camera_and_light()
    _render_settings(bpy.context.scene, frames)
    return tube, collider
