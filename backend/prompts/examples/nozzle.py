import cadquery as cq

# Conical nozzle — convergent section
# Suitable for fluid/rocket nozzle applications

# ── Parameters ────────────────────────────────────────────────
inlet_od       = 30    # mm — inlet outer diameter
throat_od      = 12    # mm — throat (narrowest) diameter
outlet_od      = 20    # mm — outlet diameter (small divergent section)
wall_thickness = 2.5   # mm — uniform wall thickness
conv_length    = 40    # mm — convergent section length
div_length     = 15    # mm — divergent section length
fillet_r       = 1.5   # mm — fillet at throat

# ── Build outer profile via revolve ──────────────────────────
# Points: (x along axis, r radius) defining the profile
outer_pts = [
    (0,            inlet_od/2),
    (conv_length,  throat_od/2),
    (conv_length + div_length, outlet_od/2),
]

# ── Outer shell (revolve around X axis) ──────────────────────
outer = (
    cq.Workplane("XZ")
    .polyline(outer_pts)
    .close()
    .revolve(360, (0,0,0), (1,0,0))
)

# ── Inner bore (slightly smaller = wall thickness) ────────────
inner_pts = [
    (wall_thickness,                      inlet_od/2  - wall_thickness),
    (conv_length,                          throat_od/2 - wall_thickness),
    (conv_length + div_length - wall_thickness, outlet_od/2 - wall_thickness),
]

inner = (
    cq.Workplane("XZ")
    .polyline(inner_pts)
    .close()
    .revolve(360, (0,0,0), (1,0,0))
)

# ── Hollow nozzle ─────────────────────────────────────────────
result = outer.cut(inner)
