# Stepped bracket (OIP-479997622.jpg) — REBUILD per corrected spec (specs/spec_step_bracket.json, Reading B).
# Frame: spec X=width 0..115 (arm + web + boss + foot), Y=depth 0..50 (legs + slot), Z=height 0..80.
# Fusion mapping: (fx, fy, fz) = (specX, specZ, specY).  Fusion: X right, Y UP, Z depth.
#
# NOTE on the Fusion YZ-plane sketch: sketch X axis maps to model -Z (verified), so all YZ-plane
# profiles are drawn with su = -specY to land at model z = +specY.
#
# Structure (all mm):
#   Web plate X70..100, profile in spec Y-Z: front face Y0 Z15..60, R20 semicircular head centered
#     (Y25,Z60) crown Z80, taper (Y45,Z60)->(Y50,Z15), bottom edge Z15; SLOT NOTCH cut up from the
#     bottom edge: Y20..35 x Z15..40 (open at bottom, roof Z40) -> separates front leg (Y0..20) from
#     rear leg (Y35..50).
#   Boss O40 cylinder axis (Y25,Z60) along X, X100..105 (coincides with the R20 head cylinder).
#   Bore O30 along X through X70..105 at (Y25,Z60).
#   Arm X0..70 (incl. shoulder X45..70), Y0..20 (depth), underside Z30; LOW tier X0..15 top Z50,
#     RAISED tier X15..70 top Z58 (rise 8, riser at X15, full depth).
#   Rounded foot: tab Y35..50 x Z0..20 on the rear leg's lower part, X70..115, half-round R10 end
#     (arc center X105,Z10; tip X115).
import adsk.core, adsk.fusion, math

def cm(mm):
    return mm * 0.1

des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent

# ---- cleanup (parametric: timeline features newest-first) ----
try:
    tl = des.timeline
except Exception:
    tl = None
if tl is not None:
    tl.markerPosition = 0
    for i in range(tl.count - 1, -1, -1):
        try: tl.item(i).entity.deleteMe()
        except Exception: pass
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

def ext(profile, op, dist_cm):
    inp = extrudes.createInput(profile, op)
    inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(dist_cm))
    return extrudes.add(inp)

def add_line(sk, a, b):
    sk.sketchCurves.sketchLines.addByTwoPoints(
        adsk.core.Point3D.create(cm(a[0]), cm(a[1]), 0),
        adsk.core.Point3D.create(cm(b[0]), cm(b[1]), 0))

def add_arc(sk, center, r, start, sweep_deg):
    c = adsk.core.Point3D.create(cm(center[0]), cm(center[1]), 0)
    s = adsk.core.Point3D.create(cm(start[0]), cm(start[1]), 0)
    return sk.sketchCurves.sketchArcs.addByCenterStartSweep(c, s, math.radians(sweep_deg))

def rect(sk, x0, y0, x1, y1):
    add_line(sk, (x0, y0), (x1, y0)); add_line(sk, (x1, y0), (x1, y1))
    add_line(sk, (x1, y1), (x0, y1)); add_line(sk, (x0, y1), (x0, y0))

# ---- 1. Web + legs profile on the Fusion YZ plane (sketch su=-specY, sv=specZ), extrude +X 105 ----
sk = root.sketches.add(root.yZConstructionPlane)
sk.name = "SK_WebPlate"
add_line(sk, (0, 15), (0, 60))           # front face of the web (su=0 -> model z=0)
add_line(sk, (0, 60), (-5, 60))          # head top, left end
add_arc(sk, (-25, 60), 20, (-5, 60), 180)  # R20 semicircular head through (-25,80) -> model z25
add_line(sk, (-45, 60), (-50, 15))       # straight tapered right edge (the 45-dim edge)
add_line(sk, (-50, 15), (-35, 15))       # rear-leg bottom edge (to slot)
add_line(sk, (-35, 15), (-35, 40))       # slot right wall (model z35)
add_line(sk, (-35, 40), (-20, 40))       # slot roof
add_line(sk, (-20, 40), (-20, 15))       # slot left wall (model z20)
add_line(sk, (-20, 15), (0, 15))         # front-leg bottom edge (close)
ext(sk.profiles.item(0), NewBody, cm(105)).name = "WebPlate"

# ---- 2. Boss O40: circle (-25,60) r20 on YZ plane, join, +X 105 (merges with head cylinder) ----
skb = root.sketches.add(root.yZConstructionPlane)
skb.name = "SK_Boss"
skb.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(cm(-25), cm(60), 0), cm(20))
ext(skb.profiles.item(0), Join, cm(105)).name = "Boss"

# ---- 3. Remove X0..70 (web/boss live at X70..105): rect covering the profile, cut +X 70 ----
skc = root.sketches.add(root.yZConstructionPlane)
skc.name = "SK_TrimFront"
rect(skc, -50, 15, 0, 80)
ext(skc.profiles.item(0), Cut, cm(70)).name = "TrimX070"

# ---- 4. Bore O30 along X at (25,60) [sketch (-25,60)], cut +X 105 ----
skh = root.sketches.add(root.yZConstructionPlane)
skh.name = "SK_Bore"
skh.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(cm(-25), cm(60), 0), cm(15))
ext(skh.profiles.item(0), Cut, cm(105)).name = "Bore_O30"

# ---- 5. Arm X0..70 (incl shoulder), Y30..58 (spec Z), depth Z0..20 (spec Y) ----
ska = root.sketches.add(root.xYConstructionPlane)
ska.name = "SK_Arm"
ska.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(cm(0), cm(30), 0),
    adsk.core.Point3D.create(cm(70), cm(58), 0))
ext(ska.profiles.item(0), Join, cm(20)).name = "Arm"

# ---- 6. Tier step: cut X0..15 x Y50..58 -> low tier (top Z50) vs raised tier (top Z58) ----
skt = root.sketches.add(root.xYConstructionPlane)
skt.name = "SK_TierStep"
skt.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(cm(0), cm(50), 0),
    adsk.core.Point3D.create(cm(15), cm(58), 0))
ext(skt.profiles.item(0), Cut, cm(20)).name = "TierStep"

# ---- 7. Rounded foot: plane Z=35 (specY 35), profile X70..105 x Y0..20 + R10 half-round, +Z 15 ----
planes = root.constructionPlanes
pinp = planes.createInput()
pinp.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(cm(35)))
plane_foot = planes.add(pinp)
skf = root.sketches.add(plane_foot)
skf.name = "SK_Foot"
add_line(skf, (70, 0), (105, 0))
add_arc(skf, (105, 10), 10, (105, 0), 180)   # half-round end through (115,10)
add_line(skf, (105, 20), (70, 20))
add_line(skf, (70, 20), (70, 0))
ext(skf.profiles.item(0), Join, cm(15)).name = "RoundedFoot"

# ---- census (ALL bodies) ----
bodies = []
for b in root.bRepBodies:
    bb = b.boundingBox
    bodies.append({
        "vol_mm3": round(b.volume*1000, 1),
        "bbox": [[round(bb.minPoint.x*10,1), round(bb.minPoint.y*10,1), round(bb.minPoint.z*10,1)],
                 [round(bb.maxPoint.x*10,1), round(bb.maxPoint.y*10,1), round(bb.maxPoint.z*10,1)]]
    })
result = {"n_bodies": root.bRepBodies.count, "bodies": bodies}
