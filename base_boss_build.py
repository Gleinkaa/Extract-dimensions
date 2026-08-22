# Base + upright bracket with slot + boss (OIP-1099189824.jpg) — rebuilt per claude-opus-5 spec.
# Spec frame (3rd-angle isometric): X length 0..95, Y depth 0..40, Z height 0..70.
#   base 95x40x15; upright X[40,55] full-depth, Z15..70; U-slot (15 wide, R7.5 bottom) down the
#   upright; boss O30 axis (X15,Y20) Z15..30 with O10 through hole; 15x3 top-face notch under the
#   upright (X40..55, Z15->12); TWO R30 fillets on opposite upright faces (X=40 front, X=55 back).
# Fusion mapping: spec(x,y,z) -> Fusion(x, z, y)  (X right, Y UP, Z depth).
import adsk.core, adsk.fusion, math

def cm(mm):
    return mm * 0.1

des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent

# ---- cleanup (parametric: delete timeline features, newest-first) ----
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

def ext_offset(profile, op, start_mm, dist_mm):
    inp = extrudes.createInput(profile, op)
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(
        adsk.core.ValueInput.createByReal(cm(start_mm)))
    inp.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(cm(dist_mm))), Pos)
    return extrudes.add(inp)

def P(x, y, z=0.0):
    return adsk.core.Point3D.create(cm(x), cm(y), cm(z))

# ---- 1. Base: rect (0,0)->(95,15) in XY, extrude +Z 40 (95 long x 15 tall x 40 deep) ----
sk = root.sketches.add(root.xYConstructionPlane)
sk.name = "SK_Base"
sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0, 0), P(95, 15))
ext(sk.profiles.item(0), NewBody, cm(40)).name = "Base"

# ---- 2. Upright: rect (40,15)->(55,70) in XY, extrude +Z 40 (full depth), join ----
sk2 = root.sketches.add(root.xYConstructionPlane)
sk2.name = "SK_Upright"
sk2.sketchCurves.sketchLines.addTwoPointRectangle(P(40, 15), P(55, 70))
ext(sk2.profiles.item(0), Join, cm(40)).name = "Upright"

# ---- 3. U-slot: 15 wide (Fusion Z 12.5..27.5), from Y70 down to Y40, R7.5 semicircle bottom ----
# Robust construction: rectangular box cut (X 40..55, Z 12.5..27.5, Y 40..70) then two R7.5
# fillets on the bottom edges -> the fillets meet tangentially, forming the U bottom (lowest Y32.5).
sk3 = root.sketches.add(root.xZConstructionPlane)
sk3.name = "SK_Slot"
L3 = sk3.sketchCurves.sketchLines
# xZ plane: MUST convert model points to sketch space (raw 3D points break the profile).
def sz(x, z):
    p = sk3.modelToSketchSpace(adsk.core.Point3D.create(cm(x), 0, cm(z)))
    return adsk.core.Point3D.create(p.x, p.y, 0)
L3.addByTwoPoints(sz(40, 12.5), sz(55, 12.5))
L3.addByTwoPoints(sz(55, 12.5), sz(55, 27.5))
L3.addByTwoPoints(sz(55, 27.5), sz(40, 27.5))
L3.addByTwoPoints(sz(40, 27.5), sz(40, 12.5))
ext_offset(sk3.profiles.item(0), Cut, 40, 30).name = "SlotBox"

# ---- 3b. Fillet the two slot-bottom edges R7.5 (form the semicircular U bottom) ----
slot_edges = adsk.core.ObjectCollection.create()
body = root.bRepBodies.item(0)
for e in body.edges:
    try:
        p1 = e.startVertex.geometry
        p2 = e.endVertex.geometry
        y1, z1 = round(p1.y*10, 2), round(p1.z*10, 2)
        y2, z2 = round(p2.y*10, 2), round(p2.z*10, 2)
        # edge along X at Y=40, Z=12.5 or 27.5
        if abs(y1 - 40) < 0.01 and abs(y2 - 40) < 0.01 and \
           ((abs(z1 - 12.5) < 0.01 and abs(z2 - 12.5) < 0.01) or
            (abs(z1 - 27.5) < 0.01 and abs(z2 - 27.5) < 0.01)):
            slot_edges.add(e)
    except Exception:
        pass
