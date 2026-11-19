"""Blender-side driver.

Per frame:
  1. gather colliders (collider objects + bones marked as colliders), world space
  2. bone chains: simulate tails, write pose rotations
  3. re-evaluate, so meshes are skinned by the simulated bones
  4. vertex layer: push skinned vertices out of colliders, write offsets
"""

import bpy
import numpy as np
from bpy.app.handlers import persistent
from mathutils import Vector

from . import gn, tips
from .bone_sim import BoneParams, TailState, step_tail
from .vertex_sim import Capsule, SimParams, VertexLayer
from .weights import dense, sparse_groups


_meshes = {}      # mesh object name -> _MeshState
_tails = {}       # (armature name, bone name) -> TailState
_last_frame = {}  # ("mesh"|"arm", name) -> last simulated frame
_prev_colliders = {}  # "frame" -> int, "data" -> snapshot of last frame's colliders


def reset_all():
    tips.clear_cache()
    _meshes.clear()
    _tails.clear()
    _last_frame.clear()
    _arm_prev.clear()
    _prev_colliders.clear()


def forget(obj_name):
    _meshes.pop(obj_name, None)
    _last_frame.pop(("mesh", obj_name), None)
    _last_frame.pop(("arm", obj_name), None)
    _arm_prev.pop(obj_name, None)
    for key in [k for k in _tails if k[0] == obj_name]:
        del _tails[key]


def _avg_scale(matrix):
    return sum(abs(s) for s in matrix.to_scale()) / 3.0


def _fps(scene):
    return scene.render.fps / scene.render.fps_base


# --------------------------------------------------------------------------
# Colliders


class WorldCollider:
    __slots__ = ("a", "b", "ra", "rb", "owner", "bone")

    def __init__(self, a, b, ra, rb, owner, bone=None):
        self.a = np.asarray(a, dtype=np.float64)
        self.b = np.asarray(b, dtype=np.float64)
        self.ra = float(ra)
        self.rb = float(rb)
        self.owner = owner  # object name
        self.bone = bone    # bone name for bone colliders, else None

    def capsule(self):
        return Capsule(self.a, self.b, self.ra, self.rb)


def bone_capsule_world(arm, pb):
    """World-space capsule for a pose bone marked as a collider."""
    c = pb.bp_bone_collider
    world = arm.matrix_world
    return WorldCollider(world @ pb.head, tips.tip_pose_world(arm, pb),
                         c.radius, c.radius_tail, arm.name, pb.name)


def gather_colliders(scene):
    out = []
    for obj in scene.objects:
        s = obj.bp_collider
        if s.enabled:
            world = obj.matrix_world
            radius = s.radius * _avg_scale(world)
            if s.shape == 'SPHERE':
                c = world.translation
                out.append(WorldCollider(c, c, radius, radius, obj.name))
            else:
                half = s.length * 0.5
                out.append(WorldCollider(world @ Vector((0, 0, -half)),
                                         world @ Vector((0, 0, half)),
                                         radius, radius, obj.name))
        if obj.type == 'ARMATURE':
            for pb in obj.pose.bones:
                if pb.bp_bone_collider.enabled:
                    out.append(bone_capsule_world(obj, pb))
    return out


# --------------------------------------------------------------------------
# Bone chains


def sim_bones(arm):
    bones = [pb for pb in arm.pose.bones if pb.bp_bone.simulate]

    def depth(pb):
        d = 0
        while pb.parent is not None:
            pb = pb.parent
            d += 1
        return d

    bones.sort(key=depth)
    return bones


def sim_armatures(scene):
    return [o for o in scene.objects
            if o.type == 'ARMATURE' and any(pb.bp_bone.simulate for pb in o.pose.bones)]


def collider_key(c):
    return (c.owner, c.bone)


def lerp_colliders(prev, now, alpha):
    """Colliders at a point between the previous frame (alpha 0) and now (1).

    `prev` maps collider_key -> (a, b) from the previous frame. Interpolating
    lets substeps see the limb sweep through the frame instead of jumping,
    so cloth is pushed from the side the limb arrives on.
    """
    if not prev or alpha >= 1.0:
        return now
    out = []
    for c in now:
        old = prev.get(collider_key(c))
        if old is None:
            out.append(c)
            continue
        a = old[0] + (c.a - old[0]) * alpha
        b = old[1] + (c.b - old[1]) * alpha
        out.append(WorldCollider(a, b, c.ra, c.rb, c.owner, c.bone))
    return out


def snapshot_colliders(colliders):
    return {collider_key(c): (c.a.copy(), c.b.copy()) for c in colliders}


_arm_prev = {}  # armature name -> {bone name or "": world matrix} from last frame


