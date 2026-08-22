#!/usr/bin/env python3
import json, urllib.request, urllib.error
URL = "http://100.73.157.46:8765/mcp"
def post(payload, sid=None, tmo=25):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    try:
        resp = urllib.request.urlopen(req, timeout=tmo)
        return resp.status, (resp.headers.get("Mcp-Session-Id") or sid), resp.read().decode()
    except urllib.error.HTTPError as e:
        raw = ""
        try: raw = e.read().decode()
        except Exception: pass
        return e.code, sid, raw
    except Exception as e:
        return None, sid, "ERR:%r" % e

st, sid, raw = post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"dsh","version":"1.0"}}})
post({"jsonrpc":"2.0","method":"notifications/initialized"}, sid)
print("init OK sid=", sid, flush=True)

probes = [
    ("list_scripts", {}),
    ("get_active_selection", {}),
    ("fetch_design_guide", {}),
    ("capture_viewport", {"width": 640, "height": 480}),
]
for name, args in probes:
    print("PROBE", name, flush=True)
    st, sid, raw = post({"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":name,"arguments":args}}, sid, tmo=25)
    print("  -> status", st, "len", len(raw), flush=True)
    print("  -> head:", raw[:300].replace(chr(10), " "), flush=True)
print("ALL DONE", flush=True)
