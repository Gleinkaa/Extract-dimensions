# Verify skillup_bracket against the extracted spec: read bodies, bbox, volume,
# feature health. Compare with output/skillup_bracket.json expectations.
import adsk.core, adsk.fusion

des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent
tl = des.timeline

feats = []
for i in range(tl.count):
    f = tl.item(i)
    try:
        hs = f.healthState
    except Exception:
        hs = "?"
    feats.append({"i": i, "name": f.name, "health": hs})

bodies = []
for b in root.bRepBodies:
    bb = b.boundingBox
    bodies.append({
        "name": b.name,
        "bbox_mm_min": [round(bb.minPoint.x * 10, 2), round(bb.minPoint.y * 10, 2), round(bb.minPoint.z * 10, 2)],
        "bbox_mm_max": [round(bb.maxPoint.x * 10, 2), round(bb.maxPoint.y * 10, 2), round(bb.maxPoint.z * 10, 2)],
        "volume_mm3": round(b.volume * 1000, 1),
    })

result = {
    "doc": app.activeDocument.name,
    "units": des.unitsManager.defaultLengthUnits,
    "timeline_count": tl.count,
    "marker": tl.markerPosition,
    "n_bodies": root.bRepBodies.count,
    "n_sketches": root.sketches.count,
    "features": feats,
    "bodies": bodies,
}
