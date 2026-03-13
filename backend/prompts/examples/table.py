import cadquery as cq
import math

# Dining table — minimal canonical example
# Demonstrates: box + cylinder Z-stacking, pushPoints for legs, centered=(True,True,False)

# ── Parameters ──────────────────────────────────────────────────────
table_l      = 1200.0   # mm — tabletop length (X)
table_w      =  800.0   # mm — tabletop width  (Y)
top_t        =   30.0   # mm — tabletop thickness
table_h      =  750.0   # mm — floor to top of tabletop [dining standard ~720-760]
leg_dia      =   60.0   # mm — round leg diameter
leg_inset    =   80.0   # mm — leg centre inset from table edge

# ── Derived ─────────────────────────────────────────────────────────
leg_h        = table_h - top_t   # 720mm — legs reach from floor to underside of top

# ── 4 legs — pushPoints, Z from floor → underside of top ────────────
lx = table_l / 2.0 - leg_inset
ly = table_w / 2.0 - leg_inset
leg_pts = [(lx, ly), (-lx, ly), (lx, -ly), (-lx, -ly)]

legs = (
    cq.Workplane("XY")
    .pushPoints(leg_pts)
    .circle(leg_dia / 2.0)
    .extrude(leg_h)
)

# ── Tabletop — bottom at Z=leg_h, top at Z=table_h ──────────────────
top = (
    cq.Workplane("XY")
    .box(table_l, table_w, top_t, centered=(True, True, False))
    .translate((0.0, 0.0, leg_h))
)

# ── Assembly ─────────────────────────────────────────────────────────
result = top.union(legs)
