import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from src.ui.styles.theme import Theme

class ProjectExplorer(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, fg_color=Theme.BG_DARKER, corner_radius=0)
        
        # Header
        self.header = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER)
        self.header.pack(fill="x", padx=10, pady=10)
        tk.Label(self.header, text="Project Explorer", font=Theme.FONT_H3, 
                 fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKER).pack(side="left")
        
        self.btn_refresh = ctk.CTkButton(self.header, text="Refresh", width=80, 
                                        fg_color=Theme.BG_DARK, hover_color=Theme.ACCENT,
                                        command=self.refresh)
        self.btn_refresh.pack(side="right")

        # Treeview Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background=Theme.BG_DARKER, 
                        foreground=Theme.TEXT_MAIN, 
                        fieldbackground=Theme.BG_DARKER,
                        borderwidth=0,
                        rowheight=25)
        style.map("Treeview", background=[('selected', Theme.PRIMARY)])

        # Treeview
        self.tree = ttk.Treeview(self, selectmode="browse", style="Treeview", show="tree")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar (Standard ttk is fine if themed)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        
        # Setup Icons (Tags)
        self.tree.tag_configure("folder", font=Theme.FONT_BODY)
        self.tree.tag_configure("file", font=Theme.FONT_BODY)

        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        self.current_root = None
        self.on_file_selected: Optional[Callable[[str], None]] = None

    def load_project(self, root_path: str):
        """Populate the tree with files from root_path."""
        self.current_root = root_path
        self._populate_tree()

    def refresh(self):
        if self.current_root:
            self._populate_tree()

    def _populate_tree(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.current_root or not os.path.exists(self.current_root):
            return

        # Insert Root
        root_node = self.tree.insert("", "end", text=os.path.basename(self.current_root), open=True, tags=("folder",))
        self._process_directory(root_node, self.current_root)

    def _process_directory(self, parent_node, path):
        try:
            items = os.listdir(path)
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            
            for item in items:
                # Ignore hidden/system folders
                if item.startswith(".") or item in ["venv", "__pycache__", ".serapeum"]:
                    continue
                    
                abspath = os.path.join(path, item)
                if os.path.isdir(abspath):
                    node = self.tree.insert(parent_node, "end", text=item, open=False, values=[abspath], tags=("folder",))
                    # Lazy loading could be added here, but for now strict recursion likely fine for small projects
                    # Actually, to be safe, let's just do one level deep or use a dummy node for lazy load?
                    # For now, simplistic recursion
                    self._process_directory(node, abspath)
                else:
                    self.tree.insert(parent_node, "end", text=item, values=[abspath], tags=("file",))
        except PermissionError:
            pass

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        values = self.tree.item(item, "values")
        if values:
            abspath = values[0]
            if os.path.isfile(abspath) and self.on_file_selected:
                self.on_file_selected(abspath)
