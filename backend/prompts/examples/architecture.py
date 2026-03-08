import cadquery as cq

# ════════════════════════════════════════════════════════════════
#  MEDIEVAL CASTLE — Comprehensive CadQuery Reference Example
#
#  AXIS RULES (read before touching any number):
#    box(X_length,  Y_width,  Z_height)   ← Z is always UP, THIRD arg
#    cylinder(height, radius)             ← height FIRST, radius SECOND
#    centered=(True, True, False)         ← XY centered, floor at Z=0
#    translate((dx, dy, dz))             ← dz lifts object in Z
#
#  LAYOUT (top-down view):
#    Courtyard walls form a square at ±courtyard_r from origin.
#    Keep (central tower) sits at origin, smallest but tallest.
#    Corner towers sit exactly at the 4 corners of the courtyard.
#    Battlements sit on top of walls (Z = wall_height, extruding upward).
# ════════════════════════════════════════════════════════════════

# ── Parameters ────────────────────────────────────────────────
courtyard_r      = 200   # mm — half-span: walls are at ±200 in X and Y
wall_thickness   = 25    # mm — wall slab depth
wall_height      = 120   # mm — Z height of outer walls  ← THIRD in box()
tower_radius     = 40    # mm — corner tower radius
tower_height     = 170   # mm — towers taller than walls ← extrude up in Z
keep_size        = 90    # mm — central keep footprint (square)
keep_height      = 240   # mm — keep is the tallest element ← THIRD in box()
merlon_w         = 18    # mm — battlement tooth width
merlon_h         = 22    # mm — battlement tooth height ← extrude up
merlon_d         = wall_thickness   # mm — same depth as wall

# Derived — compute once, reuse everywhere
wall_span        = courtyard_r * 2  # full wall length (400 mm)

# ── Outer Walls ───────────────────────────────────────────────
# Each wall runs along one side of the courtyard square.
# Translate moves the whole wall to the edge AFTER centering in XY.
#
# N/S walls run in X: box(wall_span, wall_thickness, wall_height)
# E/W walls run in Y: box(wall_thickness, wall_span, wall_height)
north_wall = (
    cq.Workplane("XY")
    .box(wall_span, wall_thickness, wall_height, centered=(True, True, False))
    .translate((0, courtyard_r, 0))          # place at Y=+200
)
south_wall = (
    cq.Workplane("XY")
    .box(wall_span, wall_thickness, wall_height, centered=(True, True, False))
    .translate((0, -courtyard_r, 0))         # place at Y=-200
)
east_wall = (
    cq.Workplane("XY")
    .box(wall_thickness, wall_span, wall_height, centered=(True, True, False))
    .translate((courtyard_r, 0, 0))          # place at X=+200
)
west_wall = (
    cq.Workplane("XY")
    .box(wall_thickness, wall_span, wall_height, centered=(True, True, False))
    .translate((-courtyard_r, 0, 0))         # place at X=-200
)

# ── Corner Towers ─────────────────────────────────────────────
# pushPoints sets XY centres of each tower; extrude rises in Z.
# Towers are taller than walls so they protrude above the wall top.
corner_pts = [
    ( courtyard_r,  courtyard_r),   # NE corner
    (-courtyard_r,  courtyard_r),   # NW corner
    ( courtyard_r, -courtyard_r),   # SE corner
    (-courtyard_r, -courtyard_r),   # SW corner
]
towers = (
    cq.Workplane("XY")
    .pushPoints(corner_pts)
    .circle(tower_radius)
    .extrude(tower_height)           # Z_bottom=0, Z_top=tower_height
)

# ── Central Keep ──────────────────────────────────────────────
# The keep is INSIDE the courtyard, centered at origin.
# It is deliberately much smaller in footprint and much taller.
keep = (
    cq.Workplane("XY")
    .box(keep_size, keep_size, keep_height, centered=(True, True, False))
    # Z_bottom = 0, Z_top = keep_height (tallest element)
)

