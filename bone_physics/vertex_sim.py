"""Vertex-level secondary motion with collision.

Pure numpy, no bpy imports, so it can be unit tested outside Blender.

Each simulated vertex is a particle that is pulled toward its *skinned*
position (where the bones put it). Gravity, damping and edge constraints give
secondary motion, and collision projection keeps the particle outside
colliders. The output is an offset from the skinned position; the Blender
layer writes that offset back to the mesh after the Armature modifier.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True, eq=False)
class Capsule:
    """Segment a-b swept by a radius that tapers linearly from `radius` (at a)
    to `radius_b` (at b). A sphere is a capsule with a == b.

    `ignore` is an optional (N,) bool mask of vertices this collider skips,
    e.g. vertices that are skinned to the collider bone itself.
    """

    a: np.ndarray
    b: np.ndarray
    radius: float
    radius_b: Optional[float] = None
    ignore: Optional[np.ndarray] = None

    @property
    def rb(self):
        return self.radius if self.radius_b is None else self.radius_b

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


def _closest_on_segment(p, a, b):
    """Returns (t, q): clamped parameter along a-b and the closest points."""
    ab = b - a
    denom = float(ab @ ab)
    if denom < 1e-12:
        return np.zeros(len(p)), np.broadcast_to(a, p.shape).copy()
    t = np.clip((p - a) @ ab / denom, 0.0, 1.0)
    return t, a + t[:, None] * ab


def penetration_depth(p, collider):
    """Signed depth of each point inside the collider (> 0 means inside)."""
    t, q = _closest_on_segment(p, collider.a, collider.b)
    radius = collider.radius + (collider.rb - collider.radius) * t
    return radius - np.linalg.norm(p - q, axis=1)


def fallback_normals(seg_dirs, a, b):
    """Push directions for contacts lying exactly on a collider's axis, where
    "away from the axis" is undefined: perpendicular to both the segment and
    the axis (or to the axis alone, or +Z for spheres)."""
    axis = b - a
    n_axis = np.linalg.norm(axis)
    out = np.tile(np.array([0.0, 0.0, 1.0]), (len(seg_dirs), 1))
    if n_axis < 1e-9:
        return out
    axis = axis / n_axis
    cand = np.cross(seg_dirs, axis)
    norm = np.linalg.norm(cand, axis=1)
    ok = norm > 1e-9
    out[ok] = cand[ok] / norm[ok, None]
    # Segment parallel to the axis (or a point): any perpendicular to the axis.
    ref = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    perp = np.cross(axis, ref)
    out[~ok] = perp / np.linalg.norm(perp)
    return out


def closest_segments(p0, p1, a, b):
    """Closest points between many segments p0-p1 (N,3) and one segment a-b.

    Returns (s, t, c1, c2): parameters on p0-p1 and a-b, and the points.
    """
    d1 = p1 - p0
    d2 = b - a
    r = p0 - a
    A = np.einsum("ij,ij->i", d1, d1)
    E = float(d2 @ d2)
    F = r @ d2
    n = len(p0)
    eps = 1e-12
    if E <= eps:
        t = np.zeros(n)
        s = np.where(A > eps, np.clip(-np.einsum("ij,ij->i", r, d1) / np.maximum(A, eps), 0, 1), 0.0)
    else:
        C = np.einsum("ij,ij->i", d1, r)
        B = d1 @ d2
        denom = A * E - B * B
        s = np.where(denom > eps, np.clip((B * F - C * E) / np.where(denom > eps, denom, 1.0), 0, 1), 0.0)
        t = (B * s + F) / E
        lo, hi = t < 0.0, t > 1.0
        safe_a = np.maximum(A, eps)
        s = np.where(lo, np.clip(-C / safe_a, 0, 1), s)
        s = np.where(hi, np.clip((B - C) / safe_a, 0, 1), s)
        t = np.clip(t, 0.0, 1.0)
        degenerate = A <= eps
        s = np.where(degenerate, 0.0, s)
        t = np.where(degenerate, np.clip(F / E, 0, 1), t)
    c1 = p0 + d1 * s[:, None]
    c2 = a + d2 * t[:, None]
    return s, t, c1, c2


def segment_depth(p0, p1, collider):
    """How deep each segment p0-p1 reaches into the collider (> 0 = crossing)."""
    _, t, c1, c2 = closest_segments(p0, p1, collider.a, collider.b)
    radius = collider.radius + (collider.rb - collider.radius) * t
    return radius - np.linalg.norm(c1 - c2, axis=1)


def push_edges_out(p, edges, collider, thickness):
    """Push edges that cross a collider out (in place), moving both ends so
    the contact point clears the surface. Catches faces spanning a thin limb
    even when every vertex is outside it."""
    if not len(edges):
        return
    i0, i1 = edges[:, 0], edges[:, 1]
    s, t, c1, c2 = closest_segments(p[i0], p[i1], collider.a, collider.b)
    d = c1 - c2
    dist = np.linalg.norm(d, axis=1)
    radius = collider.radius + (collider.rb - collider.radius) * t + thickness
    hit = dist < radius
    if collider.ignore is not None:
        hit &= ~(collider.ignore[i0] | collider.ignore[i1])
    if not np.any(hit):
        return
    i0, i1, s, d, dist, radius = i0[hit], i1[hit], s[hit], d[hit], dist[hit], radius[hit]
    normal = d / np.where(dist > 1e-9, dist, 1.0)[:, None]
    degenerate = dist <= 1e-9
    if np.any(degenerate):
        normal[degenerate] = fallback_normals(p[i1[degenerate]] - p[i0[degenerate]], collider.a, collider.b)
    pen = (radius - dist)[:, None] * normal
    w0, w1 = 1.0 - s, s
    norm = (w0 * w0 + w1 * w1)[:, None]
    delta = np.zeros_like(p)
    count = np.zeros(len(p))
    np.add.at(delta, i0, pen * w0[:, None] / norm)
    np.add.at(delta, i1, pen * w1[:, None] / norm)
    np.add.at(count, i0, 1.0)
    np.add.at(count, i1, 1.0)
    p += delta / np.maximum(count, 1.0)[:, None]


def push_out(p, collider, thickness):
    """Project points out of a (tapered) capsule, in place.

    For tapered capsules the surface point is taken radially from the closest
    axis point, which is exact for constant radius and a close approximation
    for gentle tapers such as limbs.
    """
    t, q = _closest_on_segment(p, collider.a, collider.b)
    d = p - q
    dist = np.linalg.norm(d, axis=1)
    radius = collider.radius + (collider.rb - collider.radius) * t + thickness
    inside = dist < radius
    if collider.ignore is not None:
        inside &= ~collider.ignore
    if not np.any(inside):
        return
    safe = np.where(dist > 1e-9, dist, 1.0)
    normal = d / safe[:, None]
    degenerate = dist <= 1e-9
    if np.any(degenerate):
        normal[degenerate] = fallback_normals(np.zeros((int(degenerate.sum()), 3)), collider.a, collider.b)
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
                push_edges_out(p, edges, collider, params.thickness)

        offset = p - skin
        norms = np.linalg.norm(offset, axis=1)
        if params.max_offset > 0.0:
            over = norms > params.max_offset
            offset[over] *= (params.max_offset / norms[over])[:, None]

        # Vertices outside the mask stay exactly on the skinned pose.
        offset *= np.clip(weights, 0.0, 1.0)[:, None]
        self.p = skin + offset
        return offset
