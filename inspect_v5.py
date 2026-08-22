import adsk.core, adsk.fusion, math
des = adsk.fusion.Design.cast(app.activeProduct)
root = des.rootComponent
out = {"bodies": []}
for b in root.bRepBodies:
    bb = b.boundingBox
    out["bodies"].append({
        "volume_mm3": round(b.volume*1000, 1),
        "bbox": [[round(bb.minPoint.x*10,1), round(bb.minPoint.y*10,1), round(bb.minPoint.z*10,1)],
                 [round(bb.maxPoint.x*10,1), round(bb.maxPoint.y*10,1), round(bb.maxPoint.z*10,1)]]
    })
out["n_bodies"] = root.bRepBodies.count
out["n_sketches"] = root.sketches.count
out["features"] = []
for f in root.features:
    try: out["features"].append(str(f.objectType).split("::")[-1])
    except Exception: pass
result = out
