import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup


class BP_MeshSettings(PropertyGroup):
    """Stored on mesh objects (Object.bp_mesh)."""

    enabled: BoolProperty(
        name="Enabled",
        description="Simulate this mesh's vertices after skinning",
        default=False,
    )
    mask_group: StringProperty(
        name="Mask",
        description="Vertex group that limits simulation. Empty = whole mesh",
        default="",
    )
    stiffness: FloatProperty(
        name="Stiffness",
        description="How strongly vertices are pulled back to the skinned pose each step",
        min=0.0, max=1.0, default=0.25,
    )
    damping: FloatProperty(
        name="Damping",
        description="Fraction of velocity kept each step (lower = settles faster)",
        min=0.0, max=1.0, default=0.9,
    )
    gravity_scale: FloatProperty(
        name="Gravity",
        description="Multiplier on the scene gravity",
        min=0.0, soft_max=3.0, default=1.0,
    )
    edge_stiffness: FloatProperty(
        name="Shape Keep",
        description="Keeps neighboring vertices at their skinned spacing (0 = limp, cloth-like)",
        min=0.0, max=1.0, default=0.5,
    )
    iterations: IntProperty(
        name="Solver Iterations",
        description="Constraint passes per step. More is stiffer and slower",
        min=1, max=64, default=8,
    )
    substeps: IntProperty(
        name="Substeps",
        description="Simulation steps per frame. Raise if fast motion tunnels through colliders",
        min=1, max=16, default=2,
    )
    thickness: FloatProperty(
        name="Collision Thickness",
        description="Skin added around colliders so the mesh sits just outside them",
        subtype='DISTANCE', min=0.0, default=0.01,
    )
    max_offset: FloatProperty(
        name="Max Offset",
        description="Maximum distance a vertex may move away from its skinned position (0 = no limit)",
        subtype='DISTANCE', min=0.0, default=0.15,
    )
    ignore_weight: FloatProperty(
        name="Ignore Own Bone",
        description=(
            "A vertex skips a bone collider when its weight to that bone is at least this. "
            "Stops skin from colliding with the bone that moves it"
        ),
        min=0.0, max=1.0, default=0.5,
    )


class BP_ColliderSettings(PropertyGroup):
    """Stored on any object that should act as a collider (Object.bp_collider).

    Sphere: centered on the object origin.
    Capsule: runs along the object's local Z, centered on the origin.
    Scale on the collider object scales its size.
    """

    enabled: BoolProperty(
        name="Collider",
        description="Mesh vertices are pushed out of this object",
        default=False,
    )
    shape: EnumProperty(
        name="Shape",
        items=[
            ('SPHERE', "Sphere", "Sphere around the object origin"),
            ('CAPSULE', "Capsule", "Capsule along local Z"),
        ],
        default='SPHERE',
    )
    radius: FloatProperty(
        name="Radius",
        subtype='DISTANCE', min=0.0, default=0.2,
    )
    length: FloatProperty(
        name="Length",
        description="Capsule length (ignored for spheres)",
        subtype='DISTANCE', min=0.0, default=0.5,
    )


class BP_BoneSettings(PropertyGroup):
    """Stored on pose bones (PoseBone.bp_bone): bone-chain simulation."""

    simulate: BoolProperty(
        name="Simulate",
        description="Simulate this bone as a jiggle/secondary-motion bone",
        default=False,
    )
    stiffness: FloatProperty(
        name="Stiffness",
        description="Pull back toward the animated pose per step",
        min=0.0, max=1.0, default=0.1,
    )
    damping: FloatProperty(
        name="Damping",
        description="Fraction of velocity kept per step",
        min=0.0, max=1.0, default=0.85,
    )
    gravity_scale: FloatProperty(
        name="Gravity",
        min=0.0, soft_max=3.0, default=1.0,
    )
    radius: FloatProperty(
        name="Tail Radius",
        description="Collision radius of the bone tail",
        subtype='DISTANCE', min=0.0, default=0.02,
    )
    iterations: IntProperty(
        name="Iterations",
        min=1, max=32, default=4,
    )


class BP_BoneColliderSettings(PropertyGroup):
    """Stored on pose bones (PoseBone.bp_bone_collider): bone as a tapered capsule.
    Radii are world units (refit after scaling the armature)."""

    enabled: BoolProperty(
        name="Bone Collider",
        description="Use this bone as a capsule collider (head to tail)",
        default=False,
    )
    radius: FloatProperty(
        name="Head Radius",
        description="Capsule radius at the bone head",
        subtype='DISTANCE', min=0.0, default=0.05,
    )
    radius_tail: FloatProperty(
        name="Tail Radius",
        description="Capsule radius at the bone tail",
        subtype='DISTANCE', min=0.0, default=0.05,
    )
