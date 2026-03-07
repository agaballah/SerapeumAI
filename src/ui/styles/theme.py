# -*- coding: utf-8 -*-

class Theme:
    # ---------------------------------------------------------
    # Core Palette (Noir / Professional Dark)
    # ---------------------------------------------------------
    BG_DARKEST = "#121212"    # Main app background (Now slightly lighter for better HC compatibility)
    BG_DARKER  = "#1A1A1A"    # Sidebars / Cards
    BG_DARK    = "#2D2D2D"    # Hovers / Accents
    
    PRIMARY    = "#2563EB"    # Blue 600
    ACCENT     = "#3B82F6"    # Blue 500
    SUCCESS    = "#22C55E"    # Green 500 (Cleaner)
    WARNING    = "#EAB308"    # Yellow 500
    DANGER     = "#EF4444"    # Red 500
    
    TEXT_MAIN      = "#FFFFFF"
    TEXT_MUTED     = "#A1A1AA"
    TEXT_HIGHLIGHT = "#3B82F6"

    # UI Element specific
    DANGER_RED     = "#991B1B"
    DANGER_DARK    = "#7F1D1D"
    SURFACE        = "#2B2B2B"
    BORDER_DIM     = "#3A3A3A"
    TEXT_OFFWHITE  = "#DCE4EE"
    
    # ---------------------------------------------------------
    # Fonts (Standard safe fonts to avoid fallback glitches)
    # ---------------------------------------------------------
    FONT_H1 = ("Segoe UI", 28, "bold")
    FONT_H2 = ("Segoe UI", 20, "bold")
    FONT_H3 = ("Segoe UI", 16, "bold")
    FONT_BODY = ("Segoe UI", 12)
    FONT_MONO = ("Consolas", 11)
    
    @staticmethod
    def apply_to_all():
        """Ensure global CTK settings are consistent."""
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        # Repeating to override any dynamic system detection glitches
        ctk.set_appearance_mode("dark")
