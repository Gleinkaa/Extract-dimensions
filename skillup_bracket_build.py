# SkillUP CADD "stepped/L-shaped bracket" (images.jpg, isometric view) — Fusion build.
# Runs via fusion360_mcp_bridge `run_python` (adsk/app/ui/design/math/json pre-bound)
# or autodesk-fusion-mcp `execute_python`.
#
# Drawing dims (all mm, from 4x-upscaled vision read + region crops):
#   145 base length · 72 base depth · 12 base thickness · 80 LEFT block height
#   (48+40 steps, 24 upper step width) · Ø24 through-hole @ offset 30x/36y ·
#   R30 left-edge arc · R12 fillet near hole · R6 base corners · 25 right step · 6/12 details
#
# NOTE: source is an ISOMETRIC view — exact orthographic topology is ambiguous.
# This is the corrected interpretation (base plate + LEFT upright block with Ø24 bore);
# verify against the drawing after building and adjust the *_MM parameters.
import adsk.core, adsk.fusion, math

def cm(mm):
    return mm * 0.1

# ---- parameters (mm, isometric-best-effort interpretation, upscaled read) ----
BASE_L_MM   = 145.0    # base plate length (overall X)
BASE_T_MM   = 12.0     # base plate thickness (Y)
BASE_D_MM   = 72.0     # base plate depth (Z, extrude)
BLOCK_W_MM  = 145.0    # upright block width (X): whole block is 145 long
BLOCK_H_MM  = 80.0     # upright block height (Y, sits on base -> top at 12+80=92)
BLOCK_X_MM  = 0.0      # upright block LEFT face X offset (block on LEFT side)
HOLE_X_MM   = 30.0     # Ø24 hole center X offset from base left edge
HOLE_Y_MM   = 36.0     # Ø24 hole center Y offset ABOVE base top (i.e. Y=12+36=48)
HOLE_D_MM   = 24.0     # Ø24 through-hole in upright block
R30_MM      = 30.0     # R30 left-edge arc
R12_MM      = 12.0     # R12 fillet near hole
R6_MM       = 6.0      # R6 base corner fillets
SLOT_W_MM   = 6.0      # 6 mm slot width (if present)
SLOT_PITCH_MM = 12.0   # 12 mm step/pitch

des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent

# ---- cleanup (parametric: drop prior timeline features/sketches/bodies) ----
try:
    tl = des.timeline
except Exception:
    tl = None
if tl is not None:
    tl.markerPosition = 0
    for i in range(tl.count - 1, -1, -1):
        try:
            tl.item(i).entity.deleteMe()
        except Exception:
            pass
for i in range(root.features.count - 1, -1, -1):
    try: root.features.item(i).deleteMe()
    except Exception: pass
for s in list(root.sketches):
    try: s.deleteMe()
    except Exception: pass
for b in list(root.bRepBodies):
    try: b.deleteMe()
    except Exception: pass

extrudes = root.features.extrudeFeatures
NewBody = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
Join = adsk.fusion.FeatureOperations.JoinFeatureOperation
Cut = adsk.fusion.FeatureOperations.CutFeatureOperation
Pos = adsk.fusion.ExtentDirections.PositiveExtentDirection

def ext(profile, op, dist_cm):
    inp = extrudes.createInput(profile, op)
    inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(dist_cm))
    return extrudes.add(inp)

def P(x, y, z=0.0):
    return adsk.core.Point3D.create(cm(x), cm(y), cm(z))

# ---- 1. Base plate: rect (0,0)->(BASE_L, BASE_T) in XY, extrude +Z BASE_D ----
sk = root.sketches.add(root.xYConstructionPlane)
sk.name = "SK_Base"
sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0), P(BASE_L_MM, BASE_T_MM))
ext(sk.profiles.item(0), NewBody, cm(BASE_D_MM)).name = "BasePlate"

# ---- 2. Upright block: full-width 145 (BLOCK_X=0, BLOCK_W=145), join ----
sk2 = root.sketches.add(root.xYConstructionPlane)
sk2.name = "SK_Block"
sk2.sketchCurves.sketchLines.addTwoPointRectangle(
    P(BLOCK_X_MM, BASE_T_MM), P(BLOCK_X_MM + BLOCK_W_MM, BASE_T_MM + BLOCK_H_MM))
ext(sk2.profiles.item(0), Join, cm(BASE_D_MM)).name = "UprightBlock"

