"""Where a bone really ends.

Bone tails are unreliable in imported game rigs: FBX has no tails, so after
import they can be arbitrarily long and point anywhere. The physical segment
of a bone is head -> next joint, so the "tip" is:

  1. the head of its child farthest from it (the next joint, skipping twist
     bones that sit near the head), or
  2. for a chain end, its tail if that looks sane (roughly continues the
     parent and is a plausible length), or
  3. the parent's direction and length continued past the head.

Tips are returned in the bone's local rest space, so pose matrices map them.
"""

from mathutils import Vector

_cache = {}  # (armature data name, bone name) -> Vector (bone-local tip)


def clear_cache():
    _cache.clear()


def _parent_segment(bone):
    """Head and tip (armature rest space) of the parent, or None."""
    parent = bone.parent
    if parent is None:
        return None
    tip = parent.matrix_local @ tip_local(parent)
    return parent.head_local.copy(), tip


def _tip_rest(bone):
    head = bone.head_local
    children = list(bone.children)
    if children:
        far = max(children, key=lambda c: (c.head_local - head).length)
        if (far.head_local - head).length > 1e-6:
            return far.head_local.copy()

    tail = bone.tail_local
    seg = _parent_segment(bone)
    if seg is None:
        return tail.copy()
    p_head, p_tip = seg
    p_vec = p_tip - p_head
    p_len = p_vec.length
    t_vec = tail - head
    if p_len < 1e-9:
        return tail.copy()
    sane_dir = t_vec.length > 1e-9 and t_vec.normalized().dot(p_vec.normalized()) > 0.5
    sane_len = 0.2 * p_len <= t_vec.length <= 5.0 * p_len
    if sane_dir and sane_len:
        return tail.copy()
    return head + p_vec.normalized() * p_len


def tip_local(bone):
    """Tip of a (data) Bone in its own local rest space."""
    key = (bone.id_data.name, bone.name)
    tip = _cache.get(key)
    if tip is None:
        tip = bone.matrix_local.inverted() @ _tip_rest(bone)
        _cache[key] = tip
    return tip.copy()


def tip_pose_world(arm, pb):
    """World position of a pose bone's tip in its current pose."""
    return arm.matrix_world @ (pb.matrix @ tip_local(pb.bone))
