# Bone Physics

A Blender add-on that adds vertex-level secondary motion with collision to
skinned meshes. Bones drive the mesh as usual. Each vertex is then simulated
as a particle that follows its skinned position and is pushed out of
colliders, so flared parts react to colliders instead of passing through them.

Requires **Blender 5.2+**.

## Layout

```
bone_physics/
  blender_manifest.toml   extension manifest
  __init__.py             register / unregister
  vertex_sim.py           pure numpy solver (no bpy; unit tested)
  runtime.py              frame driver: skinned pose, colliders, writes offsets
  gn.py                   Geometry Nodes modifier that applies the offsets
  props.py                per-mesh and per-collider settings
  operators.py            enable/disable, reset
  panel.py                3D View > sidebar > Bone Physics
tests/test_vertex_sim.py  solver unit tests (no Blender needed)
examples/demo_scene.py    flared tube + swinging bone + sphere collider
examples/render_demo.py   render PNG frames (and MP4) with sim on or off
examples/verify_penetration.py   headless count of vertices inside the collider
```

## How it works

1. The Armature modifier produces the skinned pose.
2. Each frame, `runtime.py` reads the evaluated mesh, removes the offsets it
   wrote last frame, and gets the pure skinned positions.
3. `vertex_sim.py` runs Verlet integration, a spring toward the skinned pose,
   edge constraints (keep the skinned spacing), collision projection against
   capsules/spheres, and a max-offset clamp.
4. The offsets are written to the `bp_offset` attribute. A Geometry Nodes
   modifier placed after the armature adds them to the positions.

## Usage

1. Install the add-on (Blender 5.2+, Extensions > Install from Disk, or copy
   the `bone_physics` folder into your extensions/add-ons path).
2. Select a skinned mesh. In the sidebar, open **Bone Physics** and click
   **Enable**.
3. Select any object and tick **Collider** in its Bone Physics panel. Spheres
   and capsules are supported. Scale on the collider object scales its size.
4. Scrub or play the timeline. Simulation runs frame by frame. Scrubbing
   backward, or jumping, resets the simulation.

Tune Stiffness and Shape Keep for how much the flare lags and holds shape,
Solver Iterations and Substeps for stiffness and stability, and Max Offset to
cap how far vertices can travel.

## Tests and demos

Solver unit tests (plain Python + numpy, no Blender):

```
python -m unittest discover -s tests -v
```

Render the demo (needs the `bpy` module from PyPI, Blender 5.2 build):

```
python examples/render_demo.py --sim off --out renders/off --video
python examples/render_demo.py --sim on  --out renders/on  --video
python examples/verify_penetration.py
```

## Limitations (current prototype)

- Colliders are spheres and capsules only. Mesh colliders are not implemented.
- No friction and no self-collision (flare against the body).
- Simulation is per frame and runs in Python. Dense meshes will be slow. The
  mask group should cover only the flared regions.
- Object scale is assumed uniform for collider radii.
- The mesh data must be single-user.
