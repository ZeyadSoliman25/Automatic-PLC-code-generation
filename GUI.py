"""
AI Agent for PLC Code Generation
Workflow: User Input → Parse/Format → Route (STL/SCL) → Local AI Gen → TIA Import
Dependencies:
pip install customtkinter python-docx pdfplumber pythonnet
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import re
from pathlib import Path
from typing import Any
import TIA_Handler as tia

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

TIA_VERSIONS  = ["V17", "V18", "V19", "V20"]
PLC_TYPES     = ["S7-1500", "S7-1200", "S7-300"]
PLC_LANGUAGES = ["SCL", "STL"]
#Output file extension per PLC language
LANG_EXTENSION = {"SCL": ".scl", "STL": ".awl"}

#TIA Portal project file extensions — one per version
#.ap17 → V17, .ap18 → V18, .ap19 → V19, .ap20 → V20
TIA_FILE_TYPES = [
    ("TIA Portal Project V17", "*.ap17"),
    ("TIA Portal Project V18", "*.ap18"),
    ("TIA Portal Project V19", "*.ap19"),
    ("TIA Portal Project V20", "*.ap20"),
    ("All TIA Portal Projects", "*.ap17 *.ap18 *.ap19 *.ap20"),
]

def _apxx_version(filepath: str) -> str:
    """Return the TIA version string encoded in a .apXX filename, or '' if unknown."""
    ext = os.path.splitext(filepath)[1].lower()
    m = re.fullmatch(r"\.ap(\d{2})", ext)
    return f"V{m.group(1)}" if m else ""

# ── Parser Layer ───────────────────────────────────────────────────────────────
def _parse_document(file_path: str) -> str:
    """
    Extract raw text from uploaded documents.
    Supports .txt natively. Requires python-docx / pdfplumber for .docx / .pdf.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".txt":
        return path.read_text(encoding="utf-8")
    elif ext == ".docx":
        try:
            import docx
            return "\n".join([p.text for p in docx.Document(str(path)).paragraphs])
        except ImportError:
            raise ImportError("Install python-docx to parse .docx files: pip install python-docx")
    elif ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            raise ImportError("Install pdfplumber to parse .pdf files: pip install pdfplumber")
    else:
        raise ValueError(f"Unsupported document format: {ext}")

