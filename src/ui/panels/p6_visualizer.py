import logging
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import numpy as np
from datetime import datetime
from tkinter import messagebox

from src.ui.styles.theme import Theme
from src.application.api.fact_api import FactQueryAPI
from src.application.services.p6_interaction import resolve_pick_index, build_schedule_audit_text

logger = logging.getLogger(__name__)

class P6Visualizer(ctk.CTkFrame):
    """
    P6 Interactive Schedule Visualizer (Phase 5.5)
    Supports cross-linking Gantt bars to the Layer 4 Fact Engine.
    """
    def __init__(self, parent, db_manager):
        super().__init__(parent, fg_color=Theme.BG_DARKEST)
        self.db = db_manager
        self.fact_api = FactQueryAPI(db_manager) if db_manager else None
        
        # Tool Controls
        self.frame_ctrl = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER, corner_radius=12, border_width=1, border_color=Theme.BG_DARK)
        self.frame_ctrl.pack(fill="x", padx=20, pady=10)
        
        self.lbl_info = ctk.CTkLabel(self.frame_ctrl, text="Interactive Gantt | Click any bar to inspect Layer 4 Certified Facts", 
                                    font=Theme.FONT_BODY, text_color=Theme.TEXT_MUTED)
        self.lbl_info.pack(side="left", padx=20, pady=10)
        
        self.btn_load = ctk.CTkButton(self.frame_ctrl, text="Refresh Schedule", 
                                     fg_color=Theme.PRIMARY, hover_color=Theme.ACCENT,
                                     command=self.load_gantt)
        self.btn_load.pack(side="right", padx=10, pady=10)
        
        # Plot Canvas Area
        self.frame_canvas = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        self.frame_canvas.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.fig = None
        self.df_current = None

    def load_gantt(self):
        if not self.db: return
        
        query = """
        SELECT activity_id, code, name, start_date, finish_date, total_float, status_code
        FROM p6_activities 
        WHERE start_date IS NOT NULL AND finish_date IS NOT NULL 
        ORDER BY start_date ASC 
        LIMIT 40
        """
        try:
            rows = self.db.execute(query).fetchall()
            if not rows:
                self._show_empty_state()
                return

            # Process Data
            self.df_current = pd.DataFrame(rows, columns=["id", "code", "name", "start", "finish", "float", "status"])
            self.df_current['start'] = pd.to_datetime(self.df_current['start'])
            self.df_current['finish'] = pd.to_datetime(self.df_current['finish'])
            self.df_current['duration'] = (self.df_current['finish'] - self.df_current['start']).dt.total_seconds() / (24 * 3600)
            
            self._render_plot()
            
        except Exception as e:
            logger.error(f"Gantt Rendering Error: {e}")
            self._show_empty_state()

    def _render_plot(self):
        plt.style.use('dark_background')
        self.fig, ax = plt.subplots(figsize=(10, 6))
        self.fig.patch.set_facecolor(Theme.BG_DARKEST) 
        ax.set_facecolor(Theme.BG_DARKEST)
        
        df = self.df_current
        y_pos = np.arange(len(df))
        
        # Critical vs Normal distinction
        colors = [Theme.DANGER if f is not None and f <= 0 else Theme.PRIMARY for f in df['float']]
        
        # Render Bars with picker enabled
        bars = ax.barh(y_pos, df['duration'], left=df['start'], height=0.6, 
                       color=colors, edgecolor='white', linewidth=0.5, picker=True)
        self._bars = list(bars)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df['name'], fontsize=9, color=Theme.TEXT_MAIN)
        ax.invert_yaxis() # Top-down schedule
        
        # Grid and Labels
        ax.set_xlabel("Timeline", color=Theme.TEXT_MUTED)
        ax.grid(True, axis='x', linestyle='--', alpha=0.1, color='white')
        ax.tick_params(colors=Theme.TEXT_MUTED)
        for spine in ax.spines.values():
            spine.set_visible(False)

        plt.tight_layout()
        
        # 4. Integrate Callbacks
        self.fig.canvas.mpl_connect('pick_event', self._on_pick)
        
        # Clear and Embed
        for widget in self.frame_canvas.winfo_children():
            widget.destroy()
            
        canvas = FigureCanvasTkAgg(self.fig, master=self.frame_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _on_pick(self, event):
        """Handle pick event on bar to fetch linked facts without crashing on event shape differences."""
        if self.df_current is None or self.df_current.empty:
            return
        ind = resolve_pick_index(event, getattr(self, "_bars", []))
        if ind is None or ind < 0 or ind >= len(self.df_current):
            logger.debug("Gantt pick ignored because the selected index could not be resolved.")
            return

        row = self.df_current.iloc[ind]
        act_code = row['code']
        act_name = row['name']

        logger.info(f"Gantt Picked: {act_code} - {act_name}")

        fact_data = {"facts": []}
        if self.fact_api:
            try:
                fact_data = self.fact_api.get_certified_facts(
                    query_intent=f"Details for activity {act_code}",
                    project_id=self.db.project_id if hasattr(self.db, 'project_id') else None,
                    fact_types=["schedule.activity", "schedule.dates", "schedule.logic", "schedule.critical_path_membership"]
                )
            except Exception as e:
                logger.error(f"Fact Retrieval Failed for {act_code}: {e}")

        self._display_fact_audit(act_name, act_code, fact_data, row)

    def _display_fact_audit(self, name, code, fact_data, row_summary=None):
        """Show factual audit trail for picked activity."""
        audit_win = ctk.CTkToplevel(self)
        audit_win.title(f"Fact Audit: {code}")
        audit_win.geometry("500x600")
        audit_win.configure(fg_color=Theme.BG_DARKER)
        audit_win.after(100, lambda: audit_win.focus_get()) # Ensure focus

        lbl_h = ctk.CTkLabel(audit_win, text=f"Truth Engine Audit: {code}", font=Theme.FONT_H3, text_color=Theme.ACCENT)
        lbl_h.pack(pady=20, padx=20, anchor="w")

        text_area = ctk.CTkTextbox(audit_win, fg_color=Theme.BG_DARKEST, font=Theme.FONT_MONO, text_color=Theme.TEXT_MAIN)
        text_area.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        content = f"Activity: {name}\n"
        content += f"Identifier: {code}\n"
        content += "="*40 + "\n\n"
        
        facts = fact_data.get("facts", [])
        if not facts:
            content += "[NO CERTIFIED FACTS FOUND]\n"
            content += "Only CANDIDATE data exists. Run Human Certification to promote.\n"
        else:
            for f in facts:
                content += f"TYPE: {f['fact_type']}\n"
                content += f"  VALUE: {f['value']}\n"
                content += f"  STATUS: {f['status']}\n"
                content += f"  METHOD: {f['method_id']}\n"
                lineage = f.get('lineage', [])
                if lineage:
                    content += f"  SOURCE: {lineage[0].get('source_path', 'unknown')}\n"
                content += "\n"

        text_area.insert("0.0", content)
        text_area.configure(state="disabled")

    def _show_empty_state(self):
        for widget in self.frame_canvas.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.frame_canvas, text="No Schedule Data Found\n(Run extraction on .xer or .xml files)", 
                     font=Theme.FONT_H3, text_color=Theme.TEXT_MUTED).place(relx=0.5, rely=0.5, anchor="center")
