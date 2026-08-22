#!/usr/bin/env python3
"""Client for the desktop's `fusion360_mcp_bridge` add-in.

The add-in exposes a JSON HTTP API on 127.0.0.1:7634 (loopback on the Windows
desktop). Reach it through an SSH tunnel::

    ssh -N -L 7634:127.0.0.1:7634 Großeel@100.125.213.97

Endpoints:
  GET  /status            -> {"status":"ok","port":7634}
  POST /command           -> {"command":"...","params":{...}} -> result JSON

Commands include ``run_python`` (arbitrary Python on Fusion's main thread, with
``adsk``/``app``/``ui``/``design``/``math``/``json`` pre-bound; set ``result``
to a JSON-serialisable value to return it), plus ``create_sketch``,
``extrude_sketch``, ``get_bodies``, ``get_sketches``, ``get_active_design``,
``export_design`` etc.

Usage:
  python3 desktop_fusion_client.py status
  python3 desktop_fusion_client.py py 'print(app.version)'
  python3 desktop_fusion_client.py run rocker_arm_build.py
  python3 desktop_fusion_client.py bodies
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:7634"


def _req(method, path, payload=None, timeout=180):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode()[:500]
        except Exception:
            err = ""
        return {"success": False, "http_error": e.code, "error": err}
    except Exception as e:
        return {"success": False, "error": repr(e)}


def status():
    return _req("GET", "/status")


def command(name, params=None):
    return _req("POST", "/command", {"command": name, "params": params or {}})


def run_python(code):
    return command("run_python", {"code": code})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(status(), indent=2))
    elif cmd == "py":
        print(json.dumps(run_python(sys.argv[2]), indent=2)[:8000])
    elif cmd == "run":
        with open(sys.argv[2], encoding="utf-8") as f:
            code = f.read()
        print(json.dumps(run_python(code), indent=2)[:12000])
    elif cmd == "bodies":
        print(json.dumps(command("get_bodies"), indent=2)[:8000])
    elif cmd == "design":
        print(json.dumps(command("get_active_design"), indent=2)[:8000])
    else:
        print("usage: status | py '<code>' | run <file.py> | bodies | design")
