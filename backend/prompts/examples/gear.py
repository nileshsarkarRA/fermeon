import cadquery as cq
import math

# Spur gear — involute profile approximated with CadQuery
# For accurate involute gears, use cadquery-contrib or FreeCAD Part Design

# ── Parameters ────────────────────────────────────────────────
module         = 2       # gear module (tooth size)
teeth          = 20      # number of teeth
face_width     = 15      # mm — gear face width (depth)
bore_dia       = 8       # mm — center bore diameter
pressure_angle = 20      # degrees

# ── Derived geometry ──────────────────────────────────────────
pitch_dia      = module * teeth              # mm
addendum       = module                      # tooth tip height above pitch circle
dedendum       = 1.25 * module               # tooth root depth below pitch circle
outer_dia      = pitch_dia + 2 * addendum
root_dia       = pitch_dia - 2 * dedendum
tooth_angle    = 360 / teeth                 # degrees per tooth

# ── Simplified gear: circle with rectangular teeth ────────────
# (For production use a proper involute profile generator)
gear_body = cq.Workplane("XY").circle(pitch_dia / 2).extrude(face_width)

# Add teeth as rectangular protrusions
for i in range(teeth):
    angle_rad = math.radians(i * tooth_angle)
    cx = (pitch_dia / 2) * math.cos(angle_rad)
    cy = (pitch_dia / 2) * math.sin(angle_rad)
    tooth = (
        cq.Workplane("XY")
        .box(module * 1.5, module * 0.9, face_width)
        .translate((cx, cy, face_width / 2))
        .rotate((0, 0, 0), (0, 0, 1), i * tooth_angle)
    )
    gear_body = gear_body.union(tooth)

# ── Center bore ───────────────────────────────────────────────
gear_body = (
    gear_body
    .faces(">Z")
    .workplane()
    .hole(bore_dia)
)

result = gear_body
