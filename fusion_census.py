#!/usr/bin/env python3
import json, sys, urllib.request, urllib.error

URL = "http://100.73.157.46:8765/mcp"
PROTO = "2025-03-26"

def post(payload, sid=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    try:
        resp = urllib.request.urlopen(req, timeout=180)
        return resp.status, (resp.headers.get("Mcp-Session-Id") or sid), resp.read().decode()
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode()
        except Exception:
            pass
        return e.code, sid, raw
    except Exception as e:
        return None, sid, "ERR:%r" % e

def parse(raw):
    raw = (raw or "").strip()
    if raw and raw[0] in "{[":
        return json.loads(raw)
    out = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            d = line[5:].strip()
            if d and d != "[DONE]":
                try:
                    out.append(json.loads(d))
                except Exception:
                    out.append(d)
    return out if out else raw

st, sid, raw = post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":PROTO,"capabilities":{},"clientInfo":{"name":"dsh","version":"1.0"}}})
post({"jsonrpc":"2.0","method":"notifications/initialized"}, sid)

census_code = (
    "import adsk.core, adsk.fusion\n"
    "app = adsk.core.Application.get()\n"
    "des = adsk.fusion.Design.cast(app.activeProduct)\n"
    "if des is None:\n"
    "    result = {'error': 'no active design'}\n"
    "else:\n"
    "    doc = app.activeDocument\n"
    "    root = des.rootComponent\n"
    "    tl = des.timeline\n"
    "    feats = []\n"
    "    for i in range(tl.count):\n"
    "        f = tl.item(i)\n"
    "        try: hs = f.healthState\n"
    "        except Exception: hs = '?'\n"
    "        feats.append({'i': i, 'name': f.name, 'health': hs})\n"
    "    bodies = []\n"
    "    for b in root.bRepBodies:\n"
    "        bb = b.boundingBox\n"
    "        bodies.append({'name': b.name, 'min_mm': [round(bb.minPoint.x*10,2), round(bb.minPoint.y*10,2), round(bb.minPoint.z*10,2)], 'max_mm': [round(bb.maxPoint.x*10,2), round(bb.maxPoint.y*10,2), round(bb.maxPoint.z*10,2)], 'vol_mm3': round(b.volume*1000,1)})\n"
    "    result = {'doc': doc.name if doc else None, 'isSaved': doc.isSaved if doc else None, 'units': des.unitsManager.defaultLengthUnits, 'timeline_count': tl.count, 'marker': tl.markerPosition, 'n_bodies': root.bRepBodies.count, 'n_sketches': root.sketches.count, 'features': feats, 'bodies': bodies}\n"
)

st, sid, raw = post({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"execute_python","arguments":{"code":census_code,"description":"state census"}}}, sid)
print("HTTP", st, "session", sid)
print(raw)
