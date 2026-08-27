# Three-lobe bracket (OIP-652393864.jpg) — REBUILD per adjudicated spec (Reading B).
# Origin = O40 hub centre (0,0). OPEN 3-lobe outer profile (no disc!):
#   R85 arm arc (138..180 deg about C1) -> R30 valley -> R30 crest over the O40 hub ->
#   straight diagonal flank -> obround lobe (EXTERNAL boundary: near cap 60mm along -45deg,
#   far cap 30mm further, R8 caps) -> R25 fillet -> O50 boss arc (C2=(-10,-63.54)) ->
#   R32 fillet -> R15 arm-tip rounding -> close onto R85.
# O40 hub is a free-standing RING the boundary passes OVER (add raised pad); plate 10 mm.
# S1 curved slot: centerline R70 about C1, 138..180 deg, outer R78 / inner R62, R8 caps.
# Bores: O20 @ C1, O16 @ C2.
#
# R25 junction: the drawing is a G1 blend (flank + near cap + R25 all merge within ~0.3mm,
# unresolvable at 0.78mm/px). Use the EXACT R25 circle tangent to the near cap (|r-N|=33)
# and the boss (|r-C2|=50); its arc grazes the flank line within 0.012mm. To make the sketch
# form VALID closed profiles, split the flank at the R25-circle crossing: the sketch then has
# TWO loops - the main plate and the small near-cap tip - and we extrude both (joined).
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

def P(x, y):
    return adsk.core.Point3D.create(cm(x), cm(y), 0)

def add_arc(sk, center, r, start, end, sweep_deg):
    c = adsk.core.Point3D.create(cm(center[0]), cm(center[1]), 0)
    s = adsk.core.Point3D.create(cm(start[0]), cm(start[1]), 0)
    return sk.sketchCurves.sketchArcs.addByCenterStartSweep(c, s, math.radians(sweep_deg))

def add_line(sk, a, b):
    sk.sketchCurves.sketchLines.addByTwoPoints(P(a[0], a[1]), P(b[0], b[1]))

def tangency_ext(P1, r1, P2, r2):
    dx, dy = P2[0]-P1[0], P2[1]-P1[1]
    d = math.hypot(dx, dy)
    return (P1[0] + r1*dx/d, P1[1] + r1*dy/d)

# ================= exact geometry (mm) =================
C1 = (0.0, 0.0)
C2 = (-10.0, -63.54)          # boss centre (adjudicated -63.54 below C1)
u45 = (math.cos(math.radians(-45)), math.sin(math.radians(-45)))
N = (60*u45[0], 60*u45[1])    # obround near cap centre (pixel-verified)
F = (90*u45[0], 90*u45[1])    # obround far cap centre
T = (-70.0, 0.0)              # R15 arm-tip centre
V = (55*math.cos(math.radians(138)), 55*math.sin(math.radians(138)))  # R30 valley centre
crest = (9.244329402223048, 3.8134464599879276)  # R30 crest: |c-C1|=10, |c-V|=60
r32 = (-64.44656622320143, -46.67075501089214)   # R32: |r-T|=47, |r-C2|=57

# ---- junction points ----
J0 = (-85.0, 0.0)
P138 = (85*math.cos(math.radians(138)), 85*math.sin(math.radians(138)))
CV = tangency_ext(V, 30, crest, 30)
J1 = tangency_ext(T, 15, r32, 32)
J2 = tangency_ext(r32, 32, C2, 25)

# flank: external tangent between crest circle (R30) and far cap (R8), upper-right side
A, rA, B, rB = crest, 30.0, F, 8.0
d = (B[0]-A[0], B[1]-A[1])
Ld = math.hypot(*d)
k = (rA - rB)/Ld
h = math.sqrt(max(1 - k*k, 0.0))
dhat = (d[0]/Ld, d[1]/Ld)
perp = (-dhat[1], dhat[0])
best = None
for s in (1, -1):
    n = (k*dhat[0] + s*h*perp[0], k*dhat[1] + s*h*perp[1])
    tpA = (A[0]+rA*n[0], A[1]+rA*n[1])
    tpB = (B[0]+rB*n[0], B[1]+rB*n[1])
    if best is None or tpA[0]+tpA[1] > best[0]:
        best = (tpA[0]+tpA[1], tpA, tpB)
tp_crest, tp_far = best[1], best[2]

# obround near-side flank (toward boss): offset 8mm along n2 = (-0.7071,-0.7071)
n2 = (-0.7071067811865476, -0.7071067811865476)
N_ll = (N[0]+8*n2[0], N[1]+8*n2[1])   # flank tangent on near cap (225 deg), pixel-verified
F_ll = (F[0]+8*n2[0], F[1]+8*n2[1])

