import cadquery as cq
import math

# Shell & tube heat exchanger — front header, tube bundle, rear header
# CEM approach: heat duty Q (Watts) drives tube count, tube length, and all geometry.
# Noyron pattern: Q = U·A·LMTD → back-calculate A_min → tube count → geometry.

# ── Design Inputs ───────────────────────────────────────────────
Q_duty_W      = 5000.0   # W   — heat duty to transfer
LMTD          = 40.0     # °C  — log mean temperature difference (hot-to-cold)
U_overall     = 800.0    # W/m²·K — overall heat transfer coefficient (liquid-liquid)
n_passes      = 1        # dimensionless — number of tube-side passes

# Tube geometry (standard 3/4" OD tube per TEMA/ISO)
tube_od        = 19.05   # mm  — standard 3/4" OD
tube_wall_t    = 1.65    # mm  — min wall, ASTM A213 drawn tube
tube_od_m      = tube_od / 1000.0
tube_id        = tube_od - 2.0 * tube_wall_t
tube_id_m      = tube_id / 1000.0

# Shell
shell_od       = 150.0   # mm  — shell OD (start estimate, adjusted after tube count)
shell_wall_t   = max(shell_od / 20.0, 4.0)   # mm  — ASME VIII D/20 rule
tube_pitch     = tube_od * 1.25              # mm  — triangular pitch: 1.25× OD (TEMA std)

# ── Derived: Heat Transfer Area & Tube Count ────────────────────
A_min          = Q_duty_W / (U_overall * LMTD)           # m² — minimum transfer area
tube_L_mm      = max(300.0, shell_od * 5)                # mm — tube length heuristic L≥5D
tube_L_m       = tube_L_mm / 1000.0
A_per_tube     = math.pi * tube_od_m * tube_L_m          # m² — one tube external area
tube_count     = max(4, math.ceil(A_min / A_per_tube))   # tubes needed

# Round tube_count to nearest triangular pitch bundle
# Rough tubesheet: pack tubes in rows; row count ≈ sqrt(tube_count)
n_rows         = max(2, math.ceil(math.sqrt(tube_count)))
tubes_per_row  = math.ceil(tube_count / n_rows)
tube_count     = n_rows * tubes_per_row   # adjusted

# Adjusted shell ID ≥ bundle + 2×clearance
bundle_w       = tubes_per_row * tube_pitch + tube_od  # width of bundle
bundle_h       = n_rows * tube_pitch * math.sin(math.radians(60)) + tube_od
shell_id_req   = max(bundle_w, bundle_h) + 20.0        # 10mm clearance each side
shell_id       = shell_id_req
shell_od       = shell_id + 2.0 * shell_wall_t

# Header / tube sheet
tubesheet_t    = max(tube_od * 1.5, 15.0)               # mm  — tube sheet, 1.5×OD min
header_h       = max(tube_od * 2.5, 50.0)               # mm  — header box height
nozzle_od      = tube_id * math.sqrt(tube_count / n_passes) * 1.15  # mm — nozzle sizing
nozzle_od      = max(nozzle_od, 20.0)
nozzle_wall    = max(nozzle_od / 20.0, 2.5)

# ── Sanity Checks ───────────────────────────────────────────────
assert tube_id > 0, f"Tube ID {tube_id:.2f}mm must be positive"
assert shell_id > bundle_w, f"Shell {shell_id:.0f}mm too narrow for bundle {bundle_w:.0f}mm"
assert tube_L_mm / tube_od >= 8, "Tube L/D < 8 — heat transfer too short; increase length"
assert tubesheet_t >= tube_od, f"Tubesheet {tubesheet_t:.1f}mm thinner than tube OD {tube_od}mm"

# ── Z layout ────────────────────────────────────────────────────
z_front_header_bot = 0
z_tubesheet_front  = header_h
z_tube_start       = z_tubesheet_front + tubesheet_t
z_tube_end         = z_tube_start + tube_L_mm
z_tubesheet_rear   = z_tube_end
z_rear_header_top  = z_tubesheet_rear + tubesheet_t + header_h

# ── Shell cylinder ──────────────────────────────────────────────
shell = (
    cq.Workplane("XY")
    .circle(shell_od / 2.0)
    .extrude(tube_L_mm + 2.0 * tubesheet_t, both=False)
    .translate((0, 0, z_tube_start - tubesheet_t))
)
shell_bore = (
    cq.Workplane("XY")
    .circle(shell_id / 2.0)
    .extrude(tube_L_mm + 2.0 * tubesheet_t, both=False)
    .translate((0, 0, z_tube_start - tubesheet_t))
)
shell_body = shell.cut(shell_bore)