def step_armature(scene, arm, world_colliders, prev_colliders=None):
    key = ("arm", arm.name)
    frame = scene.frame_current
    if _last_frame.get(key) == frame:
        return
    continuous = _last_frame.get(key) == frame - 1

    world = arm.matrix_world.copy()
    gravity = np.array(scene.gravity)
    bones = sim_bones(arm)
    names = {pb.name for pb in bones}

    # Animated (non-simulated) parents, now and at the previous frame.
    anim_now = {"": world}
    for pb in bones:
        if pb.parent is not None and pb.parent.name not in names:
            anim_now[pb.parent.name] = world @ pb.parent.matrix
    anim_prev = _arm_prev.get(arm.name) if continuous else None

    substeps = max(1, max(pb.bp_bone.substeps for pb in bones)) if continuous else 1
    dt = (1.0 / _fps(scene)) / substeps if continuous else 0.0
    last_q = {}

    for k in range(substeps):
        alpha = (k + 1) / substeps
        frame_colliders = lerp_colliders(prev_colliders if continuous else None,
                                         world_colliders, alpha)
        simulated = {}  # bone name -> world matrix of the simulated pose

        def animated(name):
            now = anim_now.get(name)
            if anim_prev is None or name not in anim_prev or alpha >= 1.0:
                return now
            return anim_prev[name].lerp(now, alpha)

        for pb in bones:
            bone = pb.bone
            parent = pb.parent
            # Pose the bone would have with no local rotation of its own: the
            # parent's (possibly simulated) pose times the rest offset.
            if parent is None:
                base = animated("") @ bone.matrix_local
            else:
                parent_world = simulated.get(parent.name)
                if parent_world is None:
                    parent_world = animated(parent.name)
                base = parent_world @ (parent.bone.matrix_local.inverted() @ bone.matrix_local)

            tip = tips.tip_local(bone)  # next joint, not the (unreliable) tail
            head = base.translation.copy()
            target_tail = base @ tip
            length = (target_tail - head).length

            s = pb.bp_bone
            params = BoneParams(stiffness=s.stiffness, damping=s.damping,
                                gravity_scale=s.gravity_scale, radius=s.radius,
                                iterations=s.iterations)
            skip = {pb.name, parent.name if parent else None}
            colliders = [c.capsule() for c in frame_colliders
                         if not (c.owner == arm.name and c.bone in skip)]

            state = _tails.get((arm.name, pb.name))
            if state is None or not continuous:
                state = TailState(np.array(target_tail))
                _tails[(arm.name, pb.name)] = state

            tail = step_tail(state, np.array(head), np.array(target_tail), length,
                             colliders, gravity, dt, params)

            rot = base.to_3x3().normalized()
            local_dir = rot.inverted() @ (Vector(tail) - head)
            q = tip.normalized().rotation_difference(local_dir)
            last_q[pb.name] = q
            simulated[pb.name] = base @ q.to_matrix().to_4x4()

    for pb in bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = last_q[pb.name]

    _arm_prev[arm.name] = anim_now
    _last_frame[key] = frame


def clear_bone_pose(arm, bones):
    for pb in bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        _tails.pop((arm.name, pb.name), None)
    _last_frame.pop(("arm", arm.name), None)


# --------------------------------------------------------------------------
# Vertex layer


class _MeshState:
    def __init__(self, obj, s):
        mesh = obj.data
        n = len(mesh.vertices)
        self.n = n
        self.groups = sparse_groups(obj)

        if s.mask_group and obj.vertex_groups.get(s.mask_group) is not None:
            mask = dense(self.groups.get(s.mask_group), n)
        else:
            mask = np.ones(n)
        self.active = np.nonzero(mask > 0.0)[0]
        self.weights = mask[self.active]

        remap = np.full(n, -1, dtype=np.int64)
        remap[self.active] = np.arange(len(self.active))
        edges = _mesh_edges(mesh)
        sub = remap[edges] if len(edges) else edges.astype(np.int64)
        self.edges = sub[(sub >= 0).all(axis=1)] if len(sub) else sub.reshape(-1, 2)

        self.layer = VertexLayer()
        self.skin_prev = None
        self._group_cache = {}

    def group_weights(self, name):
        """Weights of a vertex group restricted to the simulated vertices."""
        if name not in self._group_cache:
            entry = self.groups.get(name)
            self._group_cache[name] = None if entry is None else dense(entry, self.n)[self.active]
        return self._group_cache[name]


def _mesh_edges(mesh):
    count = len(mesh.edges)
    flat = np.empty(count * 2, dtype=np.int32)
    if count:
        mesh.edges.foreach_get("vertices", flat)
    return flat.reshape(-1, 2)


def _evaluated_positions(obj, depsgraph):
    """Positions after the offset modifier, with any later modifiers
    temporarily disabled so the vertex count matches the base mesh."""
    later = gn.modifiers_after(obj)
    for m in later:
        m.show_viewport = False
    if later:
        depsgraph.update()
    try:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        try:
            n = len(eval_mesh.vertices)
            flat = np.empty(n * 3, dtype=np.float32)
            eval_mesh.vertices.foreach_get("co", flat)
        finally:
            eval_obj.to_mesh_clear()
    finally:
        for m in later:
            m.show_viewport = True
        if later:
            depsgraph.update()
    if n != len(obj.data.vertices):
        raise RuntimeError(
            f"Bone Physics: '{obj.name}' changes vertex count before the armature "
            "(e.g. Subdivision above it). Move topology modifiers below the armature.")
    return flat.reshape(n, 3).astype(np.float64)


