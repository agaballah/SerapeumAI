import customtkinter as ctk
from src.ui.styles.theme import Theme


class BasePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=Theme.BG_DARKEST, corner_radius=0)
        self.controller = controller
        self._page_closing = False
        self._page_after_ids: set[str] = set()

    def _wrap_safe_callback(self, callback):
        def _runner():
            if self._page_closing:
                return
            controller = self.controller
            if controller is not None and getattr(controller, '_is_closing', False):
                return
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            try:
                callback()
            except Exception:
                # Never allow a late callback to surface as Tk/bgerror spam.
                return
        return _runner

    def safe_ui_after(self, delay_ms: int, callback):
        if self._page_closing:
            return None
        if self.controller is not None and getattr(self.controller, '_is_closing', False):
            return None
        try:
            if not self.winfo_exists():
                return None
            after_id = self.after(delay_ms, self._wrap_safe_callback(callback))
            if after_id:
                self._page_after_ids.add(after_id)
            return after_id
        except Exception:
            return None

    def safe_ui_after_cancel(self, after_id):
        if not after_id:
            return
        try:
            self.after_cancel(after_id)
        except Exception:
            pass
        self._page_after_ids.discard(after_id)

    def on_show(self):
        """Called when this page is displayed."""
        pass

    def on_app_close(self):
        self._page_closing = True
        for after_id in list(self._page_after_ids):
            self.safe_ui_after_cancel(after_id)