# ═══════════════════════════════════════════════════════════════════════════════
# Main application window
# ═══════════════════════════════════════════════════════════════════════════════
class PlcAgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Agent for PLC Code Generation")
        self.geometry("820x800")
        self.resizable(False, False)

        # Internal state
        self._doc_path: str      = ""
        self._project_file: str  = ""
        self._last_inputs: dict  = {}

        self._build_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC BRIDGE METHOD
    # ══════════════════════════════════════════════════════════════════════════
    def get_user_inputs(self) -> dict[str, Any]:
        raw_prompt  = self._prompt_box.get("0.0", "end").strip()
        placeholder = "Describe the PLC logic you need to generate…"
        is_text     = self._input_mode.get() == "text"

        proj_file   = self._project_file
        proj_folder = os.path.dirname(proj_file) if proj_file else ""

        self._last_inputs = {
            "input_mode":     self._input_mode.get(),
            "prompt":         raw_prompt if (is_text and raw_prompt != placeholder) else "",
            "doc_path":       self._doc_path if not is_text else "",
            "project_file":   proj_file,
            "project_folder": proj_folder,
            "tia_version":    self._tia_var.get(),
            "plc_type":       self._plc_var.get(),
            "plc_language":   self._lang_var.get(),
            "show_tia":       self._show_tia.get() == "show",
        }
        return self._last_inputs

    # ══════════════════════════════════════════════════════════════════════════
    #  UI construction
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Header bar ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#1B3A6B", corner_radius=0, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="  \u2022  AI Agent for PLC Code Generation",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=18, pady=12)

        # ── Scrollable body ───────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="#EDEDED", corner_radius=0)
        body.pack(fill="both", expand=True)

        content = ctk.CTkFrame(body, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=18)

        # ── 1. Input mode ─────────────────────────────────────────────────────
        self._build_section_label(content, "Input Control Narrative:")
        mode_row = ctk.CTkFrame(content, fg_color="transparent")
        mode_row.pack(fill="x", pady=(4, 0))

        self._input_mode = ctk.StringVar(value="text")
        ctk.CTkRadioButton(
            mode_row, text="Write text prompt",
            variable=self._input_mode, value="text",
            command=self._on_mode_change,
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            mode_row, text="Upload document",
            variable=self._input_mode, value="doc",
            command=self._on_mode_change,
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).pack(side="left", padx=(0, 14))
        self._select_btn = ctk.CTkButton(
            mode_row, text="\U0001F4C4  Select File…",
            width=140, height=30,
            fg_color="#D0D0D0", text_color="#333", hover_color="#B8B8B8",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._select_narrative_file, state="disabled",
        )
        self._select_btn.pack(side="left")

        self._file_label = ctk.CTkLabel(
            content, text="", text_color="#555",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self._file_label.pack(anchor="w", pady=(2, 0))

        # ── 2. Prompt box ──────────────────────────────────────────────────────
        self._build_section_label(content, "Enter Your Prompt:", pady_top=14)
        self._prompt_box = ctk.CTkTextbox(
            content, height=130,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="white", border_color="#CCCCCC",
            border_width=1, corner_radius=6,
        )
        self._prompt_box.pack(fill="x")
        self._prompt_box.insert("0.0", "Describe the PLC logic you need to generate…")
        self._prompt_box.bind("<FocusIn>", self._clear_placeholder)
        self._prompt_box.bind("<FocusOut>", self._restore_placeholder)

        # ── 3. Three-column dropdowns ───────────────────────────────────────────
        selectors = ctk.CTkFrame(content, fg_color="transparent")
        selectors.pack(fill="x", pady=(14, 0))
        selectors.columnconfigure(0, weight=1)
        selectors.columnconfigure(1, weight=1)
        selectors.columnconfigure(2, weight=1)

        self._tia_var  = ctk.StringVar(value=TIA_VERSIONS[0])
        self._plc_var  = ctk.StringVar(value=PLC_TYPES[0])
        self._lang_var = ctk.StringVar(value=PLC_LANGUAGES[0])

        self._build_combobox_col(selectors, col=0, label="TIA Portal Version:", values=TIA_VERSIONS, variable=self._tia_var, padx=(0, 8))
        self._build_combobox_col(selectors, col=1, label="Siemens PLC Type:", values=PLC_TYPES, variable=self._plc_var, padx=(8, 8))
        self._build_combobox_col(selectors, col=2, label="PLC Language:", values=PLC_LANGUAGES, variable=self._lang_var, padx=(8, 0))

        # ── 4. TIA Portal project file ────────────────────────────────────────
        self._separator(content)
        self._build_section_label(content, "TIA Portal Project File (.apXX):")
        proj_row = ctk.CTkFrame(content, fg_color="transparent")
        proj_row.pack(fill="x", pady=(4, 0))

        self._project_entry = ctk.CTkEntry(
            proj_row, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            placeholder_text="Browse to select your TIA Portal .apXX project file…",
            state="readonly", fg_color="white", border_color="#CCCCCC",
        )
        self._project_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            proj_row, text="Browse…", width=90, height=34,
            fg_color="#1B5EA6", text_color="white", hover_color="#154E8C",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._browse_project_file,
        ).pack(side="left")

        self._proj_info_label = ctk.CTkLabel(
            content, text="", font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#555"
        )
        self._proj_info_label.pack(anchor="w", pady=(3, 0))

        # ── 5. TIA Portal display toggle ───────────────────────────────────────
        self._separator(content)
        tia_toggle_row = ctk.CTkFrame(content, fg_color="transparent")
        tia_toggle_row.pack(fill="x")
        ctk.CTkLabel(
            tia_toggle_row, text="Display TIA Portal:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).pack(side="left", padx=(0, 14))

        self._show_tia = ctk.StringVar(value="show")
        ctk.CTkRadioButton(
            tia_toggle_row, text="Show TIA Portal",
            variable=self._show_tia, value="show",
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            tia_toggle_row, text="Do Not Show",
            variable=self._show_tia, value="hide",
            font=ctk.CTkFont(family="Segoe UI", size=13),
        ).pack(side="left")

        # ── 6. Generate button + progress ──────────────────────────────────────
        self._separator(content)
        self._gen_btn = ctk.CTkButton(
            content, text="Generate Code", height=48,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#1B5EA6", hover_color="#154E8C", corner_radius=8,
            command=self._on_generate,
        )
        self._gen_btn.pack(fill="x", pady=(4, 0))

        self._status_label = ctk.CTkLabel(
            content, text="", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#555"
        )
        self._status_label.pack(pady=(6, 0))

        self._progress = ctk.CTkProgressBar(content, height=6)
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(4, 0))
        self._progress.pack_forget()

    # ── UI helpers ─────────────────────────────────────────────────────────────
    def _build_section_label(self, parent, text: str, pady_top: int = 0):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        ).pack(anchor="w", pady=(pady_top, 2))

    def _build_combobox_col(self, parent, col: int, label: str,
                            values: list, variable: ctk.StringVar,
                            padx: tuple = (0, 0)):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=col, sticky="ew", padx=padx, pady=(0, 4))
        ctk.CTkLabel(
            frame, text=label,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkComboBox(
            frame, values=values, variable=variable,
            height=34, font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=13),
            state="readonly",
        ).pack(anchor="w", fill="x", pady=(4, 0))

    def _separator(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color="#CCCCCC").pack(fill="x", pady=12)

    def _set_entry_text(self, entry: ctk.CTkEntry, text: str):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="readonly")

    # ── Event handlers ─────────────────────────────────────────────────────────
    def _on_mode_change(self):
        if self._input_mode.get() == "doc":
            self._select_btn.configure(state="normal")
            self._prompt_box.configure(state="disabled", fg_color="#F0F0F0")
        else:
            self._select_btn.configure(state="disabled")
            self._prompt_box.configure(state="normal", fg_color="white")
            self._file_label.configure(text="")
            self._doc_path = ""

    def _select_narrative_file(self):
        path = filedialog.askopenfilename(
            title="Select Control Narrative Document",
            filetypes=[("Documents", "*.pdf *.docx *.txt"), ("All files", "*.*")],
        )
        if path:
            self._doc_path = path
            self._file_label.configure(text=f"\u2714  {os.path.basename(path)}")

    def _browse_project_file(self):
        path = filedialog.askopenfilename(
            title="Select TIA Portal Project File",
            filetypes=TIA_FILE_TYPES,
        )
        if not path:
            return

        if not re.search(r"\.ap\d{2}$", path, re.IGNORECASE):
            messagebox.showwarning("Invalid File", "Please select a valid TIA Portal project file (.ap17, .ap18, .ap19, .ap20).")
            return

        self._project_file = path
        self._set_entry_text(self._project_entry, path)

        detected = _apxx_version(path)
        if detected:
            if detected in TIA_VERSIONS:
                self._tia_var.set(detected)
            self._proj_info_label.configure(
                text=f"\u2139  Detected TIA Portal {detected}  \u2014  Folder: {os.path.dirname(path)}",
                text_color="#1B5EA6",
            )
        else:
            self._proj_info_label.configure(text=f"\u2714  {os.path.basename(path)}", text_color="#555")

    def _clear_placeholder(self, _event):
        if self._prompt_box.get("0.0", "end").strip() == "Describe the PLC logic you need to generate…":
            self._prompt_box.delete("0.0", "end")

    def _restore_placeholder(self, _event):
        if not self._prompt_box.get("0.0", "end").strip():
            self._prompt_box.insert("0.0", "Describe the PLC logic you need to generate…")

    # ── Generate ───────────────────────────────────────────────────────────────
    def _on_generate(self):
        inputs = self.get_user_inputs()

        if inputs["input_mode"] == "text":
            if not inputs["prompt"]:
                messagebox.showwarning("Missing Input", "Please enter a prompt describing the PLC logic.")
                return
        else:
            if not inputs["doc_path"]:
                messagebox.showwarning("Missing Input", "Please select a control narrative document.")
                return

        if not inputs["project_file"]:
            messagebox.showwarning("Missing Input", "Please browse and select a TIA Portal project file (.apXX).")
            return

        # Lock UI
        self._gen_btn.configure(state="disabled", text="Generating…")
        self._status_label.configure(text=f"Preparing {inputs['plc_language']} generation…", text_color="#555")
        self._progress.pack(fill="x", pady=(4, 0))
        self._progress.configure(mode="indeterminate")
        self._progress.start()

        def worker():
            try:
                import pythoncom
                pythoncom.CoInitialize()  # TIA Openness requires STA in background threads

                # 1. Parse/Format Prompt
                self.after(0, lambda: self._status_label.configure(text="Parsing narrative…", text_color="#555"))
                prompt = _parse_document(inputs["doc_path"]) if inputs["input_mode"] == "doc" else inputs["prompt"]

                if not prompt.strip():
                    raise ValueError("Prompt is empty after parsing.")

                # 2. Route & Generate
                lang = inputs["plc_language"]
                self.after(0, lambda: self._status_label.configure(text=f"Loading local AI & generating {lang}…", text_color="#555"))

                if lang == "STL":
                    import generate_stl
                    xml_path = generate_stl.generate_ob1(prompt)
                else:
                    import generate_scl
                    xml_path = generate_scl.generate_ob1_scl(prompt)

                # 3. Import to TIA Portal
                self.after(0, lambda: self._status_label.configure(text="Importing into TIA Portal…", text_color="#555"))
                handler = tia.TiaHandler()
                handler.import_generated_ob(
                    xml_path=str(xml_path),
                    project_path=inputs["project_file"],
                    with_ui=inputs["show_tia"]
                )

                self.after(0, lambda: self._on_success("Code generated & imported successfully!", inputs))

            except Exception as exc:
                self.after(0, lambda e=exc: self._on_error(str(e)))
            finally:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, code: str, inputs: dict):
        self._progress.stop()
        self._progress.pack_forget()
        self._gen_btn.configure(state="normal", text="Generate Code")
        self._status_label.configure(text="\u2705  " + code, text_color="green")

    def _on_error(self, msg: str):
        self._progress.stop()
        self._progress.pack_forget()
        self._gen_btn.configure(state="normal", text="Generate Code")
        self._status_label.configure(text="\u274C  Generation failed.", text_color="red")
        messagebox.showerror("Error", f"Workflow failed:\n{msg}")

# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════
def launch():
    app = PlcAgentApp()
    app.mainloop()

if __name__ == "__main__":
    launch()