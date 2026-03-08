import cadquery as cq

# Electronics enclosure with lid recess, mounting bosses, and ventilation slots

# ── Parameters ────────────────────────────────────────────────
outer_length   = 120   # mm
outer_width    = 80    # mm
outer_height   = 40    # mm
wall_thickness = 2.5   # mm
floor_thickness = 2.0  # mm
lid_depth      = 5     # mm — how deep lid sits in recess
boss_dia       = 6     # mm — mounting boss outer diameter
boss_hole_dia  = 3.2   # mm — M3 thread bore
corner_r       = 5     # mm — outer corner radius
vent_width     = 2     # mm
vent_count     = 6

# ── Outer shell ───────────────────────────────────────────────
outer = (
    cq.Workplane("XY")
    .rect(outer_length, outer_width)
    .extrude(outer_height)
    .edges("|Z").fillet(corner_r)
)

# ── Inner cavity ──────────────────────────────────────────────
inner_l = outer_length - 2 * wall_thickness
inner_w = outer_width  - 2 * wall_thickness
inner_h = outer_height - floor_thickness

inner_cut = (
    cq.Workplane("XY")
    .rect(inner_l, inner_w)
    .extrude(inner_h)
    .translate((0, 0, floor_thickness))
)

enclosure = outer.cut(inner_cut)

# ── Mounting bosses (4 corners inside) ───────────────────────
boss_offset = (outer_length/2 - wall_thickness - boss_dia/2 - 2)
boss_positions = [
    (boss_offset,  boss_offset/outer_length * outer_width),
    (-boss_offset, boss_offset/outer_length * outer_width),
    (boss_offset,  -boss_offset/outer_length * outer_width),
    (-boss_offset, -boss_offset/outer_length * outer_width),
]

for x, y in boss_positions:
    boss = (
        cq.Workplane("XY")
        .circle(boss_dia / 2)
        .extrude(outer_height - floor_thickness - lid_depth)
        .translate((x, y, floor_thickness))
    )
    boss_hole = (
        cq.Workplane("XY")
        .circle(boss_hole_dia / 2)
        .extrude(outer_height)
        .translate((x, y, 0))
    )
    enclosure = enclosure.union(boss).cut(boss_hole)

result = enclosure
