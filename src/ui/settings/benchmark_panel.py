# -*- coding: utf-8 -*-
"""
Benchmark Panel - UI for running and viewing model benchmarks
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging

logger = logging.getLogger(__name__)


class BenchmarkPanel(ttk.Frame):
    """
    UI for running and viewing model benchmarks.
    
    Features:
    - Task selection
    - Model selection (multi-select)
    - Test case input
    - Progress tracking
    - Results display
    """
    
    def __init__(self, parent, benchmark_service):
        """
        Initialize benchmark panel.
        
        Args:
            parent: Parent widget
            benchmark_service: BenchmarkService instance
        """
        super().__init__(parent)
        self.benchmark = benchmark_service
        self.running = False
        
        self._create_widgets()
        self._load_history()
    
    def _create_widgets(self):
        """Create UI widgets."""
        # Title
        title = ttk.Label(self, text="Model Benchmarking", font=('Arial', 12, 'bold'))
        title.pack(anchor='w', pady=(0, 10))
        
        # Configuration section
        config_frame = ttk.LabelFrame(self, text="Benchmark Configuration", padding=10)
        config_frame.pack(fill='x', pady=(0, 10))
        
        # Task selection
        task_row = ttk.Frame(config_frame)
        task_row.pack(fill='x', pady=5)
        
        ttk.Label(task_row, text="Task:", width=15).pack(side='left')
        self.task_combo = ttk.Combobox(task_row, values=[
            "vision_drawing",
            "vision_classification",
            "entity_extraction",
            "qa",
            "summarization",
            "creative_writing"
        ], state='readonly', width=25)
        self.task_combo.pack(side='left', padx=5)
        self.task_combo.current(3)  # Default to "qa"
        
        # Model selection
        model_row = ttk.Frame(config_frame)
        model_row.pack(fill='x', pady=5)
        
        ttk.Label(model_row, text="Models:", width=15).pack(side='left', anchor='n')
        
        model_list_frame = ttk.Frame(model_row)
        model_list_frame.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(model_list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.model_listbox = tk.Listbox(
            model_list_frame,
            selectmode='multiple',
            height=4,
            yscrollcommand=scrollbar.set
        )
        self.model_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.model_listbox.yview)
        
        # Populate with common models
        for model in ["granite-4-micro", "mistral-7b-instruct", "qwen2-vl-7b-instruct"]:
            self.model_listbox.insert('end', model)
        
        ttk.Button(model_row, text="Refresh", command=self._refresh_models).pack(side='left', padx=5)
        
        # Test cases
        test_frame = ttk.LabelFrame(config_frame, text="Test Cases (one per line: input | expected)", padding=5)
        test_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.test_cases_text = scrolledtext.ScrolledText(test_frame, height=6, wrap='word')
        self.test_cases_text.pack(fill='both', expand=True)
        
        # Default test cases
        self.test_cases_text.insert('1.0', """What is 2+2? | 4
