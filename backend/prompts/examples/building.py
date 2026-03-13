import cadquery as cq
import math

# Two-storey building — canonical architectural example
# Demonstrates: Z-stacking floors, pushPoints for columns, window cut-outs

# ── Parameters ──────────────────────────────────────────────────────
bldg_l       = 800.0    # mm — building length (X)
bldg_w       = 500.0    # mm — building width  (Y)
wall_t       =  20.0    # mm — wall thickness
floor_h      = 300.0    # mm — height of each storey
n_floors     =   2      # number of storeys
roof_t       =  15.0    # mm — flat roof slab thickness
col_dia      =  30.0    # mm — corner column diameter
col_inset    =  col_dia / 2.0 + 5.0   # mm — column centre inset from building corner
window_w     = 100.0    # mm — window opening width
window_h     =  80.0    # mm — window opening height

# ── Derived ──────────────────────────────────────────────────────────
total_wall_h = floor_h * n_floors

# ── North wall ────────────────────────────────────────────────────────
north_wall = (
    cq.Workplane("XY")
    .box(bldg_l, wall_t, total_wall_h, centered=(True, True, False))
    .translate((0.0, bldg_w / 2.0 - wall_t / 2.0, 0.0))
)

# ── South wall ────────────────────────────────────────────────────────
south_wall = (
    cq.Workplane("XY")
    .box(bldg_l, wall_t, total_wall_h, centered=(True, True, False))
    .translate((0.0, -(bldg_w / 2.0 - wall_t / 2.0), 0.0))
)

# ── East wall ─────────────────────────────────────────────────────────
east_wall = (
    cq.Workplane("XY")
    .box(wall_t, bldg_w - wall_t * 2.0, total_wall_h, centered=(True, True, False))
    .translate((bldg_l / 2.0 - wall_t / 2.0, 0.0, 0.0))
)

# ── West wall ─────────────────────────────────────────────────────────
west_wall = (
    cq.Workplane("XY")
    .box(wall_t, bldg_w - wall_t * 2.0, total_wall_h, centered=(True, True, False))
    .translate((-bldg_l / 2.0 + wall_t / 2.0, 0.0, 0.0))
)

# ── Floor/ceiling slab at mid-height ─────────────────────────────────
mid_slab = (
    cq.Workplane("XY")
    .box(bldg_l - wall_t * 2.0, bldg_w - wall_t * 2.0, roof_t, centered=(True, True, False))
    .translate((0.0, 0.0, floor_h))
)

# ── Roof slab ─────────────────────────────────────────────────────────
roof_slab = (
    cq.Workplane("XY")
    .box(bldg_l, bldg_w, roof_t, centered=(True, True, False))
    .translate((0.0, 0.0, total_wall_h))
)

# ── 4 corner columns ─────────────────────────────────────────────────
cx = bldg_l / 2.0 - col_inset
cy = bldg_w / 2.0 - col_inset
col_pts = [(cx, cy), (-cx, cy), (cx, -cy), (-cx, -cy)]
columns = (
    cq.Workplane("XY")
    .pushPoints(col_pts)
    .circle(col_dia / 2.0)
    .extrude(total_wall_h + roof_t)
)

# ── Union all solids first ─────────────────────────────────────────────
result = (
    north_wall
    .union(south_wall)
    .union(east_wall)
    .union(west_wall)
    .union(mid_slab)
    .union(roof_slab)
    .union(columns)
)

# ── Cut window openings into the north face (upper + lower storey) ────
# Two windows per storey on north wall, spaced evenly
win_z_lower = floor_h * 0.25             # window bottom from floor level
win_z_upper = floor_h + floor_h * 0.25  # window bottom on upper storey
win_y_cut   = bldg_w / 2.0 + wall_t    # cut depth through wall

window_cutter_1 = (
    cq.Workplane("XY")
    .box(window_w, win_y_cut, window_h, centered=(True, True, False))
    .translate((-bldg_l * 0.25, 0.0, win_z_lower))
)
window_cutter_2 = (
    cq.Workplane("XY")
    .box(window_w, win_y_cut, window_h, centered=(True, True, False))
    .translate((bldg_l * 0.25, 0.0, win_z_lower))
)
window_cutter_3 = (
    cq.Workplane("XY")
    .box(window_w, win_y_cut, window_h, centered=(True, True, False))
    .translate((-bldg_l * 0.25, 0.0, win_z_upper))
)
window_cutter_4 = (
    cq.Workplane("XY")
    .box(window_w, win_y_cut, window_h, centered=(True, True, False))
    .translate((bldg_l * 0.25, 0.0, win_z_upper))
)

result = (
    result
    .cut(window_cutter_1)
    .cut(window_cutter_2)
    .cut(window_cutter_3)
    .cut(window_cutter_4)
)
