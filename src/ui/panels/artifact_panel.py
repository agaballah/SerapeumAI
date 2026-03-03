# -*- coding: utf-8 -*-
"""
artifact_panel.py — Displays structured outputs (reports, tables, code)
---------------------------------------------------------------------
"""
import tkinter as tk
from tkinter import ttk
import os # Added for path operations
import platform # Added for platform detection
import subprocess # Added for external process calls

class ArtifactPanel(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.current_path = None
        self.artifacts_list = [] # List of {title, path, type}
        
        # Main Layout: 2-Pane split
        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        # 1. Left Sidebar (Artifact List)
        self.sidebar = ttk.Frame(self.paned, width=250, padding=5)
        self.paned.add(self.sidebar, weight=1)

        ttk.Label(self.sidebar, text="📂 Project Deliverables", font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(0, 5))
        
        self.listbox = tk.Listbox(
            self.sidebar, 
            bg="#252526", fg="#cccccc", 
            selectbackground="#37373d", 
            borderwidth=0, highlightthickness=0,
            font=("Segoe UI", 9)
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_artifact_select)

        # 2. Right Pane (Preview & Controls)
        self.main_pane = ttk.Frame(self.paned, padding=5)
        self.paned.add(self.main_pane, weight=4)

        # Header with Controls
        self.header = ttk.Frame(self.main_pane)
        self.header.pack(fill="x", pady=(0, 5))
        
        self.lbl_title = ttk.Label(self.header, text="Preview", font=("Segoe UI", 11, "bold"))
        self.lbl_title.pack(side="left")

        # Actions
        self.btn_reveal = ttk.Button(self.header, text="📁 Reveal", command=self._reveal_in_explorer, state="disabled", bootstyle="outline")
        self.btn_reveal.pack(side="right", padx=2)
        
        self.btn_open = ttk.Button(self.header, text="📖 Open", command=self._open_file, state="disabled", bootstyle="outline")
        self.btn_open.pack(side="right", padx=2)

        # Content Area
        self.text_area = tk.Text(
            self.main_pane,
            wrap="word",
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            state="disabled",
            padx=10, pady=10
        )
        self.text_area.pack(fill="both", expand=True)
        
        self._configure_tags()
        
    def _configure_tags(self):
        # Base colors (VS Code-ish)
        accent = "#4ec9b0"
        header_color = "#ce9178"
        code_bg = "#2d2d2d"
        code_fg = "#9cdcfe"

        self.text_area.tag_config("h1", font=("Segoe UI", 18, "bold"), foreground=accent, spacing3=12)
        self.text_area.tag_config("h2", font=("Segoe UI", 16, "bold"), foreground=header_color, spacing3=8)
        self.text_area.tag_config("h3", font=("Segoe UI", 14, "bold"), foreground="#569cd6", spacing3=5)
        self.text_area.tag_config("bold", font=("Segoe UI", 10, "bold"), foreground="#ffffff")
        self.text_area.tag_config("bullet", lmargin1=20, lmargin2=35)
        self.text_area.tag_config("code_block", font=("Consolas", 10), background=code_bg, foreground=code_fg, spacing1=4, spacing3=4, lmargin1=10, lmargin2=10)
        self.text_area.tag_config("normal", font=("Segoe UI", 10), foreground="#d4d4d4", spacing1=2)

    def add_artifact_record(self, title: str, path: str, artifact_type: str = "markdown"):
        """Add a new artifact record to the sidebar."""
        record = {"title": title, "path": path, "type": artifact_type}
        self.artifacts_list.append(record)
        
        display_name = f"📄 {title}" if artifact_type == "docx" else f"📊 {title}"
        if artifact_type == "pdf": display_name = f"📕 {title}"
        
        self.listbox.insert("end", display_name)
        # Select the newly added record
        idx = self.listbox.size() - 1
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(idx)
        self._on_artifact_select(None)

    def _on_artifact_select(self, event):
        selection = self.listbox.curselection()
        if not selection: return
        
        idx = selection[0]
        record = self.artifacts_list[idx]
        self.current_path = record["path"]
        self.lbl_title.config(text=record["title"])
        
        # Basic binary/structured preview logic
        ext = os.path.splitext(self.current_path)[1].lower()
        stats = os.stat(self.current_path)
        from datetime import datetime
        dt_str = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        size_kb = round(stats.st_size / 1024, 2)
        
        meta_info = f"Type: {record['type'].upper()}\nModified: {dt_str}\nSize: {size_kb} KB\nPath: {self.current_path}"
        
        if ext in [".txt", ".md", ".json"]:
             try:
                 with open(self.current_path, "r", encoding="utf-8") as f:
                     content = f"# {record['title']}\n\n{meta_info}\n" + "—" * 30 + "\n\n" + f.read()
             except: content = f"# {record['title']}\n\n{meta_info}"
        else:
             content = f"# {record['title']}\n\n{meta_info}\n\n" + "—" * 30 + "\n\n[Full preview of this binary format is not available in-app. Click 'Open' to view.]"
             
        self._render_text(content)
        self.btn_open.config(state="normal")
        self.btn_reveal.config(state="normal")

    def _render_text(self, content: str):
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")
        
        in_code_block = False
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                self.text_area.insert("end", f"{line}\n", "code_block")
                continue

            if stripped.startswith("# "): self.text_area.insert("end", f"{stripped[2:]}\n", "h1")
            elif stripped.startswith("## "): self.text_area.insert("end", f"{stripped[3:]}\n", "h2")
            elif stripped.startswith("- "): 
                self.text_area.insert("end", "  • ", "bold")
                self.text_area.insert("end", f"{stripped[2:]}\n", "bullet")
            else: self.text_area.insert("end", f"{line}\n", "normal")
                
        self.text_area.config(state="disabled")

    def _open_file(self):
        if not self.current_path or not os.path.exists(self.current_path): return
        if platform.system() == "Windows": os.startfile(self.current_path)
        elif platform.system() == "Darwin": subprocess.run(["open", self.current_path])
        else: subprocess.run(["xdg-open", self.current_path])

    def _reveal_in_explorer(self):
        if not self.current_path or not os.path.exists(self.current_path): return
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", os.path.normpath(self.current_path)])
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R", self.current_path])
        else:
            folder = os.path.dirname(self.current_path)
            subprocess.run(["xdg-open", folder])
