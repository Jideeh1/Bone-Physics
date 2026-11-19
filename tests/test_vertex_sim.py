"""Unit tests for the pure-numpy solver. Runs without Blender:

    python -m unittest discover -s tests -v
"""

import importlib.util
import pathlib
import unittest

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "vertex_sim", ROOT / "bone_physics" / "vertex_sim.py"
)
vs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vs)


def params(**kw):
    base = dict(stiffness=0.0, damping=1.0, gravity_scale=0.0, thickness=0.0,
                max_offset=0.0, edge_stiffness=0.0, iterations=4)
    base.update(kw)
    return vs.SimParams(**base)


class CollisionTests(unittest.TestCase):
    def test_points_inside_sphere_are_pushed_to_surface(self):
        sphere = vs.Capsule.sphere([0, 0, 0], 1.0)
        skin = np.array([[0.5, 0, 0], [0, 0.2, 0.3], [-0.1, -0.1, 0.1]])
        layer = vs.VertexLayer()
        layer.reset(skin)
        off = layer.step(skin, np.ones(3), np.zeros((0, 2)), [sphere],
                         np.zeros(3), 1 / 24, params(thickness=0.01))
        final = skin + off
        dist = np.linalg.norm(final, axis=1)
        self.assertTrue(np.all(dist >= 1.01 - 1e-6), dist)

    def test_points_outside_are_untouched(self):
        sphere = vs.Capsule.sphere([0, 0, 0], 1.0)
        skin = np.array([[3.0, 0, 0]])
        layer = vs.VertexLayer()
        layer.reset(skin)
        off = layer.step(skin, np.ones(1), np.zeros((0, 2)), [sphere],
                         np.zeros(3), 1 / 24, params())
        np.testing.assert_allclose(off, 0.0, atol=1e-9)

    def test_capsule_collision(self):
        cap = vs.Capsule(np.array([0, 0, -1.0]), np.array([0, 0, 1.0]), 0.5)
        skin = np.array([[0.1, 0.0, 0.0]])  # beside the axis, inside the radius
        layer = vs.VertexLayer()
        layer.reset(skin)
        off = layer.step(skin, np.ones(1), np.zeros((0, 2)), [cap],
                         np.zeros(3), 1 / 24, params())
        self.assertAlmostEqual(np.linalg.norm((skin + off)[0, :2]), 0.5, places=6)


class DynamicsTests(unittest.TestCase):
    def test_gravity_moves_free_vertex_down(self):
        skin = np.array([[0.0, 0.0, 0.0]])
        layer = vs.VertexLayer()
        layer.reset(skin)
        off = layer.step(skin, np.ones(1), np.zeros((0, 2)), [],
                         np.array([0, 0, -9.8]), 1 / 24,
                         params(gravity_scale=1.0))
        self.assertLess(off[0, 2], 0.0)

    def test_spring_returns_vertex_to_skin(self):
        skin = np.array([[0.0, 0.0, 0.0]])
        layer = vs.VertexLayer()
        layer.reset(np.array([[0.2, 0.0, 0.0]]))  # starts displaced
        for _ in range(60):
            off = layer.step(skin, np.ones(1), np.zeros((0, 2)), [],
                             np.zeros(3), 1 / 24, params(stiffness=0.3))
        self.assertLess(np.linalg.norm(off), 1e-3)

    def test_max_offset_is_respected(self):
        skin = np.zeros((4, 3))
        layer = vs.VertexLayer()
        layer.reset(skin)
        off = layer.step(skin, np.ones(4), np.zeros((0, 2)), [],
                         np.array([0, 0, -50.0]), 1 / 24,
                         params(gravity_scale=1.0, max_offset=0.1))
        self.assertTrue(np.all(np.linalg.norm(off, axis=1) <= 0.1 + 1e-9))

    def test_zero_weight_vertices_stay_on_skin(self):
        sphere = vs.Capsule.sphere([0, 0, 0], 1.0)
        skin = np.array([[0.5, 0, 0], [0.5, 0.1, 0]])
        layer = vs.VertexLayer()
        layer.reset(skin)
        off = layer.step(skin, np.array([0.0, 1.0]), np.zeros((0, 2)), [sphere],
                         np.zeros(3), 1 / 24, params())
        np.testing.assert_allclose(off[0], 0.0, atol=1e-12)
        self.assertGreater(np.linalg.norm(off[1]), 0.0)

    def test_edge_constraint_keeps_neighbours_spaced(self):
        skin = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        edges = np.array([[0, 1]])
        gravity = np.zeros(3)

        def run(k):
            layer = vs.VertexLayer()
            layer.reset(skin)
            layer.p[1] += [0.5, 0.0, 0.0]  # start stretched to 1.5
            off = None
            for _ in range(30):
                off = layer.step(skin, np.ones(2), edges, [], gravity, 1 / 24,
                                 params(stiffness=0.0, edge_stiffness=k,
                                        iterations=8, max_offset=10.0))
            return np.linalg.norm(layer.p[1] - layer.p[0])

        self.assertLess(abs(run(1.0) - 1.0), abs(run(0.0) - 1.0))


if __name__ == "__main__":
    unittest.main()
