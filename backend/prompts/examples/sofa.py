"""
NOYRON CEM — Three-Seater Sofa (High-Fidelity Assembly)
==============================================================
Computational Engineering Model following LEAP 71 / Noyron paradigm.
All dimensions derived from ISO 9241 / EN 1335 ergonomic standards.
Geometry EMERGES from function. Zero magic numbers.

FUNCTIONAL ANALYSIS:
  Purpose:       Upholstered seating for 3 adults — distribute body weight
                 via foam cushion over rigid timber frame; provide lumbar,
                 thoracic, and arm support.
  Governing standard: ISO 9241-5 / EN 1335 seating ergonomics
  Critical constraints:
    - Seat height 380-450mm (ankle clearance / popliteal height ergonomics)
    - Armrest 200-250mm above compressed seat surface (EN 1335 = 230mm min)
    - Backrest 600-700mm above seat top for thoracic/lumbar support
    - Backrest tilt 100-105° from floor for passive lumbar comfort
  Manufacturing: CNC-cut hardwood frame; MDF panels; foam upholstery over shell

ASSEMBLY HIERARCHY (all parts connected — no floating geometry):
  Floor (Z=0)
  └── 4× tapered legs  Z=0 → Z=leg_height (300 mm)
  └── Front seat rail  Z=rail_z → Z=leg_height  (flush with leg tops)
  └── Rear seat rail   Z=rail_z → Z=leg_height
  └── Left/right end rails
  └── Seat cushion     Z=leg_height → Z=seat_top_z (420 mm)
  └── 2× cushion divider grooves (3-person sections)
  └── Backrest shell   Z=seat_top_z → Z=(seat_top_z + back_h_above), tilted rearward
  └── Left armrest     Z=leg_height → Z=(leg_height + arm_h_total)
  └── Right armrest    (mirror of left)
  └── 2× armrest top pads (overhanging upholstered cap on each arm)
"""

import cadquery as cq
import math

# ── MASTER PARAMETERS ──────────────────────────────────────────────────────
seat_length    = 2100.0  # mm — three-seater width (X)  [~700 mm/person × 3]
seat_depth     =  900.0  # mm — front-to-back depth (Y)
seat_h_target  =  420.0  # mm — floor to top of seat cushion [ISO 9241-5: 380-480]
cushion_t      =  120.0  # mm — upholstered seat pad thickness [EN 1335]
back_h_above   =  680.0  # mm — backrest height above seat top [EN 1335: 600-750]
back_t         =  150.0  # mm — backrest front-to-back thickness
arm_w          =  140.0  # mm — armrest outer width (X)
arm_h_above    =  240.0  # mm — armrest height above seat top [EN 1335: 200-250]
back_tilt_deg  =   12.0  # degrees — backrest lean rearward from vertical [ergo: 5-15°]
leg_dia_top    =   50.0  # mm — leg diameter at junction with frame (structural size)
leg_dia_bot    =   28.0  # mm — leg diameter at floor (tapered aesthetic foot)

# ── DERIVED VALUES ─────────────────────────────────────────────────────────
leg_height   = seat_h_target - cushion_t               # 300mm — Z of seat cushion bottom
seat_top_z   = seat_h_target                           # 420mm — Z of seat cushion top
arm_h_total  = arm_h_above + cushion_t                 # 360mm — armrest height from seat frame
leg_inset_x  = leg_dia_top / 2.0 + 40.0               # 65mm — lateral inset from seat edge
leg_inset_y  = leg_dia_top / 2.0 + 40.0               # 65mm — fore-aft inset from seat edge

# Rail frame under seat (structural stretchers):
rail_w       = 65.0                                    # mm — cross-section width (face dimension)
rail_h       = 90.0                                    # mm — cross-section height (vertical)
rail_z_bot   = leg_height - rail_h                     # base Z of rails = top_legs - rail_h

# Offset of backrest from seat rear (flush to rear face of seat):
back_y       = -(seat_depth / 2.0 - back_t / 2.0)     # Y-centre of backrest block
back_pivot_y = back_y + back_t / 2.0                  # Y of front face = tilt pivot line

