import cadquery as cq

# ── Parameters ────────────────────────────────────────────────
height = 120           # mm — total height
base_radius = 25       # mm
top_radius = 35        # mm
wall_thickness = 2.5   # mm
base_thickness = 5.0   # mm

# ── Solid Body (Loft) ─────────────────────────────────────────
# Rather than stacking blocky cylinders, vessels are best generated
# using a loft from the base profile to the top profile.
solid_body = (
    cq.Workplane("XY")
    .circle(base_radius)
    .workplane(offset=height)
    .circle(top_radius)
    .loft(ruled=True)
)

# ── Shelling (Hollowing) ──────────────────────────────────────
# To turn the solid loft into a cup/glass, we shell the top face.
# Select the top face (the face normal to the Z direction) and apply a negative thickness.
result_shell = solid_body.faces(">Z").shell(-wall_thickness)

# ── Extra: Thicker Base ───────────────────────────────────────
# If the cup needs a thicker solid glass base (e.g. for a whisky glass),
# we can union a cylinder at the bottom inside the shell. We won't do that here
# but simply add comfortable fillets.

# ── Fillets / Comfort Edges ───────────────────────────────────
# We gracefully fillet the outer base edge and the top rim lip.
# The rim lip is small, so the fillet must be smaller than half the wall thickness!
max_rim_fillet = wall_thickness / 2.0 * 0.9  # Safety margin for fillet
base_fillet = 3.0

result = (
    result_shell
    .edges("<Z").fillet(base_fillet)          # Smooth the exact bottom outer edge
    .edges(">Z").edges().fillet(max_rim_fillet) # Smooth both the inner and outer rim lip
)
