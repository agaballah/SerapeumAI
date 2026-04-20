# -*- coding: utf-8 -*-
"""
Model Manager Panel - UI for managing LM Studio models
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

logger = logging.getLogger(__name__)


class ModelManagerPanel(ttk.Frame):
    """
    Model management UI for LM Studio integration.
    
    Features:
    - List local models with status
    - Download models from Hugging Face
    - Load/unload models
    - Real-time VRAM monitoring
    """
    
    def __init__(self, parent, lm_studio_service):
        """
        Initialize model manager panel.
        
        Args:
            parent: Parent widget
            lm_studio_service: LMStudioService instance
        """
        super().__init__(parent)
        self.lms = lm_studio_service
        self.download_jobs = {}  # download_id -> progress
        
        self._create_widgets()
        self._refresh_models()
    
    def _create_widgets(self):
        """Create UI widgets."""
        # Title
        title = ttk.Label(self, text="Model Manager", font=('Arial', 12, 'bold'))
        title.pack(anchor='w', pady=(0, 10))
        
        # Local models section
        local_frame = ttk.LabelFrame(self, text="Local Models", padding=10)
        local_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Toolbar
        toolbar = ttk.Frame(local_frame)
        toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar, text="Refresh", command=self._refresh_models).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Unload All", command=self._unload_all).pack(side='left')
        
        # Model tree
        tree_frame = ttk.Frame(local_frame)
        tree_frame.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Treeview
        self.model_tree = ttk.Treeview(
            tree_frame,
            columns=('status', 'size', 'vram', 'speed'),
            show='tree headings',
            yscrollcommand=scrollbar.set
        )
        self.model_tree.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.model_tree.yview)
        
        # Columns
        self.model_tree.heading('#0', text='Model')
        self.model_tree.heading('status', text='Status')
        self.model_tree.heading('size', text='Size')
        self.model_tree.heading('vram', text='VRAM')
        self.model_tree.heading('speed', text='Speed')
        
        self.model_tree.column('#0', width=250)
        self.model_tree.column('status', width=80)
        self.model_tree.column('size', width=80)
        self.model_tree.column('vram', width=100)
        self.model_tree.column('speed', width=100)
        
        # Context menu
        self.model_tree.bind('<Button-3>', self._show_context_menu)
        self.model_tree.bind('<Double-1>', self._on_model_double_click)
        
        # Download section
        download_frame = ttk.LabelFrame(self, text="Download Models", padding=10)
        download_frame.pack(fill='x', pady=(0, 10))
        
        # Popular models
        ttk.Label(download_frame, text="Popular Models:").pack(anchor='w', pady=(0, 5))
        
        self.popular_models = [
            ("IBM Granite 4 Micro", "ibm/granite-4-micro"),
            ("Mistral 7B Instruct", "TheBloke/Mistral-7B-Instruct-v0.2-GGUF", "mistral-7b-instruct-v0.2.Q4_K_M.gguf"),
            ("Qwen2-VL 7B", "Qwen/Qwen2-VL-7B-Instruct-GGUF", "qwen2-vl-7b-instruct-q4_k_m.gguf"),
        ]
        
        for display_name, repo, *file in self.popular_models:
            btn_frame = ttk.Frame(download_frame)
            btn_frame.pack(fill='x', pady=2)
            
            ttk.Label(btn_frame, text=f"- {display_name}", width=30).pack(side='left')
            ttk.Button(
                btn_frame,
                text="Download",
                command=lambda r=repo, f=file[0] if file else None: self._download_model(r, f)
            ).pack(side='left', padx=5)
        
        # Custom download
        custom_frame = ttk.Frame(download_frame)
        custom_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(custom_frame, text="Custom:").pack(side='left', padx=(0, 5))
        self.repo_entry = ttk.Entry(custom_frame, width=40)
        self.repo_entry.pack(side='left', padx=5)
        self.repo_entry.insert(0, "owner/repo")
        
        ttk.Button(custom_frame, text="Download", command=self._download_custom).pack(side='left')
        
        # Download progress
        self.progress_frame = ttk.Frame(download_frame)
        self.progress_frame.pack(fill='x', pady=(10, 0))
        
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(anchor='w')
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', pady=5)
        
        # VRAM monitor
        from src.ui.widgets.vram_monitor import VRAMMonitor
        vram_frame = ttk.LabelFrame(self, text="System Status", padding=10)
        vram_frame.pack(fill='x')
        
        self.vram_monitor = VRAMMonitor(vram_frame, self.lms, compact=False)
        self.vram_monitor.pack(fill='x')
    
    def _refresh_models(self):
        """Refresh model list."""
        try:
            # Clear tree
            for item in self.model_tree.get_children():
                self.model_tree.delete(item)
            
            if not self.lms or not self.lms.enabled:
                self.model_tree.insert('', 'end', text='LM Studio not connected', values=('', '', '', ''))
                return
            
            # Get models
            models = self.lms.list_models()
            status = self.lms.get_status()
            loaded_model = status.get('model', '') if status.get('loaded') else None
            
            for model in models:
                model_name = model.get('name', 'unknown')
                model_size = model.get('size', 'unknown')
                
                # Status
                if model_name == loaded_model:
                    status_text = 'Loaded'
                    vram_text = f"{status.get('vram_mb', 0):,} MB"
                    speed_text = f"{status.get('tokens_per_sec', 0):.1f} tok/s"
                else:
                    status_text = 'Ready'
                    vram_text = '-'
                    speed_text = '-'
                
                self.model_tree.insert(
                    '', 'end',
                    text=model_name,
                    values=(status_text, model_size, vram_text, speed_text),
                    tags=('loaded' if model_name == loaded_model else 'unloaded',)
                )
            
            # Configure tags
            self.model_tree.tag_configure('loaded', foreground='green')
            self.model_tree.tag_configure('unloaded', foreground='black')
            
        except Exception as e:
            logger.error(f"[ModelManager] Refresh failed: {e}")
            messagebox.showerror("Error", f"Failed to refresh models: {e}")
    
    def _show_context_menu(self, event):
        """Show context menu on right-click."""
        item = self.model_tree.identify_row(event.y)
        if not item:
            return
        
        self.model_tree.selection_set(item)
        model_name = self.model_tree.item(item, 'text')
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Load Model", command=lambda: self._load_model(model_name))
        menu.add_command(label="Unload Model", command=lambda: self._unload_model(model_name))
        menu.add_separator()
        menu.add_command(label="Delete Model", command=lambda: self._delete_model(model_name))
        
        menu.post(event.x_root, event.y_root)
    
    def _on_model_double_click(self, event):
        """Handle double-click on model."""
        item = self.model_tree.identify_row(event.y)
        if not item:
            return
        
        model_name = self.model_tree.item(item, 'text')
        self._load_model(model_name)
    
    def _load_model(self, model_name):
        """Load model into VRAM."""
        try:
            logger.info(f"[ModelManager] Loading model: {model_name}")
            
            def load():
                try:
                    self.lms.load_model(model_name)
                    self.after(0, self._refresh_models)
                    self.after(0, lambda: messagebox.showinfo("Success", f"Model loaded: {model_name}"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to load model: {e}"))
            
            threading.Thread(target=load, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {e}")
    
    def _unload_model(self, model_name):
        """Unload model from VRAM."""
        try:
            logger.info(f"[ModelManager] Unloading model: {model_name}")
            self.lms.unload_model()
            self._refresh_models()
            messagebox.showinfo("Success", "Model unloaded")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unload model: {e}")
    
    def _unload_all(self):
        """Unload all models."""
        try:
            self.lms.unload_model()
            self._refresh_models()
            messagebox.showinfo("Success", "All models unloaded")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unload models: {e}")
    
    def _delete_model(self, model_name):
        """Delete model (not implemented in LM Studio API)."""
        messagebox.showinfo("Not Implemented", "Model deletion must be done through LM Studio UI")
    
    def _download_model(self, repo, file=None):
        """Download model from Hugging Face."""
        try:
            logger.info(f"[ModelManager] Downloading: {repo}")
            
            self.progress_label['text'] = f"Downloading {repo}..."
            self.progress_bar['value'] = 0
            
            def download():
                try:
                    def on_progress(status):
                        percent = status.get('percent', 0)
                        self.after(0, lambda: self.progress_bar.config(value=percent))
                        self.after(0, lambda: self.progress_label.config(
                            text=f"Downloading {repo}: {percent:.0f}%"
                        ))
                    
                    if file:
                        self.lms.download_model(repo, file, on_progress=on_progress)
                    else:
                        # Download default file (LM Studio will prompt)
                        self.lms.download_model(repo, "", on_progress=on_progress)
                    
                    self.after(0, lambda: self.progress_label.config(text="Download complete!"))
                    self.after(0, self._refresh_models)
                    self.after(0, lambda: messagebox.showinfo("Success", f"Downloaded: {repo}"))
                except Exception as e:
                    self.after(0, lambda: self.progress_label.config(text=f"Download failed: {e}"))
                    self.after(0, lambda: messagebox.showerror("Error", f"Download failed: {e}"))
            
            threading.Thread(target=download, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start download: {e}")
    
    def _download_custom(self):
        """Download custom model."""
        repo = self.repo_entry.get().strip()
        if not repo or repo == "owner/repo":
            messagebox.showwarning("Invalid Input", "Please enter a valid Hugging Face repo")
            return
        
        self._download_model(repo)
