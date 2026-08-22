#!/usr/bin/env python3
import json, os, urllib.request, urllib.error

token = None
for line in open(os.path.expanduser('~/.config/bambubridge.env')):
    line = line.strip()
    if line.startswith('HA_TOKEN='):
        token = line.split('=', 1)[1].strip().strip('"').strip("'")
        break
if not token:
    print("NO HA_TOKEN FOUND"); raise SystemExit(1)

HA = "http://100.125.227.26:8123"

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(HA + path, data=data, method=method)
    r.add_header("Authorization", "Bearer " + token)
    r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r, timeout=20)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, "ERR:%r" % e

# 1. find wake / input_button entities
st, raw = req("GET", "/api/states")
if st == 200:
    states = json.loads(raw)
    wakes = [s["entity_id"] for s in states if "wake" in s["entity_id"].lower()]
    buttons = [s["entity_id"] for s in states if s["entity_id"].startswith("input_button")]
    print("wake entities:", wakes)
    print("input_button entities:", buttons)
else:
    print("states GET status", st, raw[:400])

# 2. trigger WoL
st2, raw2 = req("POST", "/api/services/input_button/press", {"entity_id": "input_button.wake_pc"})
print("press input_button.wake_pc -> status", st2)
print("resp:", raw2[:500])
