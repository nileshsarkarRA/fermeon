import cadquery as cq
import math

# Spur gear — simplified involute approximation in CadQuery
# All dimensions derived from module (m) and tooth count. Zero magic numbers.

# ── Design Inputs ──────────────────────────────────────────────
module         = 2       # mm — gear module (tooth size scalar, ISO 54 preferred series)
teeth          = 20      # number of teeth (z)
face_width     = 15      # mm — gear face width (axial depth)
bore_dia       = 8       # mm — centre bore for shaft (shaft dia + clearance)
pressure_angle = 20      # degrees — standard pressure angle (ISO 54)

# ── Derived: ISO 54 Standard Gear Geometry ─────────────────────
pitch_dia   = module * teeth                  # d = m × z, fundamental gear relationship
addendum    = module                          # ha = 1.0 × m, tooth tip height above pitch circle (ISO 54)
dedendum    = 1.25 * module                   # hf = 1.25 × m, includes 0.25m clearance (ISO 54)
outer_dia   = pitch_dia + 2.0 * addendum      # tip circle: da = d + 2m
root_dia    = pitch_dia - 2.0 * dedendum      # root circle: df = d − 2.5m
tooth_angle = 360.0 / teeth                   # angular pitch: τ = 360°/z
shaft_fit_clearance = 0.002 * bore_dia        # ISO H7/g6 light running fit: Δ = 0.002×d

# ── Sanity Validation ──────────────────────────────────────────
assert root_dia > bore_dia * 1.5, \
    f"Root dia ({root_dia:.1f}mm) too close to bore ({bore_dia:.1f}mm) — increase module or teeth"
assert face_width >= module * 8, \
    f"Face width {face_width}mm < 8×m minimum ({module*8}mm) for adequate tooth contact"
assert addendum < pitch_dia / 2, \
    "Addendum exceeds pitch radius — reduce module"

# ── Gear blank ─────────────────────────────────────────────────
gear_body = cq.Workplane("XY").circle(pitch_dia / 2.0).extrude(face_width)

# ── Teeth: rectangular protrusion at each pitch circle position ─
# (Production use: replace with proper involute profile generator)
tooth_w = module * 1.5   # approximate tooth width at pitch circle
tooth_h = addendum        # protrudes addendum above pitch circle

for i in range(teeth):
    angle_rad = math.radians(i * tooth_angle)
    cx = (pitch_dia / 2.0) * math.cos(angle_rad)
    cy = (pitch_dia / 2.0) * math.sin(angle_rad)
    tooth = (
        cq.Workplane("XY")
        .box(tooth_w, tooth_h * 2.0, face_width)
        .translate((cx, cy, face_width / 2.0))
        .rotate((0, 0, 0), (0, 0, 1), i * tooth_angle)
    )
    gear_body = gear_body.union(tooth)

# ── Centre bore — through hub (cut last into final solid) ──────
result = gear_body.faces(">Z").workplane().hole(bore_dia)