# R25 circle: tangent to near cap (|r-N|=33) AND tangent to boss (|r-C2|=50)
def circ_intersect(P1, r1, P2, r2):
    dx, dy = P2[0]-P1[0], P2[1]-P1[1]
    dd = math.hypot(dx, dy)
    a = (r1*r1 - r2*r2 + dd*dd)/(2*dd)
    h2 = r1*r1 - a*a
    if h2 < 0: return None
    hh = math.sqrt(h2)
    xm = P1[0] + a*dx/dd; ym = P1[1] + a*dy/dd
    return ((xm + hh*dy/dd, ym - hh*dx/dd), (xm - hh*dy/dd, ym + hh*dx/dd))

sols = circ_intersect(N, 33, C2, 50)
r25c = min(sols, key=lambda p: abs(p[0]-38.62) + abs(p[1]+75.21))
J4 = tangency_ext(N, 8, r25c, 25)     # near-cap tangency of the R25 circle (263.4 deg on cap)
J3 = tangency_ext(C2, 25, r25c, 25)   # boss tangency of the R25 circle

# ---- SPLIT the flank at the R25-circle crossing ----
flank_d = (N_ll[0]-F_ll[0], N_ll[1]-F_ll[1])
Lf = math.hypot(*flank_d)
ux, uy = flank_d[0]/Lf, flank_d[1]/Lf
dxf, dyf = F_ll[0]-r25c[0], F_ll[1]-r25c[1]
Bq = 2*(ux*dxf + uy*dyf)
Cq = dxf*dxf + dyf*dyf - 625
disc = Bq*Bq - 4*Cq
t_cross = 0.0
if disc >= 0:
    t1 = (-Bq - math.sqrt(disc))/2
    t2 = (-Bq + math.sqrt(disc))/2
    for t in (t1, t2):
        if 0.0 <= t <= Lf:   # t is in mm along the 30mm flank
            t_cross = t
X = (F_ll[0] + (t_cross/Lf)*flank_d[0], F_ll[1] + (t_cross/Lf)*flank_d[1])

# ---- outer profile: build the sketch so BOTH loops form, extrude both (joined) ----
def ang_of(P, c):
    return math.degrees(math.atan2(P[1]-c[1], P[0]-c[0]))

def sweep_ccw(a, b, c):
    d = (ang_of(b, c) - ang_of(a, c)) % 360
    if d > 180: d -= 360
    return d

sk = root.sketches.add(root.xYConstructionPlane)
sk.name = "SK_Outer3Lobe"
add_arc(sk, C1, 85,  J0,      P138,    sweep_ccw(J0, P138, C1))      # R85 arm
add_arc(sk, V,  30,  P138,    CV,      sweep_ccw(P138, CV, V))       # R30 valley
add_arc(sk, crest, 30, CV,    tp_crest, sweep_ccw(CV, tp_crest, crest))  # R30 crest
add_line(sk, tp_crest, tp_far)                    # straight diagonal flank
add_arc(sk, F,  8,   tp_far,  F_ll,    sweep_ccw(tp_far, F_ll, F))   # far cap (LONG CW)
add_line(sk, F_ll, X)                             # near-side flank part 1 (to R25 crossing)
add_line(sk, X, N_ll)                             # near-side flank part 2 (to near cap)
add_arc(sk, N,  8,   N_ll,    J4,      sweep_ccw(N_ll, J4, N))       # near cap arc
# R25 fillet split at X so both loops close: J4->X then X->J3 (CCW)
add_arc(sk, r25c, 25, J4,     X,       sweep_ccw(J4, X, r25c))
add_arc(sk, r25c, 25, X,      J3,      sweep_ccw(X, J3, r25c))
# boss arc: LONG CW (outward) = -(360 - ccw)
add_arc(sk, C2, 25,  J3,      J2,      sweep_ccw(J3, J2, C2) - 360)
add_arc(sk, r32, 32, J2,      J1,      sweep_ccw(J2, J1, r32))       # R32 concave fillet
add_arc(sk, T,  15,  J1,      J0,      sweep_ccw(J1, J0, T))         # R15 arm tip

# ---- collect ALL positive-area profiles and extrude them joined ----
n_profiles = sk.profiles.count
areas = []
profiles = adsk.core.ObjectCollection.create()
total_area = 0.0
for i in range(sk.profiles.count):
    try:
        a = sk.profiles.item(i).areaProperties().area
        areas.append(round(a*100, 1))
        if a > 1e-4:  # skip degenerate slivers
            profiles.add(sk.profiles.item(i))
            total_area += a*100
    except Exception:
        pass

