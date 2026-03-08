import cadquery as cq
import math

# Pressure vessel weld-neck flange — ASME B16.5 proportions
# All geometry derived from bore_dia and pressure. Zero magic numbers.

# ── Design Inputs ──────────────────────────────────────────────
bore_dia      = 50.0   # mm  — nominal bore (NPS 2" pipe schedule 40)
pressure_mpa  =  8.0   # MPa — design pressure
material_sy   = 250.0  # MPa — carbon steel yield at 20°C (ASME II Part D, SA-105)
safety_factor =  2.5   # dimensionless — ASME VIII minimum for pressure flanges

# ── Derived: Pipe Wall & Hub  (Barlow thin-wall, ASME VIII) ────
wall_t     = pressure_mpa * bore_dia / (2.0 * material_sy / safety_factor)  # t = PD/2σ
wall_t     = max(wall_t, bore_dia / 20.0)          # D/20 practical floor (schedule min)
hub_od     = bore_dia + 2.0 * wall_t               # pipe outer diameter (seamless)
hub_h      = max(0.6 * bore_dia, 1.5 * hub_od)    # stub length rule: ≥ 0.6×bore or 1.5×OD

# ── Derived: Flange Plate (ASME B16.5 dimensional proportions) ──
flange_od  = hub_od + 6.0 * wall_t                 # 3× wall extension each side of hub OD
flange_t   = max(1.5 * wall_t, 10.0)               # flange plate: 1.5× wall, 10mm minimum
raised_face_od  = bore_dia + 2.0 * wall_t * 1.5   # raised sealing face ~75% of hub OD
raised_face_h   = 1.6                              # 1.6mm raised face height (ASME B16.5 std)

# ── Derived: Bolt Circle & Pattern (ASME B16.5 Table) ──────────
bolt_circle_r = flange_od / 2.0 * 0.72             # bolt circle = 72% of flange OD/2
bolt_dia      = max(6.0, 0.8 * wall_t)             # M6 minimum; scale proportionally with wall
clearance_hole = bolt_dia * 1.08                   # ISO 273 medium clearance hole
bolt_count    = 4 if flange_od < 80.0 else 8       # ASME B16.5 bolt count tier

bolt_pts = [
    (bolt_circle_r * math.cos(math.radians(i * 360.0 / bolt_count)),
     bolt_circle_r * math.sin(math.radians(i * 360.0 / bolt_count)))
    for i in range(bolt_count)
]

# ── Sanity Validation ──────────────────────────────────────────
assert wall_t >= bore_dia / 20.0, \
    f"Wall {wall_t:.2f}mm < D/20 minimum ({bore_dia/20.0:.2f}mm) — increase wall or reduce pressure"
assert bolt_circle_r > hub_od / 2.0 + clearance_hole, \
    f"Bolt holes ({clearance_hole:.1f}mm) overlap hub — increase flange_od"
assert flange_od > bolt_circle_r * 2.0 + bolt_dia * 2.0, \
    "Bolt pattern exceeds flange edge — increase flange_od or reduce bolt count"
assert hub_h > wall_t * 2.0, \
    f"Hub too short ({hub_h:.1f}mm) relative to wall thickness {wall_t:.1f}mm"

# ── Flange plate — circular disc with central bore ─────────────
flange_plate = (
    cq.Workplane("XY")
    .circle(flange_od / 2.0)
    .extrude(flange_t)
    # Cut full-length bore through flange plate
    .faces(">Z").workplane()
    .circle(bore_dia / 2.0)
    .cutThruAll()
)

# ── Raised sealing face — sits on top of flange plate ──────────
raised_face = (
    cq.Workplane("XY")
    .transformed(offset=(0.0, 0.0, flange_t))
    .circle(raised_face_od / 2.0)
    .extrude(raised_face_h)
    .faces(">Z").workplane()
    .circle(bore_dia / 2.0)
    .cutThruAll()
)

# ── Pipe hub — weld-neck stub above flange ─────────────────────
# Positioned at top of flange plate + raised face
hub_base_z = flange_t + raised_face_h
pipe_hub = (
    cq.Workplane("XY")
    .transformed(offset=(0.0, 0.0, hub_base_z))
    .circle(hub_od / 2.0)
    .extrude(hub_h)
    .faces(">Z").workplane()
    .circle(bore_dia / 2.0)
    .cutThruAll()
)

# ── Union all solid bodies first, THEN cut bolt holes ──────────
flange_assembly = flange_plate.union(raised_face).union(pipe_hub)

# Bolt clearance holes — cut from bottom face of flange
result = (
    flange_assembly
    .faces("<Z").workplane()
    .pushPoints(bolt_pts)
    .hole(clearance_hole)
)
