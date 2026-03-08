import cadquery as cq

# ── Parameters ────────────────────────────────────────────────
diameter = 50           # mm

# ── Solid Body (Sphere) ───────────────────────────────────────
# When creating a ball, orb, or sphere, do NOT extrude a circle or use cylinders.
# Use CadQuery's native .sphere() method.

result = (
    cq.Workplane("XY")
    .sphere(diameter / 2)
)