# ── Front tubesheet ─────────────────────────────────────────────
front_ts = (
    cq.Workplane("XY")
    .circle(shell_od / 2.0)
    .extrude(tubesheet_t)
    .translate((0, 0, z_tubesheet_front))
)

# ── Rear tubesheet ──────────────────────────────────────────────
rear_ts = front_ts.translate((0, 0, tube_L_mm + tubesheet_t))

# ── Tube bundle — triangular pitch grid ─────────────────────────
# Place tubes at triangular pitch — rows offset by half-pitch
tube_pts = []
row_spacing = tube_pitch * math.sin(math.radians(60))
x_start = -(tubes_per_row - 1) * tube_pitch / 2.0
y_start = -(n_rows - 1) * row_spacing / 2.0
for row in range(n_rows):
    offset = (tube_pitch / 2.0) if (row % 2 == 1) else 0.0
    for col in range(tubes_per_row):
        tx = x_start + col * tube_pitch + offset
        ty = y_start + row * row_spacing
        # Only add if inside shell_id circle
        if math.sqrt(tx**2 + ty**2) < shell_id / 2.0 - tube_od:
            tube_pts.append((tx, ty))

tube_bundle = (
    cq.Workplane("XY")
    .pushPoints(tube_pts)
    .circle(tube_od / 2.0)
    .extrude(tube_L_mm + 2.0 * tubesheet_t)
    .translate((0, 0, z_tubesheet_front))
)
tube_bores = (
    cq.Workplane("XY")
    .pushPoints(tube_pts)
    .circle(tube_id / 2.0)
    .extrude(tube_L_mm + 2.0 * tubesheet_t)
    .translate((0, 0, z_tubesheet_front))
)
hollow_tubes = tube_bundle.cut(tube_bores)

# ── Front header box ────────────────────────────────────────────
header_box_w = shell_od + 20.0
front_header = (
    cq.Workplane("XY")
    .rect(header_box_w, header_box_w)
    .extrude(header_h)
    .translate((0, 0, z_front_header_bot))
)
front_header_bore = (
    cq.Workplane("XY")
    .rect(header_box_w - 2.0 * tubesheet_t, header_box_w - 2.0 * tubesheet_t)
    .extrude(header_h - tubesheet_t)
    .translate((0, 0, tubesheet_t))
)
front_header = front_header.cut(front_header_bore)

# ── Rear header (mirror of front) ───────────────────────────────
rear_header = front_header.translate((0, 0, z_tubesheet_rear + tubesheet_t))

# ── Shell-side inlet/outlet nozzles ─────────────────────────────
nozzle_l = shell_od / 2.0 + 30.0  # protrudes 30mm outside shell
inlet_nozzle = (
    cq.Workplane("YZ")
    .circle(nozzle_od / 2.0 + nozzle_wall)
    .extrude(nozzle_l)
    .translate((0, 0, z_tube_start + tube_L_mm * 0.75))
)
inlet_nozzle_bore = (
    cq.Workplane("YZ")
    .circle(nozzle_od / 2.0)
    .extrude(nozzle_l)
    .translate((0, 0, z_tube_start + tube_L_mm * 0.75))
)
inlet_nozzle = inlet_nozzle.cut(inlet_nozzle_bore)

outlet_nozzle = (
    cq.Workplane("YZ")
    .circle(nozzle_od / 2.0 + nozzle_wall)
    .extrude(-nozzle_l)
    .translate((0, 0, z_tube_start + tube_L_mm * 0.25))
)
outlet_nozzle_bore = (
    cq.Workplane("YZ")
    .circle(nozzle_od / 2.0)
    .extrude(-nozzle_l)
    .translate((0, 0, z_tube_start + tube_L_mm * 0.25))
)
outlet_nozzle = outlet_nozzle.cut(outlet_nozzle_bore)

# ── Assemble ─────────────────────────────────────────────────────
result = (
    shell_body
    .union(front_ts)
    .union(rear_ts)
    .union(hollow_tubes)
    .union(front_header)
    .union(rear_header)
    .union(inlet_nozzle)
    .union(outlet_nozzle)
)