# ── Battlements (merlons) on North & South walls ──────────────
# Battlements are raised teeth sitting ON TOP of the wall.
# They begin at Z = wall_height (wall top face) and extrude upward.
#
# Spacing: one merlon every (merlon_w * 2.5) mm along wall span.
merlon_spacing = merlon_w * 2.5
merlon_count   = int(wall_span / merlon_spacing) - 1
merlon_xs      = [
    -wall_span / 2 + merlon_spacing * (i + 1)
    for i in range(merlon_count)
]
merlon_pts_n   = [(x, courtyard_r) for x in merlon_xs]
merlon_pts_s   = [(x, -courtyard_r) for x in merlon_xs]

battlements_north = (
    cq.Workplane("XY")
    .pushPoints(merlon_pts_n)
    .rect(merlon_w, merlon_d)
    .extrude(merlon_h)               # extrude up by merlon_h
    .translate((0, 0, wall_height))  # lift to sit on wall top face
)
battlements_south = (
    cq.Workplane("XY")
    .pushPoints(merlon_pts_s)
    .rect(merlon_w, merlon_d)
    .extrude(merlon_h)
    .translate((0, 0, wall_height))
)

# ── Tower Battlements (ring of merlons on each tower cap) ─────
# Small rectangular merlons around the perimeter of each tower top.
tower_merlon_count = 8
import math
tower_merlon_pts = [
    (
        cx + (tower_radius - merlon_w / 2) * math.cos(2 * math.pi * i / tower_merlon_count),
        cy + (tower_radius - merlon_w / 2) * math.sin(2 * math.pi * i / tower_merlon_count),
    )
    for cx, cy in corner_pts
    for i in range(tower_merlon_count)
]
tower_caps = (
    cq.Workplane("XY")
    .pushPoints(tower_merlon_pts)
    .rect(merlon_w, merlon_w)
    .extrude(merlon_h)
    .translate((0, 0, tower_height))   # sit on top of each tower
)

# ── Keep Battlements ──────────────────────────────────────────
keep_merlon_pts = [
    (-keep_size / 2 + merlon_w * (i + 0.5) * 2, 0)
    for i in range(int(keep_size / (merlon_w * 2)))
]
# Place on all four sides by rotating
keep_batt_n = (
    cq.Workplane("XY")
    .pushPoints([(x, keep_size / 2) for x, _ in keep_merlon_pts])
    .rect(merlon_w, merlon_d)
    .extrude(merlon_h)
    .translate((0, 0, keep_height))
)
keep_batt_s = (
    cq.Workplane("XY")
    .pushPoints([(x, -keep_size / 2) for x, _ in keep_merlon_pts])
    .rect(merlon_w, merlon_d)
    .extrude(merlon_h)
    .translate((0, 0, keep_height))
)
keep_batt_e = (
    cq.Workplane("XY")
    .pushPoints([(keep_size / 2, x) for x, _ in keep_merlon_pts])
    .rect(merlon_d, merlon_w)
    .extrude(merlon_h)
    .translate((0, 0, keep_height))
)
keep_batt_w = (
    cq.Workplane("XY")
    .pushPoints([(-keep_size / 2, x) for x, _ in keep_merlon_pts])
    .rect(merlon_d, merlon_w)
    .extrude(merlon_h)
    .translate((0, 0, keep_height))
)

# ── Gatehouse Arch (entrance in the south wall) ───────────────
# Cut a rectangular door opening through the south wall.
# Box sized (gate_w, wall_thickness+2, gate_h) centred on the wall face.
gate_w  = 40   # mm
gate_h  = 80   # mm
gatehouse_cut = (
    cq.Workplane("XY")
    .box(gate_w, wall_thickness + 2, gate_h, centered=(True, True, False))
    .translate((0, -courtyard_r, 0))
)

# ── Assemble Everything ───────────────────────────────────────
result = (
    north_wall
    .union(south_wall)
    .union(east_wall)
    .union(west_wall)
    .union(towers)
    .union(keep)
    .union(battlements_north)
    .union(battlements_south)
    .union(tower_caps)
    .union(keep_batt_n)
    .union(keep_batt_s)
    .union(keep_batt_e)
    .union(keep_batt_w)
    .cut(gatehouse_cut)
)