# Clear seat width between armrests:
clear_seat_w = seat_length - 2.0 * arm_w              # 1820mm for 3 persons
section_w    = clear_seat_w / 3.0                     # 606.7mm per person section
groove_w     = 10.0                                    # mm — divider groove width
groove_d     = 30.0                                    # mm — divider groove depth

# Armrest cap (upholstered pad on top of arm box):
arm_cap_extra_w = 20.0                                 # mm — cap overhang on each side (X)
arm_cap_t       = 35.0                                 # mm — cap pad height

# ── VALIDATION ASSERTIONS ──────────────────────────────────────────────────
assert 380.0 <= seat_h_target <= 480.0, \
    f"Seat height {seat_h_target}mm outside ISO 9241-5 range (380-480mm)"
assert leg_height > 0, \
    f"leg_height={leg_height}mm — cushion is taller than full seat height!"
assert arm_h_above >= 200.0, \
    f"Armrest {arm_h_above}mm below EN 1335 minimum (200mm above seat)"
assert back_h_above / back_t <= 12.0, \
    f"Backrest H/t = {back_h_above / back_t:.1f} > 12 (topple / buckling risk)"
assert seat_length > seat_depth, \
    "Sofa must be wider than it is deep"
assert 0.0 < back_tilt_deg <= 20.0, \
    f"Back tilt {back_tilt_deg}° outside ergonomic range (0-20°)"

# ── GEOMETRY ───────────────────────────────────────────────────────────────

# 1. LEGS — tapered (wide at frame, narrow at floor for refined aesthetic)
#    Build one tapered leg at origin, translate 4 copies to corner positions.
#    Loft: bottom circle (leg_dia_bot) at Z=0 → top circle (leg_dia_top) at Z=leg_height
lx1 =  seat_length / 2.0 - leg_inset_x
lx2 = -seat_length / 2.0 + leg_inset_x
ly1 =  seat_depth  / 2.0 - leg_inset_y
ly2 = -seat_depth  / 2.0 + leg_inset_y

base_leg = (
    cq.Workplane("XY")
    .circle(leg_dia_bot / 2.0)
    .workplane(offset=leg_height)
    .circle(leg_dia_top / 2.0)
    .loft()
)
leg_front_right = base_leg.translate(( lx1,  ly1, 0.0))
leg_front_left  = base_leg.translate(( lx2,  ly1, 0.0))
leg_rear_right  = base_leg.translate(( lx1,  ly2, 0.0))
leg_rear_left   = base_leg.translate(( lx2,  ly2, 0.0))

# 2. SEAT RAIL FRAME — structural rectangular stretchers connecting legs
#    Bottom at rail_z_bot, top flush with leg tops (Z=leg_height)
#    Front rail — runs full sofa width at front Y edge
front_rail = (
    cq.Workplane("XY")
    .box(seat_length, rail_w, rail_h, centered=(True, True, False))
    .translate((0.0, seat_depth / 2.0 - rail_w / 2.0, rail_z_bot))
)
# Rear rail — along back Y edge
rear_rail = (
    cq.Workplane("XY")
    .box(seat_length, rail_w, rail_h, centered=(True, True, False))
    .translate((0.0, -seat_depth / 2.0 + rail_w / 2.0, rail_z_bot))
)
# Left end rail — connects front and rear on +X side (inside armrest zone)
left_end_rail = (
    cq.Workplane("XY")
    .box(rail_w, seat_depth - rail_w * 2.0, rail_h, centered=(True, True, False))
    .translate((seat_length / 2.0 - rail_w / 2.0, 0.0, rail_z_bot))
)
# Right end rail — mirror on -X side
right_end_rail = (
    cq.Workplane("XY")
    .box(rail_w, seat_depth - rail_w * 2.0, rail_h, centered=(True, True, False))
    .translate((-seat_length / 2.0 + rail_w / 2.0, 0.0, rail_z_bot))
)

