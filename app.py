#!/usr/bin/env python3
"""
app.py — GUI launcher for extract-dimensions.
Double-click (or run `python app.py`) to open the drawing picker.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

ICON_EMOJI = "📐"   # fallback title-bar text when no .ico available


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Extract Dimensions → OpenSCAD")
        self.resizable(False, False)
        self._build_ui()
        self._center()

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 16, "pady": 8}

        # ── Icon / header ──────────────────────────────────────────────
        tk.Label(self, text=ICON_EMOJI, font=("Segoe UI Emoji", 48)).pack(pady=(20, 0))
        tk.Label(
            self,
            text="Technical Drawing → OpenSCAD",
            font=("Segoe UI", 13, "bold"),
        ).pack()
        tk.Label(
            self,
            text="Select a PDF drawing and generate a parametric .scad model.",
            font=("Segoe UI", 9),
            fg="#555",
        ).pack(pady=(2, 12))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16)

        # ── PDF file picker ────────────────────────────────────────────
        frame_file = tk.Frame(self)
        frame_file.pack(fill="x", **pad)
        tk.Label(frame_file, text="PDF drawing:", width=14, anchor="w").pack(side="left")
        self.var_pdf = tk.StringVar()
        tk.Entry(frame_file, textvariable=self.var_pdf, width=38, state="readonly").pack(
            side="left", padx=(0, 6)
        )
        tk.Button(frame_file, text="Browse…", command=self._browse_pdf).pack(side="left")

        # ── Output folder ──────────────────────────────────────────────
        frame_out = tk.Frame(self)
        frame_out.pack(fill="x", **pad)
        tk.Label(frame_out, text="Output folder:", width=14, anchor="w").pack(side="left")
        self.var_out = tk.StringVar(value=os.path.join(os.getcwd(), "output"))
        tk.Entry(frame_out, textvariable=self.var_out, width=38, state="readonly").pack(
            side="left", padx=(0, 6)
        )
        tk.Button(frame_out, text="Browse…", command=self._browse_out).pack(side="left")

        # ── Options ────────────────────────────────────────────────────
        frame_opts = tk.Frame(self)
        frame_opts.pack(fill="x", **pad)

        # Extrusion height
        tk.Label(frame_opts, text="Extrude height:", width=14, anchor="w").pack(side="left")
        self.var_extrude = tk.StringVar()
        tk.Entry(frame_opts, textvariable=self.var_extrude, width=8).pack(side="left")
        tk.Label(frame_opts, text="mm  (leave blank for 2D only)", fg="#555").pack(side="left", padx=(4, 0))

        # PDF page index
        frame_page = tk.Frame(self)
        frame_page.pack(fill="x", **pad)
        tk.Label(frame_page, text="PDF page:", width=14, anchor="w").pack(side="left")
        self.var_page = tk.StringVar(value="1")
        tk.Entry(frame_page, textvariable=self.var_page, width=5).pack(side="left")
        tk.Label(frame_page, text="(first page = 1)", fg="#555").pack(side="left", padx=(4, 0))

        # Checkboxes
        frame_chk = tk.Frame(self)
        frame_chk.pack(fill="x", padx=16, pady=(0, 4))
        self.var_ai_only = tk.BooleanVar()
        tk.Checkbutton(
            frame_chk, text="Force AI vision (skip library parsing)", variable=self.var_ai_only
        ).pack(side="left")
        self.var_json_only = tk.BooleanVar()
        tk.Checkbutton(
            frame_chk, text="JSON only (no .scad)", variable=self.var_json_only
        ).pack(side="left", padx=(12, 0))

        # Anthropic API key (hidden)
        frame_key = tk.Frame(self)
        frame_key.pack(fill="x", **pad)
        tk.Label(frame_key, text="API key:", width=14, anchor="w").pack(side="left")
        self.var_key = tk.StringVar(value=os.environ.get("ANTHROPIC_API_KEY", ""))
        tk.Entry(frame_key, textvariable=self.var_key, width=46, show="•").pack(side="left")
        tk.Label(frame_key, text="(only needed for AI path)", fg="#888", font=("Segoe UI", 8)).pack(
            side="left", padx=(4, 0)
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=(8, 0))

        # ── Run button ─────────────────────────────────────────────────
        self.btn_run = tk.Button(
            self,
            text="▶  Extract & Generate",
            font=("Segoe UI", 11, "bold"),
            bg="#1a6fdd",
            fg="white",
            activebackground="#1258b0",
            activeforeground="white",
            relief="flat",
            padx=20,
            pady=8,
            command=self._run,
        )
        self.btn_run.pack(pady=(10, 4))

        # ── Progress / log ─────────────────────────────────────────────
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=420)
        self.progress.pack(padx=16, pady=(4, 0))

        self.log_text = tk.Text(
            self, height=8, width=60, state="disabled",
            font=("Consolas", 9), bg="#f5f5f5", relief="flat"
        )
        self.log_text.pack(padx=16, pady=(6, 16))

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------
    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select PDF technical drawing",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.var_pdf.set(path)
            # Auto-set output dir next to the PDF
            self.var_out.set(os.path.join(os.path.dirname(path), "output"))

    def _browse_out(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.var_out.set(path)

    # ------------------------------------------------------------------
    # Extraction runner (background thread to keep UI responsive)
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

        thread = threading.Thread(target=self._run_extraction, daemon=True)
        thread.start()

    def _run_extraction(self):
        pdf_path = self.var_pdf.get().strip()
        output_dir = self.var_out.get().strip() or "output"
        ai_only = self.var_ai_only.get()
        json_only = self.var_json_only.get()
        api_key = self.var_key.get().strip() or None
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
            stem = os.path.splitext(os.path.basename(pdf_path))[0]
            json_path = os.path.join(output_dir, f"{stem}.json")
            scad_path = os.path.join(output_dir, f"{stem}.scad")

            # ---- Library path ----------------------------------------
            use_ai = ai_only
            drawing_data = None

            if not ai_only:
                self._log("Stage 1: Extracting vector paths and text from PDF…")
                from pdf_parser import extract_paths, extract_raw_text
                from dimension_parser import parse_dimensions, infer_units

                shapes = extract_paths(pdf_path, page_index=page_index)
                raw_text = extract_raw_text(pdf_path, page_index=page_index)
                dimensions = parse_dimensions(raw_text)
                units = infer_units(dimensions)

                self._log(f"  → {len(shapes)} shape(s), {len(dimensions)} dimension(s) found")

                if len(dimensions) < 2 or len(shapes) < 1:
                    self._log("  → Not enough data — switching to Claude vision API…")
                    use_ai = True
                else:
                    from data_model import DrawingData
                    drawing_data = DrawingData(
                        source=os.path.basename(pdf_path),
                        units=units,
                        extraction_method="library",
                        dimensions=dimensions,
                        shapes=shapes,
                        extrude_height=extrude_height,
                    )

            # ---- AI path ---------------------------------------------
            if use_ai:
                self._log("Stage 2: Calling Claude vision API (claude-opus-4-6)…")
                if api_key:
                    os.environ["ANTHROPIC_API_KEY"] = api_key
                from ai_extractor import extract_with_ai
                drawing_data = extract_with_ai(
                    pdf_path,
                    page_index=page_index,
                    extrude_height=extrude_height,
                    api_key=api_key,
                )
                self._log(
                    f"  → AI extracted {len(drawing_data.dimensions)} dim(s), "
                    f"{len(drawing_data.shapes)} shape(s)"
                )

            if drawing_data is None:
                raise RuntimeError("No data could be extracted.")

            if extrude_height is not None:
                drawing_data.extrude_height = extrude_height

            # ---- JSON ------------------------------------------------
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(drawing_data.to_json())
            self._log(f"JSON  → {json_path}")

            # ---- .scad -----------------------------------------------
            if not json_only:
                from scad_generator import generate_scad
                generate_scad(drawing_data, scad_path)
                self._log(f".scad → {scad_path}")

            self._log(
                f"\nDone! method={drawing_data.extraction_method}"
                f"  units={drawing_data.units}"
            )
            self.after(0, lambda: self._on_success(output_dir))

        except Exception as exc:
            self._log(f"\nERROR: {exc}")
            self.after(0, lambda: messagebox.showerror("Extraction failed", str(exc)))
            self.after(0, self._stop_progress)

    def _on_success(self, output_dir: str):
        self._stop_progress()
        if messagebox.askyesno(
            "Done!", f"Extraction complete.\n\nOpen output folder?\n{output_dir}"
        ):
            _open_folder(output_dir)

    def _stop_progress(self):
        self.progress.stop()
        self.btn_run.config(state="normal")

    # ------------------------------------------------------------------
    # Log helpers
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
        w, h = self.winfo_width(), self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ---------------------------------------------------------------------------
# Helper: open folder in the OS file manager
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
