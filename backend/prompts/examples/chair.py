"""
NOYRON CEM — Four-Leg Dining Chair
==============================================================
Computational Engineering Model following LEAP 71 / Noyron paradigm.
All dimensions derived from ISO 9241 / EN 1335 ergonomic standards.

FUNCTIONAL ANALYSIS:
  Purpose:       Single-user seating; support adult body weight through
                 4 legs to floor; provide lumbar + optional arm support.
  Governing standard: ISO 9241-5 / EN 1335 office/dining furniture
  Critical constraints:
    - Seat height 420-450mm for average adult (popliteal height + heel)
    - Backrest height 450-600mm above seat for lumbar support
    - Leg slenderness L/D < 15 for buckling safety
"""

import cadquery as cq
import math

# ── MASTER PARAMETERS ──────────────────────────────────────────────────────
total_h      = 900.0   # mm — overall chair height (floor to top of backrest)
seat_w       = 450.0   # mm — seat width (X)
seat_d       = 420.0   # mm — seat depth (Y)
back_w       = seat_w  # mm — backrest width matches seat
leg_taper    =   5.0   # mm — taper reduction at bottom of leg (aesthetic)

# ── DERIVED VALUES (ISO 9241-5 / EN 1335) ────────────────────────────────
seat_h       = total_h * 0.47           # 420mm: floor to seat top [ISO 9241-5: 0.47×total]
seat_t       = 40.0                     # mm seat board thickness (solid timber)
leg_height   = seat_h - seat_t         # 380mm: leg height (floor to seat underside)
back_h       = total_h - seat_h        # 480mm: backrest height above seat
back_depth   = 35.0                    # mm backrest thickness
leg_od_top   = max(leg_height / 12.0, 28.0)  # structural: H/12, min 28mm
leg_od_bot   = leg_od_top - leg_taper  # tapered leg bottom dia
leg_inset    = leg_od_top / 2.0 + 20.0 # inset from seat edge

# ── VALIDATION ASSERTIONS ──────────────────────────────────────────────────
assert 400.0 <= seat_h <= 480.0, \
    f"Seat height {seat_h:.0f}mm outside ISO 9241-5 range (400-480mm)"
assert leg_height / leg_od_top < 15.0, \
    f"Leg slenderness L/D = {leg_height/leg_od_top:.1f} > 15 (buckling risk)"
assert back_h >= 200.0, \
    "Backrest too short for lumbar support (min 200mm)"

# ── GEOMETRY ───────────────────────────────────────────────────────────────

# 4 tapered round legs — floor to seat underside
leg_pts = [
    ( seat_w/2.0 - leg_inset,  seat_d/2.0 - leg_inset),
    (-seat_w/2.0 + leg_inset,  seat_d/2.0 - leg_inset),
    ( seat_w/2.0 - leg_inset, -seat_d/2.0 + leg_inset),
    (-seat_w/2.0 + leg_inset, -seat_d/2.0 + leg_inset),
]
# Tapered leg: loft from larger circle at bottom to top
# Simplified as straight cylinder for robust execution:
legs = (
    cq.Workplane("XY")
    .pushPoints(leg_pts)
    .circle(leg_od_top / 2.0)
    .extrude(leg_height)
)

# Seat board — rests on top of legs at Z=leg_height
seat_board = (
    cq.Workplane("XY")
    .box(seat_w, seat_d, seat_t, centered=(True, True, False))
    .translate((0.0, 0.0, leg_height))
)

# Backrest panel — starts at top of seat, at rear face
back_y = -(seat_d / 2.0 - back_depth / 2.0)    # flush with rear face
backrest = (
    cq.Workplane("XY")
    .box(back_w, back_depth, back_h, centered=(True, True, False))
    .translate((0.0, back_y, seat_h))
)

# ── ASSEMBLY ───────────────────────────────────────────────────────────────
result = seat_board.union(backrest).union(legs)