Explain photosynthesis in one sentence | Plants convert light to energy
What is the capital of France? | Paris""")
        
        # Run button
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill='x', pady=(10, 0))
        
        self.run_btn = ttk.Button(btn_frame, text="▶ Run Benchmark", command=self._run_benchmark)
        self.run_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self._stop_benchmark, state='disabled')
        self.stop_btn.pack(side='left')
        
        # Progress section
        progress_frame = ttk.LabelFrame(self, text="Progress", padding=10)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x')
        
        # Results section
        results_frame = ttk.LabelFrame(self, text="Results", padding=10)
        results_frame.pack(fill='both', expand=True)
        
        # Results tree
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.results_tree = ttk.Treeview(
            tree_frame,
            columns=('model', 'quality', 'speed', 'duration', 'winner'),
            show='headings',
            yscrollcommand=scrollbar.set
        )
        self.results_tree.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.results_tree.yview)
        
        # Columns
        self.results_tree.heading('model', text='Model')
        self.results_tree.heading('quality', text='Quality')
        self.results_tree.heading('speed', text='Speed')
        self.results_tree.heading('duration', text='Avg Duration')
        self.results_tree.heading('winner', text='')
        
        self.results_tree.column('model', width=200)
        self.results_tree.column('quality', width=100)
        self.results_tree.column('speed', width=100)
        self.results_tree.column('duration', width=100)
        self.results_tree.column('winner', width=50)
        
        # Recommendation label
        self.recommendation_label = ttk.Label(results_frame, text="", foreground='blue', wraplength=500)
        self.recommendation_label.pack(anchor='w', pady=(10, 0))
    
    def _refresh_models(self):
        """Refresh model list from LM Studio."""
        try:
            if not self.benchmark.lms or not self.benchmark.lms.enabled:
                messagebox.showwarning("Not Connected", "LM Studio is not connected")
                return
            
            models = self.benchmark.lms.list_models()
            
            self.model_listbox.delete(0, 'end')
            for model in models:
                self.model_listbox.insert('end', model.get('name', 'unknown'))
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh models: {e}")
    
    def _parse_test_cases(self) -> list:
        """Parse test cases from text widget."""
        text = self.test_cases_text.get('1.0', 'end').strip()
        cases = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '|' in line:
                parts = line.split('|', 1)
                cases.append({
                    "input": parts[0].strip(),
                    "expected": parts[1].strip() if len(parts) > 1 else ""
                })
            else:
                cases.append({"input": line, "expected": ""})
        
        return cases
    
    def _run_benchmark(self):
        """Run benchmark in background thread."""
        # Validate inputs
        task = self.task_combo.get()
        if not task:
            messagebox.showwarning("Invalid Input", "Please select a task")
            return
        
        selected_indices = self.model_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Invalid Input", "Please select at least one model")
            return
        
        models = [self.model_listbox.get(i) for i in selected_indices]
        test_cases = self._parse_test_cases()
        
        if not test_cases:
            messagebox.showwarning("Invalid Input", "Please enter at least one test case")
            return
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.recommendation_label['text'] = ""
        
        # Update UI
        self.running = True
        self.run_btn['state'] = 'disabled'
        self.stop_btn['state'] = 'normal'
        self.progress_bar['value'] = 0
        
        # Run in thread
        def run():
            try:
                results = self.benchmark.run_benchmark(
                    task=task,
                    models=models,
                    test_cases=test_cases,
                    on_progress=self._update_progress
                )
                
                self.after(0, lambda: self._display_results(results))
                
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Benchmark failed: {e}"))
            finally:
                self.after(0, self._reset_ui)
        
        threading.Thread(target=run, daemon=True).start()
    
    def _stop_benchmark(self):
        """Stop running benchmark."""
        self.running = False
        self._reset_ui()
    
    def _update_progress(self, model: str, case_idx: int, total_cases: int):
        """Update progress display."""
        if not self.running:
            return
        
        percent = ((case_idx + 1) / total_cases) * 100
        
        self.after(0, lambda: self.progress_label.config(
            text=f"Testing {model}: {case_idx + 1}/{total_cases}"
        ))
        self.after(0, lambda: self.progress_bar.config(value=percent))
    
    def _display_results(self, results: dict):
        """Display benchmark results."""
        # Clear tree
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Add results
        for model, metrics in results["results"].items():
            if "error" in metrics:
                self.results_tree.insert('', 'end', values=(
                    model, "ERROR", "-", "-", ""
                ))
            else:
                winner_mark = "🏆" if model == results["winner"] else ""
                
                self.results_tree.insert('', 'end', values=(
                    model,
                    f"{metrics['avg_quality']:.1%}",
                    f"{metrics['avg_speed']:.1f} tok/s",
                    f"{metrics['avg_duration']:.2f}s",
                    winner_mark
                ))
        
        # Show recommendation
        self.recommendation_label['text'] = results["recommendation"]
        
        # Show completion message
        messagebox.showinfo("Benchmark Complete", results["recommendation"])
    
    def _reset_ui(self):
        """Reset UI after benchmark."""
        self.running = False
        self.run_btn['state'] = 'normal'
        self.stop_btn['state'] = 'disabled'
        self.progress_label['text'] = "Ready"
        self.progress_bar['value'] = 0
    
    def _load_history(self):
        """Load benchmark history (optional)."""
        # Could display historical results here
        pass
