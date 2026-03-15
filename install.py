#!/usr/bin/env python3
"""
install.py — Install the Extract Dimensions desktop icon.

Run once:
    python install.py

What it does:
  • Copies the .desktop file to ~/Desktop  (double-clickable icon)
  • Also installs to ~/.local/share/applications  (shows in app launcher / start menu)
  • Makes both copies executable
  • Runs `update-desktop-database` if available (Linux)
"""

import os
import shutil
import stat
import subprocess
import sys

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DESKTOP_SRC = os.path.join(BASE_DIR, "extract-dimensions.desktop")
ICON_SRC    = os.path.join(BASE_DIR, "icon.png")
APP_PY      = os.path.join(BASE_DIR, "app.py")


def main():
    # ── Sanity checks ─────────────────────────────────────────────────
    if not os.path.isfile(DESKTOP_SRC):
        sys.exit(f"Error: {DESKTOP_SRC} not found. Run from the project directory.")
    if not os.path.isfile(APP_PY):
        sys.exit(f"Error: {APP_PY} not found.")

    # ── Rewrite Exec / Icon paths to absolute ─────────────────────────
    with open(DESKTOP_SRC, "r") as f:
        content = f.read()

    python_exe = sys.executable
    content = _set_field(content, "Exec",  f"{python_exe} {APP_PY}")
    content = _set_field(content, "Icon",  ICON_SRC)

    # ── Install to Desktop ────────────────────────────────────────────
    desktop_dir = _find_desktop()
    if desktop_dir:
        dst = os.path.join(desktop_dir, "extract-dimensions.desktop")
        _write(dst, content)
        print(f"  Desktop icon → {dst}")
    else:
        print("  Desktop folder not found — skipping desktop icon.")

    # ── Install to app launcher ───────────────────────────────────────
    apps_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    os.makedirs(apps_dir, exist_ok=True)
    dst2 = os.path.join(apps_dir, "extract-dimensions.desktop")
    _write(dst2, content)
    print(f"  App launcher  → {dst2}")

    # ── Refresh desktop database (Linux) ─────────────────────────────
    try:
        subprocess.run(["update-desktop-database", apps_dir],
                       check=False, capture_output=True)
    except FileNotFoundError:
        pass

    print("\nInstalled! You can now launch the app from your desktop or app menu.")
    print(f"Or run directly:  python {APP_PY}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_desktop() -> str | None:
    """Return the path to the user's Desktop folder (cross-platform)."""
    # XDG standard
    try:
        result = subprocess.run(
            ["xdg-user-dir", "DESKTOP"], capture_output=True, text=True
        )
        path = result.stdout.strip()
        if path and os.path.isdir(path):
            return path
    except FileNotFoundError:
        pass

    # Common fallbacks
    for candidate in [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "desktop"),
    ]:
        if os.path.isdir(candidate):
            return candidate

    return None


def _set_field(content: str, key: str, value: str) -> str:
    """Replace a key=value line in a .desktop file."""
    import re
    return re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)


def _write(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)
    # Make executable (required on Linux for .desktop files)
    current = os.stat(path).st_mode
    os.chmod(path, current | stat.S_IXUSR | stat.S_IXGRP)


if __name__ == "__main__":
    main()
