import cadquery as cq

# Multi-level mounting bracket — main body, top/bottom plates, 4 corner columns, bolt holes
# Demonstrates: correct Z stacking, pushPoints for columns, holes cut into final solid

# ── Parameters ─────────────────────────────────────────────────
body_l, body_w, body_t    = 200, 80, 10     # main body: length, width, thickness
plate_l, plate_w, plate_t = 180, 70, 6      # top & bottom plates
col_dia, col_h            = 16, 60          # corner support columns
hole_dia                  = 8              # mounting hole diameter
col_inset                 = 14             # column centre inset from plate edge

# ── Z positions (all centred in Z by default, use centered=(T,T,F) to floor-base) ──
# main body:  Z = -body_t/2 .. +body_t/2  (centred at 0)
# top plate:  bottom = body_t/2  → translate Z = body_t/2 + plate_t/2
# bottom plate: top = -body_t/2  → translate Z = -body_t/2 - plate_t/2
# columns:    bottom = body_t/2  → translate Z = body_t/2, extrude up by col_h

top_plate_z    = body_t / 2 + plate_t / 2
bottom_plate_z = -(body_t / 2 + plate_t / 2)
col_base_z     = body_t / 2   # columns sit on top face of main body

# ── Main body ───────────────────────────────────────────────────
main_body = cq.Workplane("XY").box(body_l, body_w, body_t)

# ── Top plate (rests on top of main body) ──────────────────────
top_plate = (
    cq.Workplane("XY")
    .box(plate_l, plate_w, plate_t)
    .translate((0, 0, top_plate_z))
)

# ── Bottom plate (hangs below main body) ───────────────────────
bottom_plate = (
    cq.Workplane("XY")
    .box(plate_l, plate_w, plate_t)
    .translate((0, 0, bottom_plate_z))
)

# ── 4 corner columns (pushPoints — NOT rarray) ─────────────────
# Columns stand on the top face of the main body, reaching upward
cx = plate_l / 2 - col_inset
cy = plate_w / 2 - col_inset
col_pts = [(cx, cy), (-cx, cy), (cx, -cy), (-cx, -cy)]
columns = (
    cq.Workplane("XY")
    .transformed(offset=(0, 0, col_base_z))   # start at top of main body
    .pushPoints(col_pts)
    .circle(col_dia / 2)
    .extrude(col_h)
)

# ── Assemble ALL solids first, THEN cut holes ──────────────────
result = main_body.union(top_plate).union(bottom_plate).union(columns)

# ── Mounting holes on top plate — cut into final solid ─────────
hx = plate_l / 2 - col_inset
hy = plate_w / 2 - col_inset
hole_pts = [(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]
result = (
    result
    .faces(">Z")
    .workplane()
    .pushPoints(hole_pts)
    .hole(hole_dia)
)

# ── Mounting holes on bottom plate — cut from bottom face ──────
result = (
    result
    .faces("<Z")
    .workplane()
    .pushPoints(hole_pts)
    .hole(hole_dia)
)
