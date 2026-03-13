import cadquery as cq
import math

# Ceramic mug — minimal canonical example
# Demonstrates: .revolve() for hollow body of revolution, swept handle

# ── Parameters ──────────────────────────────────────────────────────
mug_h        =  110.0   # mm — mug height
od_base      =   72.0   # mm — outer diameter at base
od_top       =   80.0   # mm — outer diameter at rim (slight taper)
wall_t       =    5.0   # mm — wall thickness
base_t       =    6.0   # mm — base thickness
handle_w     =   12.0   # mm — handle cross-section width
handle_d     =    8.0   # mm — handle cross-section depth
handle_r_outer = 35.0   # mm — outer radius of handle arc

# ── Body — 2D profile revolved around Y axis ─────────────────────────
# Profile is traced as closed polygon in XZ plane (Z=up, X=radial)
r_base_out = od_base / 2.0
r_top_out  = od_top  / 2.0
r_base_in  = r_base_out - wall_t
r_top_in   = r_top_out  - wall_t

pts = [
    (r_base_out, 0.0),           # outer bottom
    (r_top_out,  mug_h),         # outer top (rim)
    (r_top_in,   mug_h),         # inner top (rim interior)
    (r_base_in,  base_t),        # inner wall bottom
    (r_base_in,  base_t),        # base inner edge
    (0.0,         base_t),       # centre of base (solid base radius=0)
    (0.0,         0.0),          # centre bottom
    (r_base_out, 0.0),           # back to outer bottom (close)
]

body = (
    cq.Workplane("XZ")
    .polyline(pts)
    .close()
    .revolve(360, (0, 0, 0), (0, 1, 0))
)

# ── Handle — rectangular cross-section swept along a semicircular arc ──
# Build arc in XZ: handle attaches at mid-height on the +X side of the mug
handle_attach_z = mug_h * 0.60    # top attachment height
handle_low_z    = mug_h * 0.25    # bottom attachment height
handle_cx       = r_top_out + handle_r_outer - handle_w / 2.0

# Simple elliptical handle using loft between two spline points
# Use a 3-point arc approximation via workplane trick
handle_pts = [
    (r_top_out,                  0.0, handle_attach_z),
    (r_top_out + handle_r_outer, 0.0, (handle_attach_z + handle_low_z) / 2.0),
    (r_top_out,                  0.0, handle_low_z),
]
handle_spine = (
    cq.Workplane("XZ")
    .spline([(p[0], p[2]) for p in handle_pts])
)
handle = (
    cq.Workplane("YZ")
    .rect(handle_w, handle_d)
    .sweep(handle_spine)
)

# ── Assembly ─────────────────────────────────────────────────────────
result = body.union(handle)
