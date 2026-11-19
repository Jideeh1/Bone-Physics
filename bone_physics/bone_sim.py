"""Bone-chain secondary motion (the "goo physics" part). Pure numpy.

Each simulated bone is a particle at its tail. The head is fixed by the parent
(simulated or animated). Every step the tail is integrated with inertia and
gravity, pulled toward where the animated pose would put it, pushed out of
colliders, and projected back to the bone's length. The Blender layer turns
the tail position back into a pose rotation.
"""

from dataclasses import dataclass

import numpy as np

from .vertex_sim import push_out


@dataclass
class BoneParams:
    stiffness: float = 0.1      # 0..1 pull toward the animated pose per step
    damping: float = 0.85       # 0..1 velocity kept per step
    gravity_scale: float = 1.0
    radius: float = 0.02        # collision radius of the bone tail
    iterations: int = 4


class TailState:
    __slots__ = ("x", "x_prev")

    def __init__(self, x):
        self.x = np.array(x, dtype=np.float64)
        self.x_prev = self.x.copy()


def _fix_length(pts, head, length, fallback_dir):
    d = pts - head
    n = np.linalg.norm(d, axis=1)
    out = np.empty_like(pts)
    ok = n > 1e-9
    out[ok] = head + d[ok] / n[ok, None] * length
    out[~ok] = head + fallback_dir * length
    return out


def step_tail(state, head, target_tail, length, colliders, gravity, dt, params):
    """Advance one tail particle. Returns the new tail position (3,).

    head, target_tail, gravity: (3,) world space. colliders: list of Capsule.
    dt == 0 resolves collisions and length without adding motion.
    """
    head = np.asarray(head, dtype=np.float64)
    target_tail = np.asarray(target_tail, dtype=np.float64)
    gravity = np.asarray(gravity, dtype=np.float64)

    rest_dir = target_tail - head
    rest_len = np.linalg.norm(rest_dir)
    fallback = rest_dir / rest_len if rest_len > 1e-9 else np.array([0.0, 0.0, 1.0])

    velocity = (state.x - state.x_prev) * params.damping
    state.x_prev = state.x.copy()
    x = state.x + velocity + gravity * (dt * dt * params.gravity_scale)
    x = x + (target_tail - x) * float(np.clip(params.stiffness, 0.0, 1.0))

    pts = x[None, :]
    for _ in range(max(1, int(params.iterations))):
        pts = _fix_length(pts, head, length, fallback)
        for collider in colliders:
            push_out(pts, collider, params.radius)
    pts = _fix_length(pts, head, length, fallback)  # bones never stretch

    state.x = pts[0].copy()
    return state.x
