
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime

class P6Visualizer(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        
        # UI Controls
        self.frame_ctrl = ctk.CTkFrame(self)
        self.frame_ctrl.pack(fill="x", padx=10, pady=5)
        
        self.btn_load = ctk.CTkButton(self.frame_ctrl, text="Load Gantt", command=self.load_gantt)
        self.btn_load.pack(side="left", padx=10)
        
        # Canvas Area
        self.frame_canvas = ctk.CTkFrame(self)
        self.frame_canvas.pack(fill="both", expand=True, padx=10, pady=5)
        
    def load_gantt(self):
        # 1. Fetch P6 Activities
        if not self.db: return
        
        query = """
        SELECT activity_id, name, start_date, finish_date 
        FROM p6_activities 
        WHERE start_date IS NOT NULL AND finish_date IS NOT NULL 
        ORDER BY start_date ASC 
        LIMIT 50
        """
        rows = self.db.execute(query).fetchall()
        
        if not rows:
            self._show_empty_state()
            return

        # 2. Process Data
        try:
            df = pd.DataFrame(rows, columns=["id", "name", "start", "finish"])
            df['start'] = pd.to_datetime(df['start'])
            df['finish'] = pd.to_datetime(df['finish'])
            df['duration'] = (df['finish'] - df['start']).dt.days
            
            # 3. Plot (Dark Mode)
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#1e1e1e') # Exact match for CTk background
            ax.set_facecolor('#1e1e1e')
            
            y_pos = range(len(df))
            ax.barh(y_pos, df['duration'], left=df['start'], height=0.5, color='#1f538d', edgecolor='white')
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df['name'], fontsize=8, color='white')
            ax.set_xlabel("Date", color='white')
            ax.set_title(f"Schedule Overview (Top {len(df)} Activities)", color='white')
            ax.tick_params(colors='white')
            ax.grid(True, axis='x', linestyle='--', alpha=0.3, color='gray')
            
            # Format Date Axis
            fig.autofmt_xdate()
            plt.tight_layout()
            
            # 4. Embed in Tk
            for widget in self.frame_canvas.winfo_children():
                widget.destroy()
                
            canvas = FigureCanvasTkAgg(fig, master=self.frame_canvas)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            print(f"P6 Plot Error: {e}")
            self._show_empty_state()

    def _show_empty_state(self):
        for widget in self.frame_canvas.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.frame_canvas, text="No Schedule Data Found\n(Ingest .xer or .xml files)", 
                     font=("Arial", 16), text_color="gray").place(relx=0.5, rely=0.5, anchor="center")
