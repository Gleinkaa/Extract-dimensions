# Rocker arm / two-ended crank link (example5-2094245636.png)
# Runs in fusion360_mcp_bridge `run_python` context (adsk/app/ui/design/math/json pre-bound).
# Exact tangency geometry (no 3-decimal rounding) so the 8-arc profile closes.
import adsk.core, adsk.fusion, math

def cm(mm):
    return mm * 0.1

# ---- cleanup: drop prior features/sketches/bodies (parametric: timeline items) ----
des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent
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
    try:
        root.features.item(i).deleteMe()
    except Exception:
        pass
for s in list(root.sketches):
    try:
        s.deleteMe()
    except Exception:
        pass
for b in list(root.bRepBodies):
    try:
        b.deleteMe()
    except Exception:
        pass

# ---- exact geometry (mm) ----
Yb = math.sqrt(5796.0)          # boss centre Y = sqrt(90^2 - 48^2)
O  = (0.0, 0.0)
B  = (12.0, Yb)                 # top boss centre, R10
C2 = (60.0, 0.0)                # R100 flank centre (upper-left sweep), R100

def _intersect(P1, r1, P2, r2):
    dx, dy = P2[0]-P1[0], P2[1]-P1[1]
    d = math.hypot(dx, dy)
    a = (r1*r1 - r2*r2 + d*d) / (2*d)
    h = math.sqrt(max(r1*r1 - a*a, 0.0))
    xm = P1[0] + a*dx/d
    ym = P1[1] + a*dy/d
    return ((xm + h*dy/d, ym - h*dx/d), (xm - h*dy/d, ym + h*dx/d))

c1a, c1b = _intersect(O, 75.0, B, 45.0)   # R35 neck centre: |C1|=75, |C1-B|=45
C1 = c1a if c1a[0] > c1b[0] else c1b      # upper-right solution (larger X)

def tangency_ext(P1, r1, P2, r2):          # external: P1-circle toward P2
    d = math.hypot(P2[0]-P1[0], P2[1]-P1[1])
    return (P1[0] + r1*(P2[0]-P1[0])/d, P1[1] + r1*(P2[1]-P1[1])/d)

def tangency_int(P1, r1, P2, r2):          # internal: P1-circle away from P2
    d = math.hypot(P2[0]-P1[0], P2[1]-P1[1])
    return (P1[0] - r1*(P2[0]-P1[0])/d, P1[1] - r1*(P2[1]-P1[1])/d)

J0 = (40.0, 0.0)                                     # hub rightmost
J1 = tangency_ext(O, 40.0, C1, 35.0)                 # hub <-> R35 neck
J2 = tangency_ext(C1, 35.0, B, 10.0)                 # R35 neck <-> boss
J3 = tangency_int(B, 10.0, C2, 100.0)                # boss <-> R100
J4 = (-40.0, 0.0)                                    # hub leftmost
J5 = (-J1[0], -J1[1])
J6 = (-J2[0], -J2[1])
J7 = (-J3[0], -J3[1])

# ---- Sketch 1: 8-arc closed profile ----
sk = root.sketches.add(root.xYConstructionPlane)
sk.name = "SK_Rocker_Profile"
arcs = sk.sketchCurves.sketchArcs
# (center, radius, start, end) in mm, CCW traversal
loop = [
    (O, 40.0, J0, J1),
    (C1, 35.0, J1, J2),
    (B, 10.0, J2, J3),
    (C2, 100.0, J3, J4),
    (O, 40.0, J4, J5),
    ((-C1[0], -C1[1]), 35.0, J5, J6),
    ((-B[0], -B[1]), 10.0, J6, J7),
    ((-C2[0], -C2[1]), 100.0, J7, J0),
]
for (cx, cy), r, (sx, sy), (ex, ey) in loop:
    c = adsk.core.Point3D.create(cm(cx), cm(cy), 0)
    s = adsk.core.Point3D.create(cm(sx), cm(sy), 0)
    vx0, vy0 = sx - cx, sy - cy
    vx1, vy1 = ex - cx, ey - cy
    sweep = math.atan2(vx0*vy1 - vy0*vx1, vx0*vx1 + vy0*vy1)
    arcs.addByCenterStartSweep(c, s, sweep)

n_profiles = sk.profiles.count

# ---- Feature: web, symmetric 10 mm total ----
prof = sk.profiles.item(0)
extrudes = root.features.extrudeFeatures
inp = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
inp.setDistanceExtent(True, adsk.core.ValueInput.createByReal(cm(5)))   # 5 mm each side = 10 total
extrudes.add(inp).name = "Web"

# ---- Sketch 2: hub + two boss pads ----
sk2 = root.sketches.add(root.xYConstructionPlane)
sk2.name = "SK_Rocker_Pads"
sk2.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), cm(40))
sk2.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(cm(B[0]), cm(B[1]), 0), cm(10))
sk2.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(cm(-B[0]), cm(-B[1]), 0), cm(10))
profs2 = adsk.core.ObjectCollection.create()
for p in sk2.profiles:
    profs2.add(p)
inp2 = extrudes.createInput(profs2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
inp2.setDistanceExtent(True, adsk.core.ValueInput.createByReal(cm(10)))  # 10 mm each side = 20 total
extrudes.add(inp2).name = "HubAndBosses"

# ---- Sketch 3: bores (O40 + 2x O10), through ----
sk3 = root.sketches.add(root.xYConstructionPlane)
sk3.name = "SK_Rocker_Bores"
sk3.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), cm(20))
sk3.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(cm(B[0]), cm(B[1]), 0), cm(5))
sk3.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(cm(-B[0]), cm(-B[1]), 0), cm(5))
profs3 = adsk.core.ObjectCollection.create()
for p in sk3.profiles:
    profs3.add(p)
inp3 = extrudes.createInput(profs3, adsk.fusion.FeatureOperations.CutFeatureOperation)
inp3.setDistanceExtent(True, adsk.core.ValueInput.createByReal(cm(15)))  # 15 mm each side = through 20 mm
extrudes.add(inp3).name = "Bores"

# ---- census ----
bb = root.bRepBodies.item(0).boundingBox
result = {
    "Yb": round(Yb, 4),
    "C1": [round(C1[0], 4), round(C1[1], 4)],
    "n_profiles": n_profiles,
    "n_bodies": root.bRepBodies.count,
    "bbox_mm_min": [round(bb.minPoint.x*10, 2), round(bb.minPoint.y*10, 2), round(bb.minPoint.z*10, 2)],
    "bbox_mm_max": [round(bb.maxPoint.x*10, 2), round(bb.maxPoint.y*10, 2), round(bb.maxPoint.z*10, 2)],
    "volume_mm3": round(root.bRepBodies.item(0).volume*1000, 1),
}
