#!/usr/bin/env python3
import json, time, urllib.request, urllib.error
URL = "http://100.73.157.46:8765/mcp"
def post(p, sid=None, tmo=10):
    d = json.dumps(p).encode(); r = urllib.request.Request(URL, data=d, method="POST")
    r.add_header("Content-Type","application/json"); r.add_header("Accept","application/json, text/event-stream")
    if sid: r.add_header("Mcp-Session-Id", sid)
    try:
        x = urllib.request.urlopen(r, timeout=tmo); return x.status, (x.headers.get("Mcp-Session-Id") or sid), x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, sid, e.read().decode()[:200]
    except Exception as e:
        return None, sid, "ERR:%r" % e

def poll_once():
    st, sid, raw = post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"watch","version":"1"}}}, tmo=10)
    if st != 200:
        return "down(init %s)" % st
    post({"jsonrpc":"2.0","method":"notifications/initialized"}, sid)
    st, sid, raw = post({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_scripts","arguments":{}}}, sid, tmo=10)
    if st == 200:
        return "READY"
    if st is None:
        return "hung(timeout)"
    return "status %s" % st

print("watching Fusion MCP...", flush=True)
deadline = time.time() + 1800
while time.time() < deadline:
    s = poll_once()
    print("[%s] %s" % (time.strftime("%H:%M:%S"), s), flush=True)
    if s == "READY":
        print("FUSION_READY", flush=True)
        break
    time.sleep(20)
else:
    print("WATCH_TIMEOUT", flush=True)
