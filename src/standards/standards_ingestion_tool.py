# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ahmed Gaballa
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
standards_ingestion_tool.py — Bulk standards ingestion UI
---------------------------------------------------------

Standalone tool for importing standards/codes into the global database.

Features:
- Browse and select multiple files
- Auto-classify with StandardsClassifier
- Preview and confirm/override classifications
- Batch processing with progress bar
- Launch from main menu: Tools → Ingest Standards
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *  # noqa: F403
except ImportError:
    import tkinter as tk
    from tkinter import ttk


class StandardsIngestionTool(ttk.Frame):
    """UI for bulk standards ingestion."""
    
    def __init__(self, master, *, db, llm=None):
        super().__init__(master)
        self.db = db
        self.llm = llm
        self.selected_files: List[Dict[str, Any]] = []
        
        self.pack(fill="both", expand=True)
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the UI layout."""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(
            title_frame,
            text="📚 Standards Ingestion Tool",
            font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        
        # Instructions
        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Label(
            info_frame,
            text="Import building codes, standards, and regulations into the global database for reuse across all projects.",
            wraplength=600,
            font=("Segoe UI", 9)
        ).pack(anchor="w")
        
        # Buttons bar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="📁 Browse Files",
            command=self._browse_files,
            bootstyle="primary"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="🔍 Classify All",
            command=self._classify_all,
            bootstyle="info"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="✅ Import Selected",
            command=self._import_selected,
            bootstyle="success"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="❌ Clear All",
            command=self._clear_all,
            bootstyle="danger-outline"
        ).pack(side="left")
        
        # File list with classification results
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Create Treeview
        columns = ("filename", "category", "confidence", "status")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )
        
        self.tree.heading("filename", text="File Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("confidence", text="Confidence")
        self.tree.heading("status", text="Status")
        
        self.tree.column("filename", width=300)
        self.tree.column("category", width=150)
        self.tree.column("confidence", width=100)
        self.tree.column("status", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Browse files to get started.")
        status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            foreground="gray"
        )
        status_label.pack(fill="x", padx=10, pady=(0, 10))
    
    def _browse_files(self):
        """Browse and select files to import."""
        filetypes = [
            ("All Supported", "*.pdf *.docx *.xlsx"),
            ("PDF Files", "*.pdf"),
            ("Word Documents", "*.docx"),
            ("Excel Files", "*.xlsx"),
            ("All Files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="Select Standards Files",
            filetypes=filetypes
        )
        
        if files:
            for file_path in files:
                # Add to list if not already present
                if not any(f['path'] == file_path for f in self.selected_files):
                    file_data = {
                        'path': file_path,
                        'filename': os.path.basename(file_path),
                        'category': 'Not classified',
                        'confidence': 0.0,
                        'is_standard': False,
                        'status': 'Pending'
                    }
                    self.selected_files.append(file_data)
                    
                    # Add to tree
                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            file_data['filename'],
                            file_data['category'],
                            f"{file_data['confidence']:.0%}",
                            file_data['status']
                        )
                    )
            
            self.status_var.set(f"Added {len(files)} file(s). Click 'Classify All' to detect standards.")
    
    def _classify_all(self):
        """Classify all files using StandardsClassifier."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please browse and select files first.")
            return
        
        try:
            from src.standards.standards_classifier import StandardsClassifier
            
            classifier = StandardsClassifier(llm=self.llm)
            
            self.status_var.set("Classifying files...")
            self.update()
            
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Classify each file
            for i, file_data in enumerate(self.selected_files):
                result = classifier.classify(file_data['path'], use_llm=False)
                
                file_data['is_standard'] = result['is_standard']
                file_data['category'] = result['category']
                file_data['confidence'] = result['confidence']
                file_data['status'] = "✓ Standard" if result['is_standard'] else "⚠ Project Doc"
                
                # Add to tree
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        file_data['filename'],
                        file_data['category'],
                        f"{file_data['confidence']:.0%}",
                        file_data['status']
                    )
                )
            
            standards_count = sum(1 for f in self.selected_files if f['is_standard'])
            self.status_var.set(
                f"Classification complete. {standards_count}/{len(self.selected_files)} detected as standards."
            )
            
        except Exception as e:
            messagebox.showerror("Classification Error", str(e))
            self.status_var.set(f"Error: {str(e)}")
    
    def _import_selected(self):
        """Import selected standards into database."""
        standards = [f for f in self.selected_files if f['is_standard']]
        
        if not standards:
            messagebox.showwarning(
                "No Standards",
                "No files were classified as standards. Run 'Classify All' first."
            )
            return
        
        response = messagebox.askyesno(
            "Confirm Import",
            f"Import {len(standards)} standard(s) into the global database?\n\n"
            "This will make them available for compliance checking across all projects."
        )
        
        if not response:
            return
        
        try:
            # Import each standard
            from src.document_processing.generic_processor import GenericProcessor
            
            processor = GenericProcessor()
            imported = 0
            
            for std in standards:
                try:
                    # Process the file
                    result = processor.process(
                        abs_path=std['path'],
                        rel_path=std['filename'],
                        export_root=os.path.join(os.path.dirname(std['path']), ".serapeum", "exports")
                    )
                    
                    # Save to standards database
                    # TODO: Implement standards DB save method
                    # For now, save to regular DB with special project_id
                    self.db.upsert_document(
                        project_id="__STANDARDS__",
                        doc_id=result['doc_id'],
                        file_name=std['filename'],
                        file_path=std['path'],
                        payload=result
                    )
                    
                    std['status'] = "✅ Imported"
                    imported += 1
                    
                except Exception as e:
                    std['status'] = f"❌ Error: {str(e)[:20]}"
            
            # Refresh tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            for file_data in self.selected_files:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        file_data['filename'],
                        file_data['category'],
                        f"{file_data['confidence']:.0%}",
                        file_data['status']
                    )
                )
            
            messagebox.showinfo(
                "Import Complete",
                f"Successfully imported {imported}/{len(standards)} standard(s)."
            )
            self.status_var.set(f"Import complete. {imported} standard(s) added to database.")
            
        except Exception as e:
            messagebox.showerror("Import Error", str(e))
            self.status_var.set(f"Error: {str(e)}")
    
    def _clear_all(self):
        """Clear all files from the list."""
        if self.selected_files:
            response = messagebox.askyesno(
                "Clear All",
                f"Remove all {len(self.selected_files)} file(s) from the list?"
            )
            if response:
                self.selected_files.clear()
                for item in self.tree.get_children():
                    self.tree.delete(item)
                self.status_var.set("Cleared. Ready for new files.")


def launch_standards_tool(db, llm=None):
    """Launch the standards ingestion tool in a new window."""
    root = tk.Tk()
    root.title("Standards Ingestion Tool - Serapeum AECO")
    root.geometry("800x600")
    
    # Apply theme if available
    try:
        import ttkbootstrap as ttk
        _style = ttk.Style("darkly")
    except Exception:
        pass
    
    StandardsIngestionTool(root, db=db, llm=llm)
    root.mainloop()


if __name__ == "__main__":
    # For standalone testing
    print("Standards Ingestion Tool")
    print("This tool should be launched from the main application.")
    print("\nUsage:")
    print("  from src.standards.standards_ingestion_tool import launch_standards_tool")
    print("  launch_standards_tool(db, llm)")
