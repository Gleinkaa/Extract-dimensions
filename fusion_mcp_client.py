#!/usr/bin/env python3
"""Scratch Streamable-HTTP MCP client for autodesk-fusion-mcp (v1.3.0)."""
import json, sys, urllib.request, urllib.error

URL = "http://100.73.157.46:8765/mcp"
PROTO = "2025-03-26"

def _req(payload, sid=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    try:
        r = urllib.request.urlopen(req, timeout=180)
        raw = r.read().decode()
        nsid = r.headers.get("Mcp-Session-Id") or r.headers.get("mcp-session-id") or sid
        return r.status, nsid, raw
    except urllib.error.HTTPError as e:
        raw = ""
        try: raw = e.read().decode()
        except Exception: pass
        return e.code, (e.headers.get("Mcp-Session-Id") if e.headers else sid), raw
    except Exception as e:
        return None, sid, "CLIENT_ERR: %r" % e

def _parse(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw[0] in "{[":
        try: return json.loads(raw)
        except Exception: return raw
    vals = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            d = line[5:].strip()
            if d and d != "[DONE]":
                try: vals.append(json.loads(d))
                except Exception: vals.append(d)
    return vals if vals else raw

def init():
    st, sid, raw = _req({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":PROTO,"capabilities":{},"clientInfo":{"name":"dsh-agent","version":"1.0"}}})
    _req({"jsonrpc":"2.0","method":"notifications/initialized"}, sid)
    return sid

def main():
    sid = init()
    cmd = sys.argv[1]
    if cmd == "tools":
        st, sid, raw = _req({"jsonrpc":"2.0","id":2,"method":"tools/list"}, sid)
        r = _parse(raw)
        tools = r.get("result", {}).get("tools", []) if isinstance(r, dict) else []
        print("TOOL COUNT:", len(tools))
        for t in tools:
            print("=== " + t.get("name") + " ===")
            print((t.get("description") or "")[:400].replace("\n", " "))
            try:
                print("SCHEMA:", json.dumps(t.get("inputSchema", {}).get("properties", {}).keys().__iter__().__length_hint__() and list(t.get("inputSchema", {}).get("properties", {}).keys())))
            except Exception:
                pass
    elif cmd == "call":
        name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        st, sid, raw = _req({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":name,"arguments":args}}, sid)
        r = _parse(raw)
        print(json.dumps(r, indent=2)[:12000])
    else:
        print("unknown cmd")

if __name__ == "__main__":
    main()