def _local_colliders(obj, state, s, world_colliders):
    to_local = obj.matrix_world.inverted()
    mesh_scale = max(_avg_scale(obj.matrix_world), 1e-9)
    out = []
    for c in world_colliders:
        if c.owner == obj.name and c.bone is None:
            continue
        ignore = None
        if c.bone is not None:
            w = state.group_weights(c.bone)
            if w is not None:
                ignore = w >= s.ignore_weight
                if ignore.all():
                    continue
        a = np.array(to_local @ Vector(c.a))
        b = np.array(to_local @ Vector(c.b))
        out.append(Capsule(a, b, c.ra / mesh_scale, c.rb / mesh_scale, ignore))
    return out


def _params(s, obj):
    # Distances are set in world units; the solver works in mesh-local units.
    scale = max(_avg_scale(obj.matrix_world), 1e-9)
    return SimParams(stiffness=s.stiffness, damping=s.damping, gravity_scale=s.gravity_scale,
                     thickness=s.thickness / scale, max_offset=s.max_offset / scale,
                     edge_stiffness=s.edge_stiffness, iterations=s.iterations)


def step(scene, obj, world_colliders=None, depsgraph=None, prev_colliders=None):
    """Advance one frame for one mesh object. Safe to call repeatedly per frame."""
    s = obj.bp_mesh
    key = ("mesh", obj.name)
    frame = scene.frame_current
    state = _meshes.get(obj.name)
    if state is not None and _last_frame.get(key) == frame:
        return

    if depsgraph is None:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    if world_colliders is None:
        world_colliders = gather_colliders(scene)

    evaluated = _evaluated_positions(obj, depsgraph)
    n = len(evaluated)
    # The evaluated mesh includes our offset modifier; remove it to get the
    # pure skinned pose the bones produce.
    skin_full = evaluated - gn.read_offsets(obj)

    continuous = (state is not None and state.n == n and _last_frame.get(key) == frame - 1)
    if not continuous:
        state = _MeshState(obj, s)
        _meshes[obj.name] = state
        state.layer.reset(skin_full[state.active])

    skin = skin_full[state.active]
    gravity = np.array(obj.matrix_world.inverted().to_3x3() @ Vector(scene.gravity))
    params = _params(s, obj)

    if not continuous:
        # dt=0: no motion, but collisions resolve, so the first frame is clean.
        colliders = _local_colliders(obj, state, s, world_colliders)
        offset = state.layer.step(skin, state.weights, state.edges, colliders, gravity, 0.0, params)
    else:
        # Substeps interpolate the skinned target and the colliders from the
        # previous frame to this one, so fast limbs sweep instead of teleport.
        substeps = max(1, int(s.substeps))
        dt = 1.0 / _fps(scene) / substeps
        skin_prev = state.skin_prev if state.skin_prev is not None else skin
        for k in range(substeps):
            alpha = (k + 1) / substeps
            skin_k = skin_prev + (skin - skin_prev) * alpha
            colliders = _local_colliders(obj, state, s,
                                         lerp_colliders(prev_colliders, world_colliders, alpha))
            offset = state.layer.step(skin_k, state.weights, state.edges, colliders, gravity, dt, params)
    state.skin_prev = skin

    full = np.zeros((n, 3))
    full[state.active] = offset
    gn.write_offsets(obj, full)
    _last_frame[key] = frame


def sim_objects(scene):
    return [o for o in scene.objects if o.type == 'MESH' and o.bp_mesh.enabled]


# --------------------------------------------------------------------------
# Handlers


@persistent
def on_frame_change(scene, *_args):
    armatures = sim_armatures(scene)
    meshes = sim_objects(scene)
    if not armatures and not meshes:
        return

    frame = scene.frame_current
    prev = _prev_colliders.get("data") if _prev_colliders.get("frame") == frame - 1 else None
    if _prev_colliders.get("frame") == frame:
        prev = _prev_colliders.get("before")  # re-run of the same frame

    colliders = gather_colliders(scene)
    for arm in armatures:
        step_armature(scene, arm, colliders, prev)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    if armatures:
        depsgraph.update()  # skin meshes with the simulated bones
        colliders = gather_colliders(scene)
    for obj in meshes:
        step(scene, obj, colliders, depsgraph, prev)

    if _prev_colliders.get("frame") != frame:
        _prev_colliders["before"] = prev
        _prev_colliders["data"] = snapshot_colliders(colliders)
        _prev_colliders["frame"] = frame


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
