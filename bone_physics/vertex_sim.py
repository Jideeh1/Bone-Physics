"""Vertex-level secondary motion with collision.

Pure numpy, no bpy imports, so it can be unit tested outside Blender.

Each simulated vertex is a particle that is pulled toward its *skinned*
position (where the bones put it). Gravity, damping and edge constraints give
secondary motion, and collision projection keeps the particle outside
colliders. The output is an offset from the skinned position; the Blender
layer writes that offset back to the mesh after the Armature modifier.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Capsule:
    """Segment a-b swept by `radius`. A sphere is a capsule with a == b."""

    a: np.ndarray
    b: np.ndarray
    radius: float

    @staticmethod
    def sphere(center, radius):
        c = np.asarray(center, dtype=np.float64)
        return Capsule(c, c.copy(), float(radius))


@dataclass
class SimParams:
    stiffness: float = 0.25        # 0..1, pull toward skinned pose per step
    damping: float = 0.9           # 0..1, velocity kept per step
    gravity_scale: float = 1.0
    thickness: float = 0.01        # collision skin added to every collider
    max_offset: float = 0.15       # hard cap on distance from skinned pose
    edge_stiffness: float = 0.5    # 0 disables edge (shape-keeping) constraints
    iterations: int = 8            # constraint solver iterations per step


def _closest_point_on_segment(p, a, b):
    ab = b - a
    denom = float(ab @ ab)
    if denom < 1e-12:
        return np.broadcast_to(a, p.shape).copy()
    t = np.clip((p - a) @ ab / denom, 0.0, 1.0)
    return a + t[:, None] * ab


def push_out(p, collider, thickness):
    """Project points out of a capsule (in place). Returns nothing."""
    q = _closest_point_on_segment(p, collider.a, collider.b)
    d = p - q
    dist = np.linalg.norm(d, axis=1)
    radius = collider.radius + thickness
    inside = dist < radius
    if not np.any(inside):
        return
    safe = np.where(dist > 1e-9, dist, 1.0)
    normal = d / safe[:, None]
    degenerate = dist <= 1e-9
    normal[degenerate] = (0.0, 0.0, 1.0)  # point exactly on the axis: push up
    penetration = radius - dist
    p[inside] += normal[inside] * penetration[inside, None]


def _solve_edges(p, edges, rest, k):
    """One Jacobi pass of distance constraints. Returns the corrected array."""
    a = edges[:, 0]
    b = edges[:, 1]
    d = p[b] - p[a]
    dist = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
    corr = (0.5 * k * (dist - rest) / dist)[:, None] * d
    delta = np.zeros_like(p)
    deg = np.zeros(len(p))
    np.add.at(delta, a, corr)
    np.add.at(delta, b, -corr)
    np.add.at(deg, a, 1.0)
    np.add.at(deg, b, 1.0)
    return p + delta / np.maximum(deg, 1.0)[:, None]


class VertexLayer:
    """Persistent per-vertex simulation state for one mesh.

    Call `step` once per frame, in order. If the frame sequence breaks,
    call `reset` (the runtime layer does this automatically).
    """

    def __init__(self):
        self.p = None        # current simulated positions, (N, 3)
        self.p_prev = None   # previous simulated positions, (N, 3)

    @property
    def count(self):
        return 0 if self.p is None else len(self.p)

    def reset(self, skin):
        skin = np.asarray(skin, dtype=np.float64)
        self.p = skin.copy()
        self.p_prev = skin.copy()

    def step(self, skin, weights, edges, colliders, gravity, dt, params):
        """Advance one step. Returns offsets (N, 3) from the skinned pose.

        skin       (N, 3) skinned positions, local space of the mesh
        weights    (N,)   0..1 per-vertex simulation influence (mask)
        edges      (E, 2) int vertex index pairs
        colliders  list of Capsule, local space
        gravity    (3,)   gravity vector, local space
        dt         seconds
        """
        skin = np.asarray(skin, dtype=np.float64)
        weights = np.asarray(weights, dtype=np.float64)
        edges = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
        gravity = np.asarray(gravity, dtype=np.float64)

        if self.p is None or self.p.shape != skin.shape:
            self.reset(skin)

        stiffness = float(np.clip(params.stiffness, 0.0, 1.0))
        p = self.p
        velocity = (p - self.p_prev) * params.damping
        self.p_prev = p.copy()

        # Verlet integration, then a spring back toward the skinned pose.
        p = p + velocity + gravity[None, :] * (dt * dt * params.gravity_scale)
        p = p + (skin - p) * stiffness

        # Edge rest lengths come from the skinned shape, so the flare keeps
        # the shape the bones give it and only deviates when pushed.
        rest = None
        if len(edges) and params.edge_stiffness > 0.0:
            rest = np.linalg.norm(skin[edges[:, 1]] - skin[edges[:, 0]], axis=1)

        for _ in range(max(1, int(params.iterations))):
            if rest is not None:
                p = _solve_edges(p, edges, rest, params.edge_stiffness)
            for collider in colliders:
                push_out(p, collider, params.thickness)

        offset = p - skin
        norms = np.linalg.norm(offset, axis=1)
        if params.max_offset > 0.0:
            over = norms > params.max_offset
            offset[over] *= (params.max_offset / norms[over])[:, None]

        # Vertices outside the mask stay exactly on the skinned pose.
        offset *= np.clip(weights, 0.0, 1.0)[:, None]
        self.p = skin + offset
        return offset
