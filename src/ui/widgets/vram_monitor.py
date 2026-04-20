# -*- coding: utf-8 -*-
"""
VRAM Monitor Widget - Real-time VRAM usage display
"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)


class VRAMMonitor(ttk.Frame):
    """
    Real-time VRAM usage monitor with color-coded progress bar.
    
    Colors:
    - Green: < 60% usage
    - Yellow: 60-85% usage
    - Red: >= 85% usage
    """
    
    def __init__(self, parent, lm_studio_service, compact=False):
        """
        Initialize VRAM monitor.
        
        Args:
            parent: Parent widget
            lm_studio_service: LMStudioService instance
            compact: If True, show minimal UI for status bar
        """
        super().__init__(parent)
        self.lms = lm_studio_service
        self.compact = compact
        self.max_vram = 8192  # Default, will be updated
        
        self._create_widgets()
        self._start_monitoring()
    
    def _create_widgets(self):
        """Create UI widgets."""
        if self.compact:
            # Compact mode: just progress bar + label
            self.progress = ttk.Progressbar(
                self,
                mode='determinate',
                length=100
            )
            self.progress.pack(side='left', padx=5)
            
            self.label = ttk.Label(self, text="VRAM: 0 MB")
            self.label.pack(side='left')
        else:
            # Full mode: title + progress + detailed label
            title = ttk.Label(self, text="VRAM Usage", font=('Arial', 10, 'bold'))
            title.pack(anchor='w', pady=(0, 5))
            
            self.progress = ttk.Progressbar(
                self,
                mode='determinate',
                length=300
            )
            self.progress.pack(fill='x', pady=5)
            
            self.label = ttk.Label(self, text="VRAM: 0 / 8,192 MB (0%)")
            self.label.pack(anchor='w')
            
            self.model_label = ttk.Label(self, text="No model loaded", foreground='gray')
            self.model_label.pack(anchor='w', pady=(5, 0))
    
    def _start_monitoring(self):
        """Start periodic VRAM monitoring."""
        self._update_vram()
    
    def _update_vram(self):
        """Update VRAM display."""
        try:
            if not self.lms or not self.lms.enabled:
                self._set_unavailable()
                self.after(5000, self._update_vram)
                return
            
            status = self.lms.get_status()
            
            vram_used = status.get('vram_mb', 0)
            vram_total = status.get('vram_total_mb', self.max_vram)
            model_loaded = status.get('loaded', False)
            model_name = status.get('model', 'unknown')
            
            # Update max VRAM if provided
            if vram_total > 0:
                self.max_vram = vram_total
            
            # Calculate percentage
            percent = (vram_used / self.max_vram * 100) if self.max_vram > 0 else 0
            
            # Update progress bar
            self.progress['value'] = percent
            
            # Update color based on usage
            if percent < 60:
                style_name = 'green.Horizontal.TProgressbar'
            elif percent < 85:
                style_name = 'yellow.Horizontal.TProgressbar'
            else:
                style_name = 'red.Horizontal.TProgressbar'
            
            self.progress['style'] = style_name
            
            # Update labels
            if self.compact:
                self.label['text'] = f"VRAM: {vram_used:,} MB"
            else:
                self.label['text'] = f"VRAM: {vram_used:,} / {self.max_vram:,} MB ({percent:.0f}%)"
                
                if model_loaded:
                    self.model_label['text'] = f"Model: {model_name}"
                    self.model_label['foreground'] = 'black'
                else:
                    self.model_label['text'] = "No model loaded"
                    self.model_label['foreground'] = 'gray'
            
            # Tooltip
            tooltip_text = f"VRAM: {vram_used:,} MB / {self.max_vram:,} MB\n"
            if model_loaded:
                tooltip_text += f"Model: {model_name}\n"
                tooltip_text += f"Speed: {status.get('tokens_per_sec', 0):.1f} tok/s"
            else:
                tooltip_text += "No model loaded"
            
            self._set_tooltip(tooltip_text)
            
        except Exception as e:
            logger.warning(f"[VRAMMonitor] Update failed: {e}")
            self._set_unavailable()
        
        # Schedule next update (every 2 seconds)
        self.after(2000, self._update_vram)
    
    def _set_unavailable(self):
        """Set UI to unavailable state."""
        self.progress['value'] = 0
        if self.compact:
            self.label['text'] = "VRAM: N/A"
        else:
            self.label['text'] = "VRAM: Unavailable"
            self.model_label['text'] = "LM Studio not connected"
            self.model_label['foreground'] = 'red'
    
    def _set_tooltip(self, text):
        """Set tooltip text (simple implementation)."""
        # Note: Full tooltip requires additional library or custom implementation
        # For now, just store it as an attribute
        self.tooltip_text = text
    
    def stop_monitoring(self):
        """Stop VRAM monitoring (call on widget destroy)."""
        # Cancel any pending after() calls
        pass


def configure_progressbar_styles():
    """Configure custom progressbar styles with colors."""
    style = ttk.Style()
    
    # Green style
    style.configure(
        'green.Horizontal.TProgressbar',
        troughcolor='#e0e0e0',
        background='#4caf50'
    )
    
    # Yellow style
    style.configure(
        'yellow.Horizontal.TProgressbar',
        troughcolor='#e0e0e0',
        background='#ff9800'
    )
    
    # Red style
    style.configure(
        'red.Horizontal.TProgressbar',
        troughcolor='#e0e0e0',
        background='#f44336'
    )
