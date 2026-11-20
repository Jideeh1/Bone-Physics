First test build. Requires **Blender 5.2+**.

## Install
1. Download `bone_physics-0.1.0.zip` below (don't unzip it).
2. Blender > Edit > Preferences > Get Extensions > ⌄ (top right) > **Install from Disk...** and pick the zip.
3. 3D View > sidebar (N) > **Bone Physics** tab.

## Quick setup (skirt + thighs)
1. Pose Mode: select the skirt bones > **Simulate Selected**.
2. Select the thigh (and calf) bones > **Make Selected Colliders**. Radii are fitted to the skin automatically.
3. Object Mode: select the mesh with the skirt, set **Mask** to a vertex group covering the skirt, click **Enable** under Vertex Collision.
4. Play from the first frame. Jumping or scrubbing backward resets the simulation.

## What's in it
- Bone-chain physics (inertia, gravity, stiffness) with whole-bone collision.
- Bones as colliders: tapered capsules from the joint to the next joint, fitted to the skin.
- Vertex collision after skinning, so the mesh between skirt bones stays out of the legs.
- Substeps that sweep fast limbs between frames instead of letting them tunnel.

## Known limits
- Tested headlessly on stand-in rigs (including a rip-style FBX), not yet on a real HoYoverse model.
- Colliders are capsules and spheres only. No friction, no skirt self-collision.
- Pure Python: keep the mask to the parts that need it on dense meshes.
- Modifiers that change vertex count must sit below the Armature modifier.