if slot_edges.count == 2:
    ff = root.features.filletFeatures
    fi = ff.createInput()
    fi.addConstantRadiusEdgeSet(slot_edges, adsk.core.ValueInput.createByReal(cm(7.5)), True)
    ff.add(fi).name = "SlotBottomFillet"

# ---- 3c. Two R30 web fillets (front X=40 edge, back X=55 edge) in ONE input ----
# MUST be applied BEFORE the boss join: the boss cylinder (X 0..30) sits inside the fillet's
# roll zone (X 10..40) and the boss would otherwise make the fillet fail silently.
web_edges = adsk.core.ObjectCollection.create()
body = root.bRepBodies.item(0)
for e in body.edges:
    try:
        p1 = e.startVertex.geometry
        p2 = e.endVertex.geometry
        x1, y1 = round(p1.x*10, 2), round(p1.y*10, 2)
        x2, y2 = round(p2.x*10, 2), round(p2.y*10, 2)
        if abs(x1 - 40) < 0.01 and abs(x2 - 40) < 0.01 and abs(y1 - 15) < 0.01 and abs(y2 - 15) < 0.01:
            web_edges.add(e)
        if abs(x1 - 55) < 0.01 and abs(x2 - 55) < 0.01 and abs(y1 - 15) < 0.01 and abs(y2 - 15) < 0.01:
            web_edges.add(e)
    except Exception:
        pass
if web_edges.count == 2:
    ff = root.features.filletFeatures
    fi = ff.createInput()
    fi.addConstantRadiusEdgeSet(web_edges, adsk.core.ValueInput.createByReal(cm(30)), True)
    ff.add(fi).name = "WebFillets_R30"

# ---- 4. Boss O30: axis (X15, Y20 depth) along +Z height, Z15..30 ----
sk4 = root.sketches.add(root.xZConstructionPlane)
sk4.name = "SK_Boss"
sp = sk4.modelToSketchSpace(P(15, 0, 20))
sk4.sketchCurves.sketchCircles.addByCenterRadius(sp, cm(15))
ext_offset(sk4.profiles.item(0), Join, 15, 15).name = "Boss"

# ---- 5. Hole O10 through boss+base, axis (X15, Y20), Z0..30 ----
sk5 = root.sketches.add(root.xZConstructionPlane)
sk5.name = "SK_Hole"
sp5 = sk5.modelToSketchSpace(P(15, 0, 20))
sk5.sketchCurves.sketchCircles.addByCenterRadius(sp5, cm(5))
ext(sk5.profiles.item(0), Cut, cm(30)).name = "Hole"

# ---- 6. 15x3 notch: step cut down into base top face under upright (X40..55, Z15->12) ----
sk6 = root.sketches.add(root.xYConstructionPlane)
sk6.name = "SK_Notch"
sk6.sketchCurves.sketchLines.addTwoPointRectangle(P(40, 12), P(55, 15))
ext(sk6.profiles.item(0), Cut, cm(40)).name = "Notch"

# ---- census ----
bb = root.bRepBodies.item(0).boundingBox
result = {
    "n_bodies": root.bRepBodies.count,
    "n_web_fillet_edges": web_edges.count if "web_edges" in dir() else -1,
    "bbox_mm_min": [round(bb.minPoint.x*10, 1), round(bb.minPoint.y*10, 1), round(bb.minPoint.z*10, 1)],
    "bbox_mm_max": [round(bb.maxPoint.x*10, 1), round(bb.maxPoint.y*10, 1), round(bb.maxPoint.z*10, 1)],
    "volume_mm3": round(root.bRepBodies.item(0).volume*1000, 1),
}