# 3. SEAT CUSHION — full width between armrests, bottom at Z=leg_height
seat_pad = (
    cq.Workplane("XY")
    .box(clear_seat_w, seat_depth, cushion_t, centered=(True, True, False))
    .translate((0.0, 0.0, leg_height))
)

# 3a. CUSHION DIVIDERS — two vertical groove cuts showing 3-person sections
#     Grooves cut from the top face downward into the seat pad
groove_x1 =  section_w / 2.0   # +X divider centre
groove_x2 = -section_w / 2.0   # -X divider centre
groove_cutter_1 = (
    cq.Workplane("XY")
    .box(groove_w, seat_depth, groove_d, centered=(True, True, False))
    .translate((groove_x1, 0.0, seat_top_z - groove_d))
)
groove_cutter_2 = (
    cq.Workplane("XY")
    .box(groove_w, seat_depth, groove_d, centered=(True, True, False))
    .translate((groove_x2, 0.0, seat_top_z - groove_d))
)
seat_cushion = seat_pad.cut(groove_cutter_1).cut(groove_cutter_2)

# 4. BACKREST — tilted rearward by back_tilt_deg from vertical
#    Build upright first (bottom at Z=seat_top_z, rear-flush Y), then rotate.
back_upright = (
    cq.Workplane("XY")
    .box(clear_seat_w, back_t, back_h_above, centered=(True, True, False))
    .translate((0.0, back_y, seat_top_z))
)
# Pivot axis = horizontal X-line at the front-bottom edge of the backrest
# Negative angle → top tilts rearward (away from user), base stays fixed
backrest = back_upright.rotate(
    (0.0,   back_pivot_y, seat_top_z),   # pivot point
    (100.0, back_pivot_y, seat_top_z),   # second point on axis (X direction)
    -back_tilt_deg                        # tilt top rearward
)

# 5. ARMRESTS — structural core box + overhanging upholstered cap on top
arm_core_h = arm_h_total - arm_cap_t       # structural arm box height

# Left armrest core (full seat depth)
left_arm_core = (
    cq.Workplane("XY")
    .box(arm_w, seat_depth, arm_core_h, centered=(True, True, False))
    .translate((seat_length / 2.0 - arm_w / 2.0, 0.0, leg_height))
)
# Left armrest upholstered cap (wider pad on top of core)
left_arm_cap = (
    cq.Workplane("XY")
    .box(arm_w + arm_cap_extra_w * 2.0, seat_depth, arm_cap_t, centered=(True, True, False))
    .translate((seat_length / 2.0 - arm_w / 2.0, 0.0, leg_height + arm_core_h))
)
left_armrest = left_arm_core.union(left_arm_cap)

# Right armrest core (mirror X)
right_arm_core = (
    cq.Workplane("XY")
    .box(arm_w, seat_depth, arm_core_h, centered=(True, True, False))
    .translate((-seat_length / 2.0 + arm_w / 2.0, 0.0, leg_height))
)
# Right armrest cap
right_arm_cap = (
    cq.Workplane("XY")
    .box(arm_w + arm_cap_extra_w * 2.0, seat_depth, arm_cap_t, centered=(True, True, False))
    .translate((-seat_length / 2.0 + arm_w / 2.0, 0.0, leg_height + arm_core_h))
)
right_armrest = right_arm_core.union(right_arm_cap)

# ── ASSEMBLY ───────────────────────────────────────────────────────────────
# Union all sub-assemblies — all parts are geometrically touching / connected:
#   legs touch rail frame  |  rail frame touches seat cushion bottom
#   backrest bottom sits on seat_top_z  |  armrests flank seat cushion
result = (
    leg_front_right
    .union(leg_front_left)
    .union(leg_rear_right)
    .union(leg_rear_left)
    .union(front_rail)
    .union(rear_rail)
    .union(left_end_rail)
    .union(right_end_rail)
    .union(seat_cushion)
    .union(backrest)
    .union(left_armrest)
    .union(right_armrest)
)
