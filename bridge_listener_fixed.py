"""
Corrected listener section for the `fusion360_mcp_bridge` add-in (port 7634).

Drop the functions below into the add-in, replacing the current
`_tailscale_ip` / `_serve_on` / `_start_tailnet_listener` / `run` / `stop`.
Keep your existing module-level `BridgeHTTPHandler`, `BRIDGE_PORT`,
`_TAILNET_RETRY_ATTEMPTS`, `_TAILNET_RETRY_DELAY`, `_handlers`, `handler`,
`CUSTOM_EVENT_ID`, and the imports (`socket`, `threading`, `time`, `traceback`,
`HTTPServer`).

Also ADD near your other module globals (they must exist before run()/stop()):

    _http_server = None
    _http_thread = None
    _tailnet_server = None
    _tailnet_thread = None
    _stopping = False

And ADD `import os` and `import subprocess` at the top of the file.

What was fixed (see the git note in the repo handoffs):
  1. run() started the loopback server TWICE (a manual HTTPServer block, then
     `_serve_on("127.0.0.1")`), orphaning the first listener and overwriting
     the globals. Only `_serve_on` remains.
  2. run() had an orphaned `_ui.messageBox(...)` at wrong indentation — a
     leftover that is both an IndentationError and, if kept under an except, a
     modal fired from run() (which blocks Fusion's startup). Failures now go to
     bridge.log, non-modally.
  3. stop() only called shutdown(); the listening socket stayed bound until
     server_close(). Both servers are now fully released.
  4. stop() ended in a dangling `except Exception:` with no body.
  5. Duplicate `global` lines in run() and stop() collapsed.
  6. _tailscale_ip() relied on getaddrinfo(hostname), which on Windows often
     resolves only to the LAN NIC and misses the 100.x Tailscale address.
     `tailscale ip -4` is tried first, getaddrinfo scan as fallback.
  7. Everything was silent; a tiny `_log()` (bridge.log next to the add-in)
     records binds, failures, and stops without any UI.
"""

import os
import socket
import subprocess
import threading
import time
import traceback
from http.server import HTTPServer


# ── Logging (non-modal: never pop a dialog from run()) ──────────────────────

def _log(msg):
    """Append a timestamped line to bridge.log beside this add-in. Writing to a
    file (not the Fusion UI) keeps startup non-blocking and debuggable."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass  # logging must never take the bridge down


# ── Listener Setup ───────────────────────────────────────────────────────────

def _tailscale_ip():
    """This host's Tailscale IPv4 (100.64.0.0/10), or None if the tailnet is down.

    Prefers `tailscale ip -4` (Windows getaddrinfo(hostname) often resolves to
    the LAN NIC only and misses the CGNAT address), falls back to scanning
    hostname resolution for a 100.64/10 address.
    """
    try:
        out = subprocess.check_output(
            ["tailscale", "ip", "-4"], timeout=5, text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            ip = line.strip()
            octets = ip.split(".")
            if len(octets) == 4 and octets[0] == "100" and 64 <= int(octets[1]) <= 127:
                return ip
    except Exception:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            octets = ip.split(".")
            if octets[0] == "100" and 64 <= int(octets[1]) <= 127:
                return ip
    except Exception:
        pass
    return None


def _serve_on(bind_ip):
    """Start a bridge listener bound to one address. Returns (server, thread)."""
    server = HTTPServer((bind_ip, BRIDGE_PORT), BridgeHTTPHandler)
    server.allow_reuse_address = True  # reloads must not hit EADDRINUSE
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _start_tailnet_listener():
    """
    Bind a second listener to the Tailscale IP so peers (e.g. the a9 agent
    host) reach the bridge directly instead of through an SSH reverse tunnel.

    Retries because Tailscale may not have an address yet when Fusion starts.
    Failure here is non-fatal — the loopback listener is the source of truth, so
    local control keeps working even with the tailnet down.
    """
    global _tailnet_server, _tailnet_thread

    for attempt in range(1, _TAILNET_RETRY_ATTEMPTS + 1):
        if _stopping:
            return
        ip = _tailscale_ip()
        if ip:
            try:
                _tailnet_server, _tailnet_thread = _serve_on(ip)
                _log("tailnet bridge listening on %s:%s" % (ip, BRIDGE_PORT))
                return
            except OSError as exc:
                _log("tailnet bind %s:%s failed (attempt %d): %s" % (ip, BRIDGE_PORT, attempt, exc))
        else:
            _log("no tailscale address yet (attempt %d)" % attempt)
        time.sleep(_TAILNET_RETRY_DELAY)
    _log("tailnet listener gave up after %d retries" % _TAILNET_RETRY_ATTEMPTS)


# ── Add-in Entry Points ───────────────────────────────────────────────────────

def run(context):
    global _app, _ui, _http_server, _http_thread, _tailnet_server, _tailnet_thread, _stopping

    try:
        _stopping = False
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        # Register the custom event used to wake the main thread (prevent GC)
        _handlers.append(handler)

        # Loopback listener is the source of truth — local control always works.
        _http_server, _http_thread = _serve_on("127.0.0.1")
        _log("bridge listening on 127.0.0.1:%s" % BRIDGE_PORT)

        # Tailnet listener starts off-thread: it sleeps between retries and
        # must never block Fusion's init sequence.
        threading.Thread(target=_start_tailnet_listener, daemon=True).start()

        # NOTE: Do NOT pop a modal messageBox here. A modal dialog fired from
        # run() during Fusion startup blocks the init sequence and freezes the
        # app. The bridge starts silently; failures go to bridge.log. Check
        # port 7634 (and the tailnet IP) to confirm it's up.
    except Exception:
        _log("run() failed:\n" + traceback.format_exc())


def stop(context):
    global _http_server, _http_thread, _tailnet_server, _tailnet_thread, _stopping

    _stopping = True  # tells a pending tailnet retry loop to give up

    for srv in (_http_server, _tailnet_server):
        if srv is not None:
            try:
                srv.shutdown()
                srv.server_close()  # release the socket, not just the loop
            except Exception:
                _log("shutdown error:\n" + traceback.format_exc())
    _http_server = None
    _tailnet_server = None

    try:
        _app.unregisterCustomEvent(CUSTOM_EVENT_ID)
        _handlers.clear()
        _log("bridge stopped")
    except Exception:
        _log("stop cleanup error:\n" + traceback.format_exc())
