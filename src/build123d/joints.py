"""
Experimental Joint development file
"""
from __future__ import annotations
from math import inf
from abc import ABC, abstractmethod
from typing import overload
from build123d import *


class Joint(ABC):
    """Joint

    Abstract Base Joint class - used to join two components together

    Args:
        parent (Union[Solid, Compound]): object that joint to bound to
    """

    def __init__(self, parent: JointBox):
        self.parent: Solid = parent
        self.connected_to: Joint = None

    @abstractmethod
    def connect_to(self, other: Joint, **kwargs):
        """Connect Joint self by repositioning other"""
        return NotImplementedError

    @property
    @abstractmethod
    def symbol(self) -> Compound:
        """A CAD object positioned in global space to illustrate the joint"""
        return NotImplementedError


class RigidJoint(Joint):
    """RigidJoint

    A rigid joint fixes two components to one another.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        joint_location (Location): global location of joint
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol (XYZ indicator) as bound to part"""
        size = self.parent.bounding_box().diagonal_length() / 12
        return SVG.axes(axes_scale=size).locate(
            self.parent.location * self.relative_location
        )

    def __init__(self, label: str, to_part: JointBox, joint_location: Location):
        self.label = label
        self.to_part = to_part
        self.relative_location = joint_location.relative_to(to_part.location)
        to_part.joints[label] = self
        super().__init__(to_part)

    def connect_to(self, other: RigidJoint):
        """connect_to

        Connect the other joint to self by repositioning other's parent object.

        Args:
            other (RigidJoint): joint to connect to
        """
        other.parent.locate(
            self.parent.location * self.relative_location * other.relative_location
        )

        self.connected_to = other


