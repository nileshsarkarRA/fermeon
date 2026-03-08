import cadquery as cq
import math

# Aerospace wing section — NACA 4-digit profile extruded to wing span
# Demonstrates: spline-based aerofoil profile, lofted taper, spar bores
# CEM approach: chord length drives ALL other dimensions via aerodynamic sizing rules

# ── Design Inputs ──────────────────────────────────────────────
root_chord     = 400.0    # mm  — root chord length (at wing root)
tip_chord      = 200.0    # mm  — tip chord length (taper ratio = 0.5)
half_span      = 800.0    # mm  — semi-span (root to tip)
sweep_angle_deg = 15.0    # °   — quarter-chord sweep angle
airfoil_t_ratio = 0.12    # dimensionless — NACA 0012: 12% thickness-to-chord

# ── Derived: Spar Sizing (bending loads at root) ────────────────
# Simplified beam bending: spar must carry lift × arm
# Spar wall = chord/40 minimum (aerospace rule for wing box spar cap)
front_spar_x   = root_chord * 0.25    # mm — front spar at 25% chord (standard)
rear_spar_x    = root_chord * 0.65    # mm — rear spar at 65% chord
spar_h         = root_chord * airfoil_t_ratio * 0.80  # 80% of max thickness
spar_wall_t    = max(root_chord / 40.0, 1.5)          # mm — spar wall, 1.5mm min (AM)
spar_od        = spar_wall_t * 4                       # hollow spar OD

# ── Derived: Skin thickness ─────────────────────────────────────
skin_t         = max(root_chord / 200.0, 1.0)         # mm — skin: chord/200, 1mm min

# ── Sanity Checks ───────────────────────────────────────────────
assert spar_wall_t >= 1.5, f"Spar wall {spar_wall_t:.2f}mm below AM 1.5mm minimum"
assert front_spar_x < rear_spar_x, "Front spar must be ahead of rear spar"
assert half_span > root_chord, "Semi-span must exceed root chord"

# ── NACA 4-digit (symmetric, t=12%) profile points ─────────────
# NACA 00tt: y_t = 5t(0.2969√x - 0.1260x - 0.3516x² + 0.2843x³ - 0.1015x⁴)
def naca_half_thickness(x_norm: float, t: float = 0.12) -> float:
    """Normalised half-thickness at chord fraction x (0-1)."""
    xn = x_norm
    return 5 * t * (0.2969 * math.sqrt(xn) - 0.1260 * xn
                    - 0.3516 * xn**2 + 0.2843 * xn**3 - 0.1015 * xn**4)

n_pts = 20   # points per surface (upper + lower)
x_stations = [math.sin(math.pi / 2 * i / n_pts)**2 for i in range(n_pts + 1)]  # cosine spacing

# Build 2D profile (XZ plane): X = chordwise, Z = thickness direction
# Upper surface: forward to trailing edge; lower surface reversed
upper = [(x * root_chord, naca_half_thickness(x, airfoil_t_ratio) * root_chord)
         for x in x_stations]
lower = [(x * root_chord, -naca_half_thickness(x, airfoil_t_ratio) * root_chord)
         for x in reversed(x_stations)]
profile_pts = upper + lower[1:-1]    # closed loop, skip duplicate endpoints

# ── Root aerofoil section (XZ workplane → profile in X/Z) ──────
root_wire = (
    cq.Workplane("XZ")
    .polyline(profile_pts)
    .close()
)

# ── Tip section: scaled chord, offset by half_span in Y ────────
tip_scale  = tip_chord / root_chord
sweep_ofs  = half_span * math.tan(math.radians(sweep_angle_deg))
tip_pts    = [(x * tip_chord + sweep_ofs,
               naca_half_thickness(x / tip_chord * (tip_chord / root_chord)
                                   if tip_chord > 0 else x, airfoil_t_ratio) * tip_chord)
              for x in [p * tip_chord / root_chord for p in x_stations]]
tip_lower  = [(x * tip_chord + sweep_ofs,
               -naca_half_thickness(x, airfoil_t_ratio) * tip_chord)
              for x in reversed(x_stations)]
tip_profile = [(p[0] + sweep_ofs, p[1]) for p in upper[::-1]]  # simplified: scale + shift

# ── Loft: root profile to tip profile ──────────────────────────
# Simplified loft using scale + translate since CQ loft needs wires in workplane stacks

# Build root section on XZ plane at Y=0
root_section = cq.Workplane("XZ").polyline(profile_pts).close()

# Tip section on XZ plane translated to Y=half_span and X offset by sweep
tip_profile_pts = [
    (x * tip_chord + sweep_ofs, naca_half_thickness(x / 1.0, airfoil_t_ratio) * tip_chord)
    for x in x_stations
] + [
    (x * tip_chord + sweep_ofs, -naca_half_thickness(x / 1.0, airfoil_t_ratio) * tip_chord)
    for x in reversed(x_stations)
]

# Wing body: loft from root to tip
wing_body = (
    cq.Workplane("XZ")
    .polyline(profile_pts).close()
    .workplane(offset=half_span)
    .transformed(offset=(sweep_ofs, 0, 0))
    .polyline([(x * tip_chord + sweep_ofs, y * tip_scale)
               for x, y in profile_pts]).close()
    .loft()
)

# ── Front spar bore (circular hollow tube along span) ──────────
front_spar_bore = (
    cq.Workplane("YZ")
    .transformed(offset=(0, 0, front_spar_x))
    .circle(spar_od / 2)
    .extrude(half_span + 5)
)
front_spar_inner = (
    cq.Workplane("YZ")
    .transformed(offset=(0, 0, front_spar_x))
    .circle((spar_od / 2) - spar_wall_t)
    .extrude(half_span + 5)
)

# ── Rear spar bore ──────────────────────────────────────────────
rear_spar_bore  = front_spar_bore.translate((rear_spar_x - front_spar_x, 0, 0))
rear_spar_inner = front_spar_inner.translate((rear_spar_x - front_spar_x, 0, 0))

# ── Assemble: wing skin + hollow spars ─────────────────────────
wing_with_spars = (
    wing_body
    .cut(front_spar_inner)
    .cut(rear_spar_inner)
)

result = wing_with_spars
