#!/usr/bin/env python3
"""
app.py — GUI launcher for extract-dimensions.
Double-click the desktop icon (or run `python app.py`) to open the drawing picker.
Missing information (API key, output folder) is requested via pop-up dialogs
only when actually needed.
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".config", "extract-dimensions", "config.json")


# ---------------------------------------------------------------------------
# Persistent config (API key, last output dir)
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(data: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Pop-up dialog: ask for a single text value
# ---------------------------------------------------------------------------

class _AskDialog(tk.Toplevel):
    """Modal dialog that asks for a single string value."""

    def __init__(self, parent, title: str, prompt: str, secret: bool = False, initial: str = ""):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: str | None = None
        self.grab_set()

        tk.Label(self, text=prompt, wraplength=340, justify="left",
                 font=("Segoe UI", 10)).pack(padx=20, pady=(20, 8))

        self._var = tk.StringVar(value=initial)
        show = "•" if secret else ""
        entry = tk.Entry(self, textvariable=self._var, width=44, show=show)
        entry.pack(padx=20, pady=(0, 12))
        entry.focus_set()

        btn_frame = tk.Frame(self)
        btn_frame.pack(padx=20, pady=(0, 16))
        tk.Button(btn_frame, text="OK", width=10, command=self._ok,
                  bg="#1a6fdd", fg="white", relief="flat").pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="Cancel", width=10,
                  command=self._cancel, relief="flat").pack(side="left")

        self.bind("<Return>", lambda _: self._ok())
        self.bind("<Escape>", lambda _: self._cancel())
        self._center(parent)
        self.wait_window()

    def _ok(self):
        self.result = self._var.get().strip()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Extract Dimensions → OpenSCAD")
        self.resizable(False, False)
        self._config = _load_config()
        self._set_icon()
        self._build_ui()
        self._center()

    # ------------------------------------------------------------------
    # Icon
    # ------------------------------------------------------------------
    def _set_icon(self):
        icon_path = os.path.join(BASE_DIR, "icon.png")
        if os.path.isfile(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, img)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 16, "pady": 8}

        # Header
        tk.Label(self, text="📐", font=("Segoe UI Emoji", 44)).pack(pady=(18, 0))
        tk.Label(self, text="Technical Drawing → OpenSCAD",
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(self, text="Pick a PDF drawing and get a parametric .scad model.",
                 font=("Segoe UI", 9), fg="#555").pack(pady=(2, 10))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16)

        # PDF picker
        fr = tk.Frame(self)
        fr.pack(fill="x", **pad)
        tk.Label(fr, text="PDF drawing:", width=14, anchor="w").pack(side="left")
        self.var_pdf = tk.StringVar()
        tk.Entry(fr, textvariable=self.var_pdf, width=36, state="readonly").pack(side="left", padx=(0, 6))
        tk.Button(fr, text="Browse…", command=self._browse_pdf).pack(side="left")

        # Output folder
        fr2 = tk.Frame(self)
        fr2.pack(fill="x", **pad)
        tk.Label(fr2, text="Output folder:", width=14, anchor="w").pack(side="left")
        default_out = self._config.get("last_output", os.path.join(os.getcwd(), "output"))
        self.var_out = tk.StringVar(value=default_out)
        tk.Entry(fr2, textvariable=self.var_out, width=36, state="readonly").pack(side="left", padx=(0, 6))
        tk.Button(fr2, text="Browse…", command=self._browse_out).pack(side="left")

        # Extrude height
        fr3 = tk.Frame(self)
        fr3.pack(fill="x", **pad)
        tk.Label(fr3, text="Extrude height:", width=14, anchor="w").pack(side="left")
        self.var_extrude = tk.StringVar()
        tk.Entry(fr3, textvariable=self.var_extrude, width=8).pack(side="left")
        tk.Label(fr3, text="mm  (blank = 2D only)", fg="#666").pack(side="left", padx=(6, 0))

        # PDF page
        fr4 = tk.Frame(self)
        fr4.pack(fill="x", **pad)
        tk.Label(fr4, text="PDF page:", width=14, anchor="w").pack(side="left")
        self.var_page = tk.StringVar(value="1")
        tk.Entry(fr4, textvariable=self.var_page, width=5).pack(side="left")
        tk.Label(fr4, text="(first page = 1)", fg="#666").pack(side="left", padx=(6, 0))

        # Checkboxes
        fr5 = tk.Frame(self)
        fr5.pack(fill="x", padx=16, pady=(0, 2))
        self.var_ai_only = tk.BooleanVar()
        tk.Checkbutton(fr5, text="Force AI vision", variable=self.var_ai_only).pack(side="left")
        self.var_json_only = tk.BooleanVar()
        tk.Checkbutton(fr5, text="JSON only (no .scad)", variable=self.var_json_only).pack(side="left", padx=(16, 0))

        # API key status indicator (no text field — key is managed via dialog)
        self.lbl_key_status = tk.Label(self, text="", font=("Segoe UI", 8), fg="#888")
        self.lbl_key_status.pack()
        self._refresh_key_status()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=(6, 0))

        # Run button
        self.btn_run = tk.Button(
            self, text="▶  Extract & Generate",
            font=("Segoe UI", 11, "bold"),
            bg="#1a6fdd", fg="white",
            activebackground="#1258b0", activeforeground="white",
            relief="flat", padx=20, pady=8,
            command=self._run,
        )
        self.btn_run.pack(pady=(10, 4))

        # Small "Set API key" link
        tk.Button(self, text="Set / update API key", font=("Segoe UI", 8),
                  relief="flat", fg="#1a6fdd", cursor="hand2",
                  command=self._prompt_api_key).pack(pady=(0, 4))

        # Progress + log
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        self.progress.pack(padx=16, pady=(4, 0))

        self.log_text = tk.Text(self, height=7, width=58, state="disabled",
                                font=("Consolas", 9), bg="#f5f5f5", relief="flat")
        self.log_text.pack(padx=16, pady=(6, 16))

    # ------------------------------------------------------------------
    # API key management
    # ------------------------------------------------------------------
    def _get_api_key(self) -> str | None:
        """Return API key from env → config → user dialog (cached to config)."""
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if key:
            return key
        key = self._config.get("api_key", "").strip()
        if key:
            return key
        return None

    def _prompt_api_key(self, reason: str = "") -> str | None:
        """Show a modal dialog asking for the API key. Saves to config on OK."""
        msg = (reason + "\n\n" if reason else "") + \
              "Enter your Anthropic API key.\nIt will be saved locally for future use."
        dlg = _AskDialog(self, title="Anthropic API Key", prompt=msg,
                         secret=True, initial=self._config.get("api_key", ""))
        key = dlg.result
        if key:
            self._config["api_key"] = key
            _save_config(self._config)
            self._refresh_key_status()
        return key

    def _refresh_key_status(self):
        key = self._get_api_key()
        if key:
            self.lbl_key_status.config(text=f"API key: set  ({'env' if os.environ.get('ANTHROPIC_API_KEY') else 'saved'})",
                                       fg="#2a9d2a")
        else:
            self.lbl_key_status.config(text="API key: not set  (needed only for scanned PDFs)", fg="#888")

    # ------------------------------------------------------------------
    # File / folder pickers
    # ------------------------------------------------------------------
    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select PDF technical drawing",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.var_pdf.set(path)
            out = os.path.join(os.path.dirname(path), "output")
            self.var_out.set(out)
            self._config["last_output"] = out
            _save_config(self._config)

    def _browse_out(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.var_out.set(path)
            self._config["last_output"] = path
            _save_config(self._config)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def _run(self):
        pdf_path = self.var_pdf.get().strip()
        if not pdf_path:
            messagebox.showwarning("No file selected", "Please select a PDF drawing first.")
            return
        if not os.path.isfile(pdf_path):
            messagebox.showerror("File not found", f"Cannot find:\n{pdf_path}")
            return

        self.btn_run.config(state="disabled")
        self.progress.start(12)
        self._clear_log()
        threading.Thread(target=self._run_extraction, daemon=True).start()

    def _run_extraction(self):
        pdf_path   = self.var_pdf.get().strip()
        output_dir = self.var_out.get().strip() or "output"
        ai_only    = self.var_ai_only.get()
        json_only  = self.var_json_only.get()
        try:
            page_index = max(0, int(self.var_page.get()) - 1)
        except ValueError:
            page_index = 0
        try:
            extrude_height = float(self.var_extrude.get()) if self.var_extrude.get().strip() else None
        except ValueError:
            extrude_height = None

        try:
            os.makedirs(output_dir, exist_ok=True)
            stem      = os.path.splitext(os.path.basename(pdf_path))[0]
            json_path = os.path.join(output_dir, f"{stem}.json")
            scad_path = os.path.join(output_dir, f"{stem}.scad")

            use_ai       = ai_only
            drawing_data = None

            # ── Library path ──────────────────────────────────────────
            if not ai_only:
                self._log("Stage 1: Extracting vector paths from PDF…")
                from pdf_parser import extract_paths, extract_text_spans
                from dimension_parser import parse_dimensions_from_spans, infer_units
                from geometry_linker import link_dimensions
                from dataclasses import asdict

                shapes     = extract_paths(pdf_path, page_index=page_index)
                spans      = extract_text_spans(pdf_path, page_index=page_index)
                dimensions = parse_dimensions_from_spans(spans)
                units      = infer_units(dimensions)

                self._log(f"  → {len(shapes)} shape(s), {len(dimensions)} dimension(s)")

                if len(dimensions) < 2 or len(shapes) < 1:
                    self._log("  → Not enough data — switching to Claude vision API…")
                    use_ai = True
                else:
                    from data_model import DrawingData
                    link_result = link_dimensions(dimensions, shapes)
                    drawing_data = DrawingData(
                        source=os.path.basename(pdf_path),
                        units=units,
                        extraction_method="library",
                        dimensions=dimensions,
                        shapes=shapes,
                        extrude_height=extrude_height,
                        links=[asdict(l) for l in link_result.links],
                        orphans=[asdict(o) for o in link_result.orphans],
                    )

            # ── AI path (ask for key only if needed) ──────────────────
            if use_ai:
                api_key = self._get_api_key()
                if not api_key:
                    # Ask from the main thread (tkinter is not thread-safe)
                    result_holder = [None]
                    event = threading.Event()

                    def ask():
                        result_holder[0] = self._prompt_api_key(
                            "This drawing needs the Claude AI vision API\n"
                            "(library parsing found insufficient data)."
                        )
                        event.set()

                    self.after(0, ask)
                    event.wait()
                    api_key = result_holder[0]

                if not api_key:
                    raise RuntimeError("API key required for AI extraction. Cancelled.")

                self._log("Stage 2: Calling Claude vision API (claude-opus-4-6)…")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                from ai_extractor import extract_with_ai
                drawing_data = extract_with_ai(
                    pdf_path, page_index=page_index,
                    extrude_height=extrude_height, api_key=api_key,
                )
                self._log(f"  → {len(drawing_data.dimensions)} dim(s), {len(drawing_data.shapes)} shape(s)")

            if drawing_data is None:
                raise RuntimeError("No data could be extracted.")

            if extrude_height is not None:
                drawing_data.extrude_height = extrude_height

            # ── Write outputs ─────────────────────────────────────────
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(drawing_data.to_json())
            self._log(f"JSON  → {json_path}")

            if not json_only:
                from scad_generator import generate_scad
                generate_scad(drawing_data, scad_path)
                self._log(f".scad → {scad_path}")

            self._log(f"\nDone!  method={drawing_data.extraction_method}  units={drawing_data.units}")
            self.after(0, lambda: self._on_success(output_dir))

        except Exception as exc:
            self._log(f"\nERROR: {exc}")
            self.after(0, lambda: messagebox.showerror("Extraction failed", str(exc)))
            self.after(0, self._stop_progress)

    def _on_success(self, output_dir: str):
        self._stop_progress()
        if messagebox.askyesno("Done!", f"Extraction complete.\n\nOpen output folder?\n{output_dir}"):
            _open_folder(output_dir)

    def _stop_progress(self):
        self.progress.stop()
        self.btn_run.config(state="normal")

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------
    def _log(self, msg: str):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _append)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    # ------------------------------------------------------------------
    # Window centering
    # ------------------------------------------------------------------
    def _center(self):
        self.update_idletasks()
        w  = self.winfo_width()
        h  = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ---------------------------------------------------------------------------
# OS folder opener
# ---------------------------------------------------------------------------
def _open_folder(path: str):
    import subprocess
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
