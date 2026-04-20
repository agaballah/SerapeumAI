
import customtkinter as ctk
import pandas as pd
from tkinter import filedialog, messagebox

class SmartImportWizard(ctk.CTkToplevel):
    def __init__(self, parent, on_import_callback):
        super().__init__(parent)
        self.title("Smart Import Wizard")
        self.geometry("800x600")
        
        self.on_import_callback = on_import_callback
        self.selected_file = None
        self.df_preview = None
        self.header_row_idx = 0
        
        # UI
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 1. File Selection
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_browse = ctk.CTkButton(self.frame_top, text="Browse Excel...", command=self.browse_file)
        self.btn_browse.pack(side="left", padx=10, pady=10)
        
        self.lbl_file = ctk.CTkLabel(self.frame_top, text="No file selected")
        self.lbl_file.pack(side="left", padx=10)
        
        # 2. Preview Grid (using Textbox for simplicity vs CTkTable)
        self.txt_preview = ctk.CTkTextbox(self, wrap="none")
        self.txt_preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # 3. Controls
        self.frame_controls = ctk.CTkFrame(self)
        self.frame_controls.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        self.lbl_header = ctk.CTkLabel(self.frame_controls, text="Header Row:")
        self.lbl_header.pack(side="left", padx=10)
        
        self.spin_header = ctk.CTkEntry(self.frame_controls, width=50)
        self.spin_header.insert(0, "0")
        self.spin_header.pack(side="left", padx=5)
        
        self.btn_preview_header = ctk.CTkButton(self.frame_controls, text="Update Preview", command=self.update_preview)
        self.btn_preview_header.pack(side="left", padx=10)
        
        self.check_global = ctk.CTkCheckBox(self.frame_controls, text="Global Engineering Standard")
        self.check_global.pack(side="left", padx=20)
        
        self.btn_import = ctk.CTkButton(self.frame_controls, text="Run Ingestion", command=self.run_import, state="disabled")
        self.btn_import.pack(side="right", padx=10, pady=10)

    def browse_file(self):
        import os
        filename = filedialog.askopenfilename(filetypes=[
            ("Engineering Documents", "*.xlsx *.xls *.pdf *.ifc"),
            ("Excel Files", "*.xlsx *.xls"),
            ("Project PDF", "*.pdf"),
            ("All Files", "*.*")
        ])
        if filename:
            self.selected_file = filename
            self.lbl_file.configure(text=filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in ('.xlsx', '.xls'):
                self.load_preview()
            else:
                self.update_info_display(f"Engineering Standard: {os.path.basename(filename)}\nReady for direct ingestion.")
                self.btn_import.configure(state="normal")
            
    def load_preview(self):
        try:
            # Load first 20 rows
            self.df_preview = pd.read_excel(self.selected_file, nrows=20, header=None)
            self.update_info_display(self.df_preview.to_string())
            self.btn_import.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")

    def update_preview(self):
        try:
            bg_row = int(self.spin_header.get())
            self.header_row_idx = bg_row
            # Reload with header
            df = pd.read_excel(self.selected_file, nrows=20, header=bg_row)
            self.update_info_display(f"--- Header Row: {bg_row} ---\nColumns: {list(df.columns)}\n\n" + df.to_string())
        except ValueError:
            pass

    def update_info_display(self, text):
        self.txt_preview.delete("0.0", "end")
        self.txt_preview.insert("0.0", text)
        
    def run_import(self):
        if self.selected_file:
            is_global = bool(self.check_global.get())
            self.on_import_callback(self.selected_file, header_row=self.header_row_idx, is_global=is_global)
            self.destroy()