# ---- Feature: plate 10 mm (join all profiles) ----
inp = extrudes.createInput(profiles, NewBody)
inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cm(10)))
extrudes.add(inp).name = "Plate3Lobe"

# ---- O40 hub: free-standing RING + raised pad (the boundary passes OVER it) ----
skh = root.sketches.add(root.xYConstructionPlane)
skh.name = "SK_HubPad"
skh.sketchCurves.sketchCircles.addByCenterRadius(P(0, 0), cm(20))
profh = None
for p in skh.profiles:
    profh = p
if profh is not None:
    # RAISED pad: extrude the O40 disc 0..13 (one-sided +normal, constructor-free API)
    # and JOIN it to the plate. The 0..10 portion is absorbed into the plate body, so
    # what remains visible is a 3 mm raised disc (10..13) on the plate top at the hub.
    # (v5.1 fix: previous symmetric +/-3 pad hung BELOW the plate and the O20 bore cut
    #  (0..10) left the pad's lower half solid, making the bore blind -> gate MINOR-DIFF.)
    inph = extrudes.createInput(profh, Join)
    inph.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cm(13)))
    extrudes.add(inph).name = "HubPad"

# ---- Bores O20 @ C1, O16 @ C2 ----
skb = root.sketches.add(root.xYConstructionPlane)
skb.name = "SK_Bores"
skb.sketchCurves.sketchCircles.addByCenterRadius(P(0, 0), cm(10))
skb.sketchCurves.sketchCircles.addByCenterRadius(P(C2[0], C2[1]), cm(8))
profsb = adsk.core.ObjectCollection.create()
for p in skb.profiles:
    profsb.add(p)
ext(profsb, Cut, cm(13)).name = "Bores"  # 0..13: through plate (0..10) AND raised pad (10..13)

# ---- S1 curved slot: centerline R70 about C1, 138..180 deg, outer R78 inner R62, R8 caps ----
sk1 = root.sketches.add(root.xYConstructionPlane)
sk1.name = "SK_SlotS1"
a1, a2 = math.radians(138), math.radians(180)
cap1 = (70*math.cos(a1), 70*math.sin(a1))
cap2 = (70*math.cos(a2), 70*math.sin(a2))
A1 = sk1.sketchCurves.sketchArcs
o1 = (78*math.cos(a1), 78*math.sin(a1))
o2 = (78*math.cos(a2), 78*math.sin(a2))
i2 = (62*math.cos(a2), 62*math.sin(a2))
i1 = (62*math.cos(a1), 62*math.sin(a1))
A1.addByCenterStartSweep(P(0, 0), P(o1[0], o1[1]), (a2 - a1))
A1.addByCenterStartSweep(P(cap2[0], cap2[1]), P(o2[0], o2[1]), math.pi)
A1.addByCenterStartSweep(P(0, 0), P(i2[0], i2[1]), -(a2 - a1))
A1.addByCenterStartSweep(P(cap1[0], cap1[1]), P(i1[0], i1[1]), math.pi)
slot_prof = None
slot_area = 1e9
for i in range(sk1.profiles.count):
    try:
        a = sk1.profiles.item(i).areaProperties().area
        if 0 < a < slot_area:
            slot_area = a
            slot_prof = sk1.profiles.item(i)
    except Exception:
        pass
if slot_prof is not None:
    ext(slot_prof, Cut, cm(10)).name = "SlotS1"

# ---- census ----
bb = root.bRepBodies.item(0).boundingBox
result = {
    "n_bodies": root.bRepBodies.count,
    "n_profiles_outer": n_profiles,
    "profile_areas_mm2": areas,
    "sum_profiles_mm2": round(total_area, 1),
    "r25_center_mm": [round(r25c[0], 2), round(r25c[1], 2)],
    "J4_mm": [round(J4[0], 2), round(J4[1], 2)],
    "J3_mm": [round(J3[0], 2), round(J3[1], 2)],
    "flank_split_t": round(t_cross, 4),
    "slot_area_mm2": round(slot_area*100, 1) if slot_prof is not None else None,
    "bbox_mm_min": [round(bb.minPoint.x*10, 1), round(bb.minPoint.y*10, 1), round(bb.minPoint.z*10, 1)],
    "bbox_mm_max": [round(bb.maxPoint.x*10, 1), round(bb.maxPoint.y*10, 1), round(bb.maxPoint.z*10, 1)],
    "volume_mm3": round(root.bRepBodies.item(0).volume*1000, 1),
}
