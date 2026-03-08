"""
Fermeon CEM — Sofa/Chair
A fully robust, parameterized model for seating furniture.
"""

import cadquery as cq
from pydantic import BaseModel, Field
from cem.base import ComputationalModel, CEMParams


class SofaParams(CEMParams):
    width: float = Field(default=1800.0, description="Total width of the sofa in mm")
    depth: float = Field(default=800.0, description="Total depth in mm")
    seat_height: float = Field(default=450.0, description="Height from floor to top of seat cushion")
    backrest_height: float = Field(default=850.0, description="Total height from floor to top of backrest")
    leg_height: float = Field(default=150.0, description="Height of the legs")
    armrest_width: float = Field(default=150.0, description="Width of each armrest")
    has_armrests: bool = Field(default=True, description="Whether to include armrests")
    is_sectional: bool = Field(default=False, description="Whether it's an L-shaped sectional sofa")
    sectional_depth: float = Field(default=1500.0, description="Depth of the L-shape extension if sectional")


from typing import Type

class SofaModel(ComputationalModel):
    @classmethod
    def get_param_schema(cls) -> Type[SofaParams]:
        return SofaParams

    def build(self) -> cq.Workplane:
        p: SofaParams = self.params

        # Frame thicknesses
        frame_t = 50.0
        cushion_t = p.seat_height - p.leg_height - frame_t
        if cushion_t < 50:
            cushion_t = 50  # minimum cushion

        # 1. Main Seat Frame
        seat_frame = (
            cq.Workplane("XY")
            .box(p.width, p.depth, frame_t, centered=(True, True, False))
            .translate((0, 0, p.leg_height))
        )

        # 2. Main Seat Cushion
        seat_cushion = (
            cq.Workplane("XY")
            .box(p.width, p.depth, cushion_t, centered=(True, True, False))
            # Move up by leg + frame length
            .translate((0, 0, p.leg_height + frame_t))
            .edges("|Z").fillet(min(20.0, cushion_t / 2.0 - 1.0))
            .edges(">Z").fillet(min(10.0, cushion_t / 4.0 - 1.0))
        )

        # 3. Backrest
        back_thickness = 150.0
        back_height = p.backrest_height - p.leg_height
        backrest = (
            cq.Workplane("XY")
            # Anchor to the back edge of the seat
            .transformed(offset=(0, p.depth/2 - back_thickness/2, p.leg_height))
            .box(p.width, back_thickness, back_height, centered=(True, True, False))
            .edges("|Z").fillet(20)
            .edges(">Z").fillet(20)
        )

        # 4. Legs
        # Place legs at the 4 corners, inset by 50mm
        inset = 50.0
        leg_pts = [
            (p.width/2 - inset, p.depth/2 - inset),
            (-p.width/2 + inset, p.depth/2 - inset),
            (p.width/2 - inset, -p.depth/2 + inset),
            (-p.width/2 + inset, -p.depth/2 + inset),
        ]
        
        # Determine leg shape
        legs = (
            cq.Workplane("XY")
            .pushPoints(leg_pts)
            .circle(25)  # 50mm diameter legs
            .extrude(p.leg_height)
        )

        # 5. Armrests (Optional)
        armrests = None
        if p.has_armrests:
            arm_total_height = p.seat_height + 200.0  # 20 cm above seat cushion top
            arm_z = arm_total_height - p.leg_height   # height of the armrest solid

            # Fillet is clamped so it never exceeds half the armrest wall width
            arm_fillet_v = min(15.0, p.armrest_width / 2.0 - 1.0)
            arm_fillet_top = min(10.0, arm_fillet_v)

            # Build left and right armrests individually — explicit is always safer
            left_arm = (
                cq.Workplane("XY")
                .transformed(offset=(-p.width / 2.0 + p.armrest_width / 2.0, 0.0, p.leg_height))
                .box(p.armrest_width, p.depth, arm_z, centered=(True, True, False))
                .edges("|Z").fillet(arm_fillet_v)
                .edges(">Z").fillet(arm_fillet_top)
            )
            right_arm = (
                cq.Workplane("XY")
                .transformed(offset=(p.width / 2.0 - p.armrest_width / 2.0, 0.0, p.leg_height))
                .box(p.armrest_width, p.depth, arm_z, centered=(True, True, False))
                .edges("|Z").fillet(arm_fillet_v)
                .edges(">Z").fillet(arm_fillet_top)
            )
            armrests = left_arm.union(right_arm)

        # 6. Sectional extension (Optional)
        chaise = None
        if p.is_sectional:
            chaise_w = 800.0  # Default chaise width
            if chaise_w > p.width / 2:
                chaise_w = p.width / 2
                
            chaise_extension = p.sectional_depth - p.depth
            if chaise_extension > 0:
                # Add extra frame and cushion on one side (e.g., left)
                chaise_offset_x = -p.width/2 + chaise_w/2
                chaise_offset_y = -p.depth/2 - chaise_extension/2
                
                chaise_frame = (
                    cq.Workplane("XY")
                    .transformed(offset=(chaise_offset_x, chaise_offset_y, p.leg_height))
                    .box(chaise_w, chaise_extension, frame_t, centered=(True, True, False))
                )
                
                chaise_cush_obj = (
                    cq.Workplane("XY")
                    .transformed(offset=(chaise_offset_x, chaise_offset_y, p.leg_height + frame_t))
                    .box(chaise_w, chaise_extension, cushion_t, centered=(True, True, False))
                    .edges("|Z").fillet(20)
                    .edges(">Z").fillet(10)
                )
                
                # Extra legs for the chaise
                chaise_leg_pts = [
                    (chaise_offset_x - chaise_w/2 + inset, chaise_offset_y - chaise_extension/2 + inset),
                    (chaise_offset_x + chaise_w/2 - inset, chaise_offset_y - chaise_extension/2 + inset)
                ]
                chaise_legs = (
                    cq.Workplane("XY")
                    .pushPoints(chaise_leg_pts)
                    .circle(25)
                    .extrude(p.leg_height)
                )
                
                chaise = chaise_frame.union(chaise_cush_obj).union(chaise_legs)


        # Assembly
        model = seat_frame.union(seat_cushion).union(backrest).union(legs)
        if armrests is not None:
            model = model.union(armrests)
        if chaise is not None:
            model = model.union(chaise)

        return model
