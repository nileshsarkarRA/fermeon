"""
Fermeon CEM — Handheld Device (iPod / iPhone / Smartphone)
Parametric model for rectangular handheld consumer electronics.

Geometry:
  - Rounded-rectangle body (box + vertical edge fillets)
  - Screen recess on front face
  - Circular home button below screen (optional)
  - Volume & lock side buttons as small protrusions (optional)

Coordinate system:
  - X = width  (short axis, e.g. 58.6 mm)
  - Y = height (tall axis, e.g. 123.4 mm)
  - Z = thickness, from Z=0 (back) to Z=thickness (front/screen face)
"""

from __future__ import annotations
import math
import cadquery as cq
from pydantic import Field
from typing import Type
from cem.base import ComputationalModel, CEMParams


class HandheldDeviceParams(CEMParams):
    # ── Body ──────────────────────────────────────────────────────────────────
    width: float = Field(default=58.6, description="Device width in mm (short dimension)")
    height: float = Field(default=123.4, description="Device height in mm (tall dimension)")
    thickness: float = Field(default=7.2, description="Device thickness in mm (back to front)")
    corner_radius: float = Field(default=8.0, description="Vertical corner rounding radius in mm")

    # ── Screen ────────────────────────────────────────────────────────────────
    screen_width: float = Field(default=44.0, description="Screen opening width in mm")
    screen_height: float = Field(default=78.0, description="Screen opening height in mm")
    screen_depth: float = Field(default=0.5, description="Screen glass recess depth in mm")
    screen_y_offset: float = Field(
        default=6.0,
        description="How far above device center the screen center sits (mm)",
    )

    # ── Home button ───────────────────────────────────────────────────────────
    has_home_button: bool = Field(default=True, description="Include circular home button")
    home_button_diameter: float = Field(default=14.0, description="Home button outer diameter in mm")

    # ── Side buttons ──────────────────────────────────────────────────────────
    has_side_buttons: bool = Field(default=True, description="Include volume + lock side buttons")
    button_length: float = Field(default=8.0, description="Length of each side button in mm")


class HandheldDeviceModel(ComputationalModel):
    @classmethod
    def get_param_schema(cls) -> Type[HandheldDeviceParams]:
        return HandheldDeviceParams

    def build(self) -> cq.Workplane:
        p: HandheldDeviceParams = self.params

        # ── Safety clamping ───────────────────────────────────────────────────
        max_cr = min(p.width / 2.0 - 1.0, p.height / 2.0 - 1.0)
        corner_r = max(0.5, min(p.corner_radius, max_cr))
        recess_d = min(p.screen_depth, p.thickness * 0.25)
        btn_depth = min(0.4, p.thickness * 0.06)

        # ── 1. Main body — box with filleted vertical corners ─────────────────
        # centered=(True, True, False) → XY centred, Z from 0 to thickness
        body = (
            cq.Workplane("XY")
            .box(p.width, p.height, p.thickness, centered=(True, True, False))
            .edges("|Z").fillet(corner_r)
        )

        # ── 2. Screen recess (front face at Z = thickness) ────────────────────
        # Build a cut tool: solid from Z=(thickness-recess_d) to Z=(thickness+overshoot)
        # so the .cut() removes exactly recess_d from the front face.
        safe_sw = min(p.screen_width,  p.width  - 2.0 * (corner_r + 2.0))
        safe_sh = min(p.screen_height, p.height - 2.0 * (corner_r + 2.0))
        if safe_sw > 2.0 and safe_sh > 2.0:
            sy = p.screen_y_offset
            # Clamp so screen doesn't overlap home-button zone or top edge
            if p.has_home_button:
                btn_r = p.home_button_diameter / 2.0
                btn_margin = corner_r + btn_r + 4.0
                min_screen_bottom = -p.height / 2.0 + btn_margin + btn_r * 2.5
                if sy - safe_sh / 2.0 < min_screen_bottom:
                    sy = min_screen_bottom + safe_sh / 2.0

            screen_tool = (
                cq.Workplane("XY")
                .workplane(offset=p.thickness - recess_d)
                .center(0.0, sy)
                .rect(safe_sw, safe_sh)
                .extrude(recess_d + 0.1)   # slight overshoot for clean boolean
            )
            body = body.cut(screen_tool)

        # ── 3. Home button — circular recess on front face ────────────────────
        if p.has_home_button:
            btn_r = p.home_button_diameter / 2.0
            btn_margin = corner_r + btn_r + 3.0
            btn_y = -p.height / 2.0 + btn_margin

            home_tool = (
                cq.Workplane("XY")
                .workplane(offset=p.thickness - btn_depth)
                .center(0.0, btn_y)
                .circle(btn_r)
                .extrude(btn_depth + 0.1)
            )
            body = body.cut(home_tool)

            # Inner ring detail
            inner_r = btn_r * 0.68
            inner_d = btn_depth * 0.6
            inner_tool = (
                cq.Workplane("XY")
                .workplane(offset=p.thickness - inner_d)
                .center(0.0, btn_y)
                .circle(inner_r)
                .extrude(inner_d + 0.1)
            )
            body = body.cut(inner_tool)

        # ── 4. Side buttons — small box protrusions ────────────────────────────
        if p.has_side_buttons:
            bt = min(2.0, p.thickness * 0.25)   # protrusion thickness
            bl = p.button_length                  # button length (Y axis)
            bh = min(3.5, p.thickness * 0.45)    # button face height (Z axis)
            bz = p.thickness * 0.5               # Z center of buttons

            # Volume UP — left side, upper position
            vol_up = (
                cq.Workplane("XY")
                .box(bt, bl, bh)
                .translate((-p.width / 2.0 - bt * 0.35,  p.height * 0.18, bz))
            )
            body = body.union(vol_up)

            # Volume DOWN — left side, lower position
            vol_dn = (
                cq.Workplane("XY")
                .box(bt, bl, bh)
                .translate((-p.width / 2.0 - bt * 0.35, -p.height * 0.02, bz))
            )
            body = body.union(vol_dn)

            # Lock / power button — right side
            lock_btn = (
                cq.Workplane("XY")
                .box(bt, bl, bh)
                .translate((p.width / 2.0 + bt * 0.35, p.height * 0.22, bz))
            )
            body = body.union(lock_btn)

        return body
