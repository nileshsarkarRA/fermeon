import cadquery as cq

# Mounting bracket — L-shaped aluminum plate with bolt holes
# Material: Al 6061-T6

# ── Parameters ────────────────────────────────────────────────
base_length   = 100   # mm — horizontal base
base_width    = 50    # mm
wall_height   = 60    # mm — vertical upright
thickness     = 5     # mm — uniform plate thickness
hole_dia      = 6.5   # mm — M6 clearance holes
hole_margin   = 12    # mm — hole center from edges
fillet_r      = 3     # mm — corner fillets

# ── Base plate ────────────────────────────────────────────────
base = (
    cq.Workplane("XY")
    .box(base_length, base_width, thickness)
)

# ── Vertical upright ──────────────────────────────────────────
upright = (
    cq.Workplane("XY")
    .box(thickness, base_width, wall_height)
    .translate((-(base_length/2 - thickness/2), 0, wall_height/2))
)

# ── Combine into L-bracket ────────────────────────────────────
bracket = base.union(upright)

# ── Mounting holes on base ────────────────────────────────────
bracket = (
    bracket
    .faces(">Z")
    .workplane()
    .pushPoints([
        (base_length/2 - hole_margin, base_width/2 - hole_margin),
        (base_length/2 - hole_margin, -(base_width/2 - hole_margin)),
        (-(base_length/2 - hole_margin - thickness*2), base_width/2 - hole_margin),
        (-(base_length/2 - hole_margin - thickness*2), -(base_width/2 - hole_margin)),
    ])
    .hole(hole_dia)
)

# ── Mounting holes on upright ────────────────────────────────
bracket = (
    bracket
    .faces("<X")
    .workplane()
    .pushPoints([
        (0, wall_height/2 - hole_margin),
        (0, -(wall_height/2 - hole_margin - thickness)),
    ])
    .hole(hole_dia)
)

# ── Fillets on outer L-corner ────────────────────────────────
result = bracket.edges("|Y").fillet(fillet_r)