# ---- 3. Ø24 through-hole in upright block (full depth) ----
sk3 = root.sketches.add(root.xYConstructionPlane)
sk3.name = "SK_Hole"
hc = sk3.modelToSketchSpace(P(HOLE_X_MM, BASE_T_MM + HOLE_Y_MM))
sk3.sketchCurves.sketchCircles.addByCenterRadius(hc, cm(HOLE_D_MM / 2))
ext(sk3.profiles.item(0), Cut, cm(BASE_D_MM + 1)).name = "Hole_O24"

# ---- 4. R30 left-edge arc (fillet on the vertical left edge of the block, at base top) ----
body = root.bRepBodies.item(0)
root_edges = adsk.core.ObjectCollection.create()
for e in body.edges:
    try:
        p1 = e.startVertex.geometry
        p2 = e.endVertex.geometry
        x1, y1 = round(p1.x * 10, 2), round(p1.y * 10, 2)
        x2, y2 = round(p2.x * 10, 2), round(p2.y * 10, 2)
        # vertical edge (same X) sitting at base top Y=BASE_T, at the block left/right faces
        if abs(x1 - x2) < 0.01 and abs(y1 - BASE_T_MM) < 0.01 and abs(y2 - BASE_T_MM) < 0.01 \
           and (abs(x1 - BLOCK_X_MM) < 0.01 or abs(x1 - (BLOCK_X_MM + BLOCK_W_MM)) < 0.01):
            root_edges.add(e)
    except Exception:
        pass
if root_edges.count > 0:
    ff = root.features.filletFeatures
    fi = ff.createInput()
    fi.addConstantRadiusEdgeSet(root_edges, adsk.core.ValueInput.createByReal(cm(R30_MM)), True)
    ff.add(fi).name = "RootFillet_R30"

# ---- 4b. R6 base corner fillets (front/back bottom corners of the base plate) ----
corner_edges = adsk.core.ObjectCollection.create()
for e in body.edges:
    try:
        p1 = e.startVertex.geometry
        p2 = e.endVertex.geometry
        x1, y1 = round(p1.x * 10, 2), round(p1.y * 10, 2)
        x2, y2 = round(p2.x * 10, 2), round(p2.y * 10, 2)
        # horizontal edge at base bottom Y=0, at X=0 or X=BASE_L
        if abs(y1 - 0.0) < 0.01 and abs(y2 - 0.0) < 0.01 and \
           (abs(x1 - 0.0) < 0.01 or abs(x1 - BASE_L_MM) < 0.01):
            corner_edges.add(e)
    except Exception:
        pass
if corner_edges.count > 0:
    ff = root.features.filletFeatures
    fi = ff.createInput()
    fi.addConstantRadiusEdgeSet(corner_edges, adsk.core.ValueInput.createByReal(cm(R6_MM)), True)
    ff.add(fi).name = "BaseCorners_R6"

# ---- 5. R12 fillet on top edges of block ----
top_edges = adsk.core.ObjectCollection.create()
for e in body.edges:
    try:
        p1 = e.startVertex.geometry
        p2 = e.endVertex.geometry
        y1, y2 = round(p1.y * 10, 2), round(p2.y * 10, 2)
        ytop = BASE_T_MM + BLOCK_H_MM
        if abs(y1 - ytop) < 0.01 and abs(y2 - ytop) < 0.01:
            top_edges.add(e)
    except Exception:
        pass
if top_edges.count > 0:
    ff = root.features.filletFeatures
    fi = ff.createInput()
    fi.addConstantRadiusEdgeSet(top_edges, adsk.core.ValueInput.createByReal(cm(R12_MM)), True)
    ff.add(fi).name = "TopFillet_R12"

# ---- census ----
bb = root.bRepBodies.item(0).boundingBox
result = {
    "n_bodies": root.bRepBodies.count,
    "bbox_mm_min": [round(bb.minPoint.x * 10, 1), round(bb.minPoint.y * 10, 1), round(bb.minPoint.z * 10, 1)],
    "bbox_mm_max": [round(bb.maxPoint.x * 10, 1), round(bb.maxPoint.y * 10, 1), round(bb.maxPoint.z * 10, 1)],
    "volume_mm3": round(root.bRepBodies.item(0).volume * 1000, 1),
    "params_mm": {
        "base_l": BASE_L_MM, "base_t": BASE_T_MM, "base_d": BASE_D_MM,
        "block_w": BLOCK_W_MM, "block_h": BLOCK_H_MM, "block_x": BLOCK_X_MM,
        "hole_x": HOLE_X_MM, "hole_y": HOLE_Y_MM, "hole_d": HOLE_D_MM,
        "r30": R30_MM, "r12": R12_MM, "r6": R6_MM,
    },
}
