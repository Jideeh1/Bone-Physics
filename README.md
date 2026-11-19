# Bone Physics

A Blender 5.2+ add-on for bone-chain secondary motion (skirts, hair, tails)
that also keeps the **mesh** out of colliders, not just the bones.

## The problem it solves

Classic bone physics simulates bones and collides bones. The mesh is then
skinned to those bones, so geometry that flares out between or away from the
bones (a skirt between its chains, for example) still passes through the legs
even when every bone is outside the collider.

Bone Physics runs two layers each frame:

1. **Bone chains.** Bones marked *Simulate* swing with inertia and gravity and
   are pushed out of colliders.
2. **Vertex collision.** After skinning, each vertex in the mask is a particle
   that follows its skinned position and is pushed out of the same colliders.
   The correction is applied by a Geometry Nodes modifier placed right after
   the Armature modifier.

Colliders can be **bones**: a bone marked as a collider is a tapered capsule
from head to tail. Its radii can be fitted automatically to the skin that bone
deforms. A vertex skips the collider of a bone it is weighted to, so skin never
fights its own bone. Spheres and capsules on regular objects also work.

## Measured on the stand-in skirt rig

`examples/run_skirt.py`: hips, thigh and shin bones, a flared skirt on
10 two-bone chains, legs kicking up into the skirt (80 frames). The check
counts skirt **edges** that cut into a thigh/shin capsule, so cloth stretched
across a leg counts even when every vertex is outside it.

| mode | edge-frames crossing a leg |
|---|---|
| no physics | 2399 |
| bone physics only | 2138 |
| bones + vertex collision | **0** |

How collisions are kept from tunneling:

- Simulated bones collide along their whole length (segment vs capsule), so a
  thigh lifting into the middle of a skirt bone lifts the chain.
- Cloth edges collide too, not just vertices.
- Substeps interpolate colliders, parent bones and the skinned target from
  the previous frame, so a fast kick sweeps through the cloth and pushes it
  from the side the leg arrives on, instead of teleporting inside it.

## Layout

```
bone_physics/
  blender_manifest.toml   extension manifest (Blender 5.2+)
  __init__.py             register / unregister
  vertex_sim.py           vertex layer solver + capsule collision (pure numpy)
  bone_sim.py             bone tail solver (pure numpy)
  runtime.py              per-frame driver: colliders, bone chains, vertex layer
  fit.py                  fit bone collider radii to skin
  gn.py                   Geometry Nodes offset modifier
  weights.py              vertex group helpers
  props.py / operators.py / panel.py   settings, operators, sidebar UI
tests/test_vertex_sim.py  solver unit tests (no Blender needed)
examples/
  skirt_scene.py          stand-in lower body: skirt chains + thighs/shins
  run_skirt.py            none / bones / full comparison, metrics + videos
  model_tool.py           same comparison on a real .blend/.fbx character
  bp_setup.py             shared setup by bone-name regex, measurement, ffmpeg
  demo_scene.py, render_demo.py, verify_penetration.py   first sphere demo
```

## Usage in Blender

1. Install the `bone_physics` folder as an extension (Blender 5.2+).
2. 3D View > sidebar > **Bone Physics**.
3. Pose Mode, select the skirt bones, click **Simulate Selected**. Tune
   Stiffness, Damping, Gravity and Tail Radius, then **Copy to Selected**.
4. Select the thigh (and shin) bones, click **Make Selected Colliders**. Radii
   are fitted to the skin; adjust them or use **Fit Collider Radii** again.
5. Object Mode, select the mesh with the skirt, set **Mask** to a vertex group
   covering the skirt, click **Enable** under Vertex Collision.
6. Play from the first frame. Jumping or scrubbing backward resets the sim.

All distances are in world units (meters).

## Running on a real character

```
python examples/model_tool.py --file Character.blend --list --grep "skirt|thigh"
python examples/model_tool.py --file Character.blend --skirt "skirt" --colliders "thigh" \
    --render --out renders/character --save-blend renders/character_bp.blend
```

The tool builds the skirt mask from the skirt bones' vertex groups. It uses the
rig's own animation if it has one, otherwise it generates leg lifts on the
`--thigh` bones. It writes per-mode MP4s, a side-by-side `comparison.mp4`, and
optionally a configured `.blend`.

## Tests

```
python -m unittest discover -s tests -v       # solvers, no Blender
python examples/run_skirt.py                  # needs the bpy module (pip install bpy==5.2.4, Python 3.13)
```

## Limitations

- Collision is projection-based: a vertex is pushed to the nearest surface.
  Very fast motion can tunnel. Raise Substeps if it does.
- The bone simulation ignores the simulated bones' own keyframes (the target
  is the rest pose relative to the parent).
- No friction, no skirt self-collision, no mesh (triangle) colliders yet.
- Python per-frame cost grows with mask size. Keep the mask to the parts
  that need it.
- Modifiers that change vertex count must sit below the Armature modifier.