class RevoluteJoint(Joint):
    """RevoluteJoint

    Component rotates around axis like a hinge.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        axis (Axis): axis of rotation
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
        range (tuple[float, float], optional): (min,max) angle or joint. Defaults to (0, 360).

    Raises:
        ValueError: angle_reference must be normal to axis
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing the axis of rotation as bound to part"""
        radius = self.parent.bounding_box().diagonal_length() / 30

        return Compound.make_compound(
            [
                Edge.make_line((0, 0, 0), (0, 0, radius * 10)),
                Edge.make_circle(radius),
            ]
        ).move(self.parent.location * self.relative_axis.to_location())

    def __init__(
        self,
        label: str,
        to_part: JointBox,
        axis: Axis,
        angle_reference: VectorLike = None,
        range: tuple[float, float] = (0, 360),
    ):
        self.label = label
        self.to_part = to_part
        self.range = range
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), angle_reference)):
                raise ValueError("angle_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self.angle = None
        self.relative_axis = axis.located(to_part.location.inverse())
        to_part.joints[label] = self
        super().__init__(to_part)

    def connect_to(self, other: RigidJoint, angle: float = None):
        """connect_to

        Connect a fixed object to the Revolute joint by repositioning other's parent
        object - a hinge.

        Args:
            other (RigidJoint): joint to connect to
            angle (float, optional): angle within angular range. Defaults to minimum.

        Raises:
            TypeError: other must of type RigidJoint
            ValueError: angle out of range
        """
        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        angle = self.range[0] if angle is None else angle
        if not self.range[0] <= angle <= self.range[1]:
            raise ValueError(f"angle ({angle}) must in range of {self.range}")
        self.angle = angle
        # Avoid strange rotations when angle is zero by using 360 instead
        angle = 360.0 if angle == 0.0 else angle
        rotation = Location(
            Plane(
                origin=(0, 0, 0),
                x_dir=self.angle_reference.rotate(Axis.Z, angle),
                z_dir=(0, 0, 1),
            )
        )
        new_location = (
            self.parent.location
            * self.relative_axis.to_location()
            * rotation
            * other.relative_location.inverse()
        )
        other.parent.locate(new_location)
        self.connected_to = other


class LinearJoint(Joint):
    """LinearJoint

    Component moves along a single axis.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        axis (Axis): axis of linear motion
        range (tuple[float, float], optional): (min,max) position of joint.
            Defaults to (0, inf).
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol of the linear axis positioned relative to_part"""
        radius = (self.range[1] - self.range[0]) / 15
        return Compound.make_compound(
            [
                Edge.make_line((0, 0, self.range[0]), (0, 0, self.range[1])),
                Edge.make_circle(radius),
            ]
        ).move(self.parent.location * self.relative_axis.to_location())

    def __init__(
        self,
        label: str,
        to_part: JointBox,
        axis: Axis,
        range: tuple[float, float] = (0, inf),
    ):
        self.label = label
        self.to_part = to_part
        self.axis = axis
        self.range = range
        self.position = None
        self.relative_axis = axis.located(to_part.location.inverse())
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(to_part)

    @overload
    def connect_to(self, other: RigidJoint, position: float = None):
        """connect_to - RigidJoint

        Connect a fixed object to the linear joint by repositioning other's parent
        object - a slider joint.

        Args:
            other (RigidJoint): joint to connect to
            position (float, optional): position within joint range. Defaults to middle.
        """
        ...

    @overload
    def connect_to(
        self, other: RevoluteJoint, position: float = None, angle: float = None
    ):
        """connect_to - RevoluteJoint

        Connect a rotating object to the linear joint by repositioning other's parent
        object - a pin slot joint.

        Args:
            other (RigidJoint): joint to connect to
            position (float, optional): position within joint range. Defaults to middle.
            angle (float, optional): angle within angular range. Defaults to minimum.
        """
        ...

    def connect_to(self, *args, **kwargs):
        """Reposition parent of other relative to linear joint defined by self"""

        # Parse the input parameters
        other, position, angle = None, None, None
        if args:
            other = args[0]
            position = args[1] if len(args) >= 2 else position
            angle = args[2] if len(args) == 3 else angle

        if kwargs:
            other = kwargs["other"] if "other" in kwargs else other
            position = kwargs["position"] if "position" in kwargs else position
            angle = kwargs["angle"] if "angle" in kwargs else angle

        if not isinstance(other, (RigidJoint, RevoluteJoint)):
            raise TypeError(
                f"other must of type RigidJoint or RevoluteJoint not {type(other)}"
            )

        position = sum(self.range) / 2 if position is None else position
        if not self.range[0] <= position <= self.range[1]:
            raise ValueError(f"position ({position}) must in range of {self.range}")
        self.position = position

        if isinstance(other, RevoluteJoint):
            angle = other.range[0] if angle is None else angle
            if not other.range[0] <= angle <= other.range[1]:
                raise ValueError(f"angle ({angle}) must in range of {other.range}")
            rotation = Location(
                Plane(
                    origin=(0, 0, 0),
                    x_dir=other.angle_reference.rotate(other.relative_axis, angle),
                    z_dir=other.relative_axis.direction,
                )
            )
        else:
            angle = 0.0
            rotation = Location()
        self.angle = angle
        joint_relative_position = (
            Location(
                self.relative_axis.position + self.relative_axis.direction * position,
            )
            * rotation
        )

        other.parent.locate(self.parent.location * joint_relative_position)
        self.connected_to = other


class CylindricalJoint(Joint):
    """CylindricalJoint

    Component rotates around and moves along a single axis like a screw.

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        axis (Axis): axis of rotation and linear motion
        angle_reference (VectorLike, optional): direction normal to axis defining where
            angles will be measured from. Defaults to None.
        linear_range (tuple[float, float], optional): (min,max) position of joint.
            Defaults to (0, inf).
        rotational_range (tuple[float, float], optional): (min,max) angle of joint.
            Defaults to (0, 360).

    Raises:
        ValueError: angle_reference must be normal to axis
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing the cylindrical axis as bound to part"""
        radius = (self.linear_range[1] - self.linear_range[0]) / 15
        return Compound.make_compound(
            [
                Edge.make_line(
                    (0, 0, self.linear_range[0]), (0, 0, self.linear_range[1])
                ),
                Edge.make_circle(radius),
            ]
        ).move(self.parent.location * self.relative_axis.to_location())

    def __init__(
        self,
        label: str,
        to_part: JointBox,
        axis: Axis,
        angle_reference: VectorLike = None,
        linear_range: tuple[float, float] = (0, inf),
        rotational_range: tuple[float, float] = (0, 360),
    ):
        self.label = label
        self.to_part = to_part
        self.axis = axis
        self.linear_position = None
        self.rotational_position = None
        if angle_reference:
            if not axis.is_normal(Axis((0, 0, 0), self.angle_reference)):
                raise ValueError("angle_reference must be normal to axis")
            self.angle_reference = Vector(angle_reference)
        else:
            self.angle_reference = Plane(origin=(0, 0, 0), z_dir=axis.direction).x_dir
        self.rotational_range = rotational_range
        self.linear_range = linear_range
        self.relative_axis = axis.located(to_part.location.inverse())
        to_part.joints[label]: dict[str, Joint] = self
        super().__init__(to_part)

    def connect_to(
        self, other: RigidJoint, position: float = None, angle: float = None
    ):
        """connect_to

        Connect the other joint to self by repositioning other's parent object.

        Args:
            other (RigidJoint): joint to connect to
            position (float, optional): position within joint linear range. Defaults to middle.
            angle (float, optional): angle within rotational range.
                Defaults to rotational_range minimum.

        Raises:
            TypeError: other must be of type RigidJoint
            ValueError: position out of range
            ValueError: angle out of range
        """
        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        position = sum(self.linear_range) / 2 if position is None else position
        if not self.linear_range[0] <= position <= self.linear_range[1]:
            raise ValueError(
                f"position ({position}) must in range of {self.linear_range}"
            )
        self.position = position
        angle = sum(self.rotational_range) / 2 if angle is None else angle
        if not self.rotational_range[0] <= angle <= self.rotational_range[1]:
            raise ValueError(
                f"angle ({angle}) must in range of {self.rotational_range}"
            )
        self.angle = angle

        joint_relative_position = Location(
            self.relative_axis.position + self.relative_axis.direction * position
        )
        joint_rotation = Location(
            Plane(
                origin=(0, 0, 0),
                x_dir=self.angle_reference.rotate(self.relative_axis, angle),
                z_dir=self.relative_axis.direction,
            )
        )
        other.parent.locate(
            self.parent.location * joint_relative_position * joint_rotation
        )
        self.connected_to = other


class BallJoint(Joint):
    """BallJoint

    A component rotates around all 3 axes using a gimbal system (3 nested rotations).

    Args:
        label (str): joint label
        to_part (Union[Solid, Compound]): object to attach joint to
        joint_location (Location): global location of joint
        angle_range (tuple[ tuple[float, float], tuple[float, float], tuple[float, float] ], optional):
            X, Y, Z angle (min, max) pairs. Defaults to ((0, 360), (0, 360), (0, 360)).
        angle_reference (Plane, optional): plane relative to part defining zero degrees of
            rotation. Defaults to Plane.XY.
    """

    @property
    def symbol(self) -> Compound:
        """A CAD symbol representing joint as bound to part"""
        radius = self.parent.bounding_box().diagonal_length() / 30
        circle_x = Edge.make_circle(radius, self.angle_reference)
        circle_y = Edge.make_circle(radius, self.angle_reference.rotated((90, 0, 0)))
        circle_z = Edge.make_circle(radius, self.angle_reference.rotated((0, 90, 0)))

        return Compound.make_compound(
            [
                circle_x,
                circle_y,
                circle_z,
                Compound.make_2d_text("X", radius / 5, halign=Halign.CENTER).locate(
                    circle_x.location_at(0.125) * Rotation(90, 0, 0)
                ),
                Compound.make_2d_text("Y", radius / 5, halign=Halign.CENTER).locate(
                    circle_y.location_at(0.625) * Rotation(90, 0, 0)
                ),
                Compound.make_2d_text("Z", radius / 5, halign=Halign.CENTER).locate(
                    circle_z.location_at(0.125) * Rotation(90, 0, 0)
                ),
            ]
        ).move(self.parent.location * self.relative_location)

    def __init__(
        self,
        label: str,
        to_part: JointBox,
        joint_location: Location,
        angle_range: tuple[
            tuple[float, float], tuple[float, float], tuple[float, float]
        ] = ((0, 360), (0, 360), (0, 360)),
        angle_reference: Plane = Plane.XY,
    ):
        self.label = label
        self.to_part = to_part
        self.relative_location = joint_location.relative_to(to_part.location)
        to_part.joints[label] = self
        self.angle_range = angle_range
        self.angle_reference = angle_reference
        super().__init__(to_part)

    def connect_to(self, other: RigidJoint, angles: RotationLike = None):
        """connect_to

        Connect the other joint to self by repositioning other's parent object.

        Args:
            other (RigidJoint): joint to connect to
            angles (RotationLike, optional): orientation of other's parent relative to
                self. Defaults to the minimums of the angle ranges.

        Raises:
            TypeError: invalid other joint type
            ValueError: angles out of range
        """

        if not isinstance(other, RigidJoint):
            raise TypeError(f"other must of type RigidJoint not {type(other)}")

        rotation = (
            Rotation(*[self.angle_range[i][0] for i in [0, 1, 2]])
            if angles is None
            else Rotation(*angles)
        ) * self.angle_reference.to_location()

        for i, r in zip(
            [0, 1, 2],
            [rotation.orientation.X, rotation.orientation.Y, rotation.orientation.Z],
        ):
            if not self.angle_range[i][0] <= r <= self.angle_range[i][1]:
                raise ValueError(
                    f"angles ({angles}) must in range of {self.angle_range}"
                )

        new_location = (
            self.parent.location
            * self.relative_location
            * rotation
            * other.relative_location.inverse()
        )
        other.parent.locate(new_location)
        self.connected_to = other


class JointBox(Solid):
    """A filleted box with joints

    A box of the given dimensions with all of the edges filleted.

    Args:
        length (float): box length
        width (float): box width
        height (float): box height
        radius (float): edge radius
        taper (float): vertical taper in degrees
    """

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        radius: float = 0.0,
        taper: float = 0.0,
    ):
        # Store the attributes so the object can be copied
        self.length = length
        self.width = width
        self.height = height
        self.joints: dict[str, Joint] = {}

        # Create the object
        obj = Solid.make_box(length, width, height, Plane((-length / 2, -width / 2, 0)))
        with BuildPart() as obj:
            with BuildSketch():
                Rectangle(length, width)
            Extrude(amount=height, taper=taper)
            if radius != 0.0:
                Fillet(*obj.part.edges(), radius=radius)
            Cylinder(width / 4, length, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
        # Initialize the Solid class with the new OCCT object
        super().__init__(obj.part.wrapped)


#
# Base Object
#
# base = JointBox(10, 10, 10)
# base = JointBox(10, 10, 10).locate(Location(Vector(1, 1, 1)))
# base = JointBox(10, 10, 10).locate(Location(Vector(1, 1, 1), (1, 0, 0), 5))
base: JointBox = JointBox(10, 10, 10, taper=3).locate(
    Location(Vector(1, 1, 1), (1, 1, 1), 30)
)
base_top_edges: ShapeList[Edge] = (
    base.edges().filter_by(Axis.X, tolerance=30).sort_by(Axis.Z)[-2:]
)
#
# Rigid Joint
#
fixed_arm = JointBox(1, 1, 5, 0.2)
j1 = RigidJoint("side", base, Plane(base.faces().sort_by(Axis.X)[-1]).to_location())
j2 = RigidJoint(
    "top", fixed_arm, (-Plane(fixed_arm.faces().sort_by(Axis.Z)[-1])).to_location()
)
base.joints["side"].connect_to(fixed_arm.joints["top"])
# or
# j1.connect_to(j2)

#
# Hinge
#
hinge_arm = JointBox(2, 1, 10, taper=1)
swing_arm_hinge_edge: Edge = (
    hinge_arm.edges()
    .group_by(SortBy.LENGTH)[-1]
    .sort_by(Axis.X)[-2:]
    .sort_by(Axis.Y)[0]
)
swing_arm_hinge_axis = swing_arm_hinge_edge.to_axis()
base_corner_edge = base.edges().sort_by(Axis((0, 0, 0), (1, 1, 0)))[-1]
base_hinge_axis = base_corner_edge.to_axis()
j3 = RevoluteJoint("hinge", base, axis=base_hinge_axis, range=(0, 180))
j4 = RigidJoint("corner", hinge_arm, swing_arm_hinge_axis.to_location())
base.joints["hinge"].connect_to(hinge_arm.joints["corner"], angle=90)

#
# Slider
#
slider_arm = JointBox(4, 1, 2, 0.2)
s1 = LinearJoint(
    "slide",
    base,
    axis=Edge.make_mid_way(*base_top_edges, 0.67).to_axis(),
    range=(0, base_top_edges[0].length),
)
s2 = RigidJoint("slide", slider_arm, Location(Vector(0, 0, 0)))
base.joints["slide"].connect_to(slider_arm.joints["slide"], position=8)
# s1.connect_to(s2,8)

#
# Cylindrical
#
hole_axis = Axis(
    base.faces().sort_by(Axis.Y)[0].center(),
    -base.faces().sort_by(Axis.Y)[0].normal_at(),
)
screw_arm = JointBox(1, 1, 10, 0.49)
j5 = CylindricalJoint("hole", base, hole_axis, linear_range=(-10, 10))
j6 = RigidJoint("screw", screw_arm, screw_arm.faces().sort_by(Axis.Z)[-1].location)
j5.connect_to(j6, position=-1, angle=90)

#
# PinSlotJoint
#
j7 = LinearJoint(
    "slot",
    base,
    axis=Edge.make_mid_way(*base_top_edges, 0.33).to_axis(),
    range=(0, base_top_edges[0].length),
)
pin_arm = JointBox(2, 1, 2)
j8 = RevoluteJoint("pin", pin_arm, axis=Axis.Z, range=(0, 360))
j7.connect_to(j8, position=6, angle=60)

#
# BallJoint
#
j9 = BallJoint("socket", base, Plane(base.faces().sort_by(Axis.X)[0]).to_location())
ball = JointBox(2, 2, 2, 0.99)
j10 = RigidJoint("ball", ball, Location(Vector(0, 0, 1)))
j9.connect_to(j10, angles=(10, 20, 30))

if "show_object" in locals():
    show_object(base, name="base", options={"alpha": 0.8})
    show_object(base.joints["side"].symbol, name="side joint")
    show_object(base.joints["hinge"].symbol, name="hinge joint")
    show_object(base.joints["slide"].symbol, name="slot joint")
    show_object(base.joints["slot"].symbol, name="pin slot joint")
    show_object(base.joints["hole"].symbol, name="hole")
    show_object(base.joints["socket"].symbol, name="socket joint")
    show_object(hinge_arm.joints["corner"].symbol, name="hinge_arm joint")
    show_object(fixed_arm, name="fixed_arm", options={"alpha": 0.6})
    show_object(fixed_arm.joints["top"].symbol, name="fixed_arm joint")
    show_object(hinge_arm, name="hinge_arm", options={"alpha": 0.6})
    show_object(slider_arm, name="slider_arm", options={"alpha": 0.6})
    show_object(pin_arm, name="pin_arm", options={"alpha": 0.6})
    show_object(slider_arm.joints["slide"].symbol, name="slider attachment")
    show_object(pin_arm.joints["pin"].symbol, name="pin axis")
    show_object(screw_arm, name="screw_arm")
    show_object(ball, name="ball", options={"alpha": 0.6})