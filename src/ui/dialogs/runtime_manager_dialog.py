import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from src.infra.services.runtime_platform_read_model import RuntimePlatformReadModelService
from src.infra.services.runtime_provider_discovery import PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY
from src.infra.services.runtime_provider_selection import RuntimeProviderSelectionService
from src.infra.services.runtime_setup_service import (
    STATUS_EMBEDDING_RUNTIME_NOT_READY,
    LocalRuntimeSetupService,
)
from src.ui.presenters.runtime_manager_presenter import present_runtime_manager_selection
from src.ui.styles.theme import Theme

logger = logging.getLogger(__name__)


class RuntimeManagerDialog(ctk.CTkToplevel):
    NO_MODELS_LABEL = "No local models listed"

    def __init__(self, parent, controller, runtime_service: LocalRuntimeSetupService):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.runtime_service = runtime_service
        self.runtime_platform_read_model_service = getattr(
            controller,
            "runtime_platform_read_model_service",
            RuntimePlatformReadModelService(config=getattr(runtime_service, "config", None)),
        )
        self.selection_service = RuntimeProviderSelectionService(runtime_service.config)
        self.title("Local Runtime Manager")
        self.geometry("1100x820")
        self.configure(fg_color=Theme.BG_DARKEST)
        self.transient(parent)
        self.grab_set()
        self._is_closing = False
        self._after_ids: set[str] = set()
        self.protocol("WM_DELETE_WINDOW", self.safe_close)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_ui()
        self._safe_after(50, self.refresh_inventory)

    def _wrap_safe_callback(self, callback):
        def _runner():
            if self._is_closing:
                return
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            try:
                callback()
            except Exception:
                return
        return _runner

    def _safe_after(self, delay_ms: int, callback):
        if self._is_closing:
            return None
        try:
            if not self.winfo_exists():
                return None
            after_id = self.after(delay_ms, self._wrap_safe_callback(callback))
            if after_id:
                self._after_ids.add(after_id)
            return after_id
        except Exception:
            return None

    def safe_close(self):
        self._is_closing = True
        for after_id in list(self._after_ids):
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
            self._after_ids.discard(after_id)
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            logger.debug("Runtime manager dialog destroy failed.", exc_info=True)

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Local Runtime Manager",
            font=Theme.FONT_H2,
            fg=Theme.TEXT_MAIN,
            bg=Theme.BG_DARKEST,
        ).grid(row=0, column=0, sticky="w")
        self.lbl_status = tk.Label(
            header,
            text="Checking runtime state...",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_DARKEST,
            justify="left",
        )
        self.lbl_status.grid(row=1, column=0, sticky="w", pady=(6, 0))

        controls = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER)
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        for col in range(6):
            controls.grid_columnconfigure(col, weight=1)

        self.btn_refresh = ctk.CTkButton(controls, text="Re-check Runtime", command=self.refresh_inventory)
        self.btn_refresh.grid(row=0, column=0, padx=10, pady=12, sticky="ew")
        self.btn_start_server = ctk.CTkButton(controls, text="Start Server", command=lambda: self._run_async(self.runtime_service.start_server))
        self.btn_start_server.grid(row=0, column=1, padx=10, pady=12, sticky="ew")
        self.btn_prepare_embedding = ctk.CTkButton(controls, text="Prepare Embedding Runtime", command=lambda: self._run_async(self.runtime_service.prepare_embedding_runtime))
        self.btn_prepare_embedding.grid(row=0, column=2, padx=10, pady=12, sticky="ew")
        self.btn_load_analysis = ctk.CTkButton(controls, text="Load Analysis Model", command=lambda: self._run_async(lambda on_status=None: self.runtime_service.load_model_for_role("analysis", on_status=on_status)))
        self.btn_load_analysis.grid(row=0, column=3, padx=10, pady=12, sticky="ew")
        self.btn_load_chat = ctk.CTkButton(controls, text="Load Chat Model", command=lambda: self._run_async(lambda on_status=None: self.runtime_service.load_model_for_role("chat", on_status=on_status)))
        self.btn_load_chat.grid(row=0, column=4, padx=10, pady=12, sticky="ew")
        self.btn_unload = ctk.CTkButton(controls, text="Unload Session Models", fg_color=Theme.BG_DARK, hover_color=Theme.ACCENT, command=lambda: self._run_async(self.runtime_service.unload_session_models))
        self.btn_unload.grid(row=0, column=5, padx=10, pady=12, sticky="ew")

        selection = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER)
        selection.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        for col in range(5):
            selection.grid_columnconfigure(col, weight=1)

        tk.Label(selection, text="Provider", font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        tk.Label(selection, text="Provider mode", font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER).grid(row=0, column=1, sticky="w", padx=12, pady=(12, 4))
        tk.Label(selection, text="Chat model", font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER).grid(row=0, column=2, sticky="w", padx=12, pady=(12, 4))
        tk.Label(selection, text="Analysis model", font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER).grid(row=0, column=3, sticky="w", padx=12, pady=(12, 4))

        self.combo_provider = ctk.CTkComboBox(selection, values=["local_review_only"], state="readonly")
        self.combo_provider.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.combo_provider_mode = ctk.CTkComboBox(selection, values=[PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY], state="readonly")
        self.combo_provider_mode.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 8))
        self.combo_chat = ctk.CTkComboBox(selection, values=[self.NO_MODELS_LABEL], state="readonly")
        self.combo_chat.grid(row=1, column=2, sticky="ew", padx=12, pady=(0, 8))
        self.combo_analysis = ctk.CTkComboBox(selection, values=[self.NO_MODELS_LABEL], state="readonly")
        self.combo_analysis.grid(row=1, column=3, sticky="ew", padx=12, pady=(0, 8))
        self.btn_save_selection = ctk.CTkButton(selection, text="Save Selection", command=self._save_selection)
        self.btn_save_selection.grid(row=1, column=4, padx=12, pady=(0, 8), sticky="ew")

        self.lbl_selection_hint = tk.Label(
            selection,
            text="Saving selection only writes local config. It does not start providers, download, load, or unload models.",
            font=Theme.FONT_BODY,
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_DARKER,
            justify="left",
            wraplength=1000,
        )
        self.lbl_selection_hint.grid(row=2, column=0, columnspan=5, sticky="w", padx=12, pady=(0, 12))

        guidance_frame = ctk.CTkFrame(self, fg_color=Theme.BG_DARKER)
        guidance_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        tk.Label(guidance_frame, text="Guidance", font=Theme.FONT_H3, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKER).pack(anchor="w", padx=12, pady=(12, 4))
        self.txt_guidance = ctk.CTkTextbox(guidance_frame, height=180, fg_color=Theme.BG_DARKEST, text_color=Theme.TEXT_MAIN, wrap="word")
        self.txt_guidance.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.txt_guidance.configure(state="disabled")

        lists = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
        lists.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 20))
        lists.grid_columnconfigure(0, weight=1)
        lists.grid_columnconfigure(1, weight=1)
        lists.grid_rowconfigure(0, weight=1)

        self.downloaded_tree = self._build_tree(lists, "Downloaded/listed models", 0)
        self.loaded_tree = self._build_tree(lists, "Loaded models", 1)

    def _build_tree(self, parent, title, column):
        frame = ctk.CTkFrame(parent, fg_color=Theme.BG_DARKER)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column == 0 else (10, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        tk.Label(frame, text=title, font=Theme.FONT_H3, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKER).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        tree_frame = ctk.CTkFrame(frame, fg_color=Theme.BG_DARKER)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree = ttk.Treeview(tree_frame, columns=("display", "identifier", "status"), show="headings", height=12, yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=tree.yview)
        tree.heading("display", text="Model")
        tree.heading("identifier", text="Identifier")
        tree.heading("status", text="Status")
        tree.column("display", width=260, anchor="w")
        tree.column("identifier", width=220, anchor="w")
        tree.column("status", width=120, anchor="w")
        return tree

    def _set_guidance(self, text: str):
        self.txt_guidance.configure(state="normal")
        self.txt_guidance.delete("1.0", "end")
        self.txt_guidance.insert("1.0", text.strip())
        self.txt_guidance.configure(state="disabled")

    def _clean_model_choice(self, value: str, *, provider: str) -> str:
        text = str(value or "").strip()
        if text in {self.NO_MODELS_LABEL, "No downloaded models"}:
            return "" if provider == "local_review_only" else text
        return text

    def _save_selection(self):
        provider = str(self.combo_provider.get() or "local_review_only").strip()
        provider_mode = str(self.combo_provider_mode.get() or PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY).strip()
        chat_value = self._clean_model_choice(str(self.combo_chat.get() or ""), provider=provider)
        analysis_value = self._clean_model_choice(str(self.combo_analysis.get() or ""), provider=provider)

        if provider != "local_review_only" and (
            not chat_value
            or not analysis_value
            or chat_value == self.NO_MODELS_LABEL
            or analysis_value == self.NO_MODELS_LABEL
        ):
            messagebox.showwarning("Runtime Manager", "Select both a chat model and an analysis model for the selected provider.", parent=self)
            return

        def _save(on_status=None):
            return self.selection_service.save_selection(
                provider=provider,
                provider_mode=provider_mode,
                chat_model=chat_value,
                analysis_model=analysis_value,
                scope="local",
            ).to_dict()

        self._run_async(_save)

    def _run_async(self, func):
        self._set_busy(True)

        def _worker():
            try:
                result = func(on_status=None)
            except TypeError:
                result = func()
            except Exception as exc:
                result = {"status": "ERROR", "message": str(exc), "guidance": str(exc)}
                logger.exception("Runtime manager action failed")
            self._safe_after(0, lambda: self._finish_action(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _finish_action(self, result):
        self._set_busy(False)
        if result and result.get("ok") is True and not result.get("status"):
            status = "SAVED"
        else:
            status = str((result or {}).get("status") or "UNKNOWN")
        message = str((result or {}).get("message") or "Action finished.")
        self.refresh_inventory(show_popup=False)
        try:
            self.controller._refresh_runtime_status(prompt_if_needed=False)
        except Exception:
            logger.debug("Controller runtime status refresh failed after dialog action.", exc_info=True)
        try:
            self.controller._refresh_runtime_platform_sidebar()
        except Exception:
            logger.debug("Controller runtime platform refresh failed after dialog action.", exc_info=True)
        if status == "ERROR":
            messagebox.showerror("Runtime Manager", message, parent=self)
        else:
            messagebox.showinfo("Runtime Manager", f"{status}: {message}", parent=self)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for widget in (
            self.btn_refresh,
            self.btn_start_server,
            self.btn_prepare_embedding,
            self.btn_load_analysis,
            self.btn_load_chat,
            self.btn_unload,
            self.btn_save_selection,
        ):
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def _build_runtime_read_model(self):
        try:
            return self.runtime_platform_read_model_service.build_read_model()
        except Exception:
            logger.debug("Runtime platform read-model refresh failed.", exc_info=True)
            return {}

    def _merge_model_values(self, presenter_values, downloaded):
        values = []
        seen = set()
        for value in list(presenter_values or []):
            text = str(value or "").strip()
            if text and text not in seen:
                seen.add(text)
                values.append(text)
        for row in downloaded or []:
            model_key = str(row.get("model_key") or "").strip()
            if model_key and model_key not in seen:
                seen.add(model_key)
                values.append(model_key)
        return values or [self.NO_MODELS_LABEL]

    def _apply_runtime_selection_presenter(self, selection_presented, downloaded, selected):
        provider_values = selection_presented.get("provider_values") or ["local_review_only"]
        mode_values = selection_presented.get("provider_mode_values") or [PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY]
        model_values = self._merge_model_values(selection_presented.get("model_values"), downloaded)

        self.combo_provider.configure(values=provider_values)
        self.combo_provider.set(selection_presented.get("selected_provider") or provider_values[0])
        self.combo_provider_mode.configure(values=mode_values)
        self.combo_provider_mode.set(selection_presented.get("selected_provider_mode") or mode_values[0])
        self.combo_chat.configure(values=model_values)
        self.combo_analysis.configure(values=model_values)

        chat_choice = str(selection_presented.get("selected_chat_model") or selected.get("chat") or "").strip()
        analysis_choice = str(selection_presented.get("selected_analysis_model") or selected.get("analysis") or "").strip()
        self.combo_chat.set(chat_choice if chat_choice in model_values else model_values[0])
        self.combo_analysis.set(analysis_choice if analysis_choice in model_values else model_values[0])

        recommendation = str(selection_presented.get("recommendation_summary") or "").strip()
        readiness = str(selection_presented.get("model_readiness") or "not_verified").strip()
        provider = str(selection_presented.get("selected_provider") or "local_review_only").strip()
        self.lbl_selection_hint.configure(
            text=(
                "Saving selection only writes local config. It does not start providers, download, load, or unload models. "
                f"Selected provider: {provider}. Model readiness: {readiness}. Recommendation: {recommendation}."
            )
        )

    def refresh_inventory(self, show_popup: bool = False):
        try:
            inventory = self.runtime_service.get_runtime_inventory()
        except Exception as exc:
            if show_popup:
                messagebox.showerror("Runtime Manager", str(exc), parent=self)
            return

        read_model = self._build_runtime_read_model()
        selection_presented = present_runtime_manager_selection(read_model)

        status = str(inventory.get("status") or "UNKNOWN")
        message = str(inventory.get("message") or "Runtime state unavailable.")
        self.lbl_status.configure(text=f"{status} - {message}", fg=Theme.TEXT_MUTED if status == "READY" else Theme.TEXT_MAIN)
        guidance = str(inventory.get("guidance") or message)
        recommendation = str(selection_presented.get("recommendation_summary") or "").strip()
        if recommendation:
            guidance = f"{guidance}\n\nHardware/model recommendation: {recommendation}"
        self._set_guidance(guidance)

        downloaded = inventory.get("downloaded_llms") or []
        loaded = inventory.get("loaded_models") or []
        selected = inventory.get("selected_models") or {}
        loaded_roles = inventory.get("loaded_roles") or {}

        self._apply_runtime_selection_presenter(selection_presented, downloaded, selected)

        for tree in (self.downloaded_tree, self.loaded_tree):
            for item in tree.get_children():
                tree.delete(item)

        loaded_keys = {str(row.get("model_key") or "").strip() for row in loaded}
        for row in downloaded:
            model_key = str(row.get("model_key") or "").strip()
            display = str(row.get("display_name") or model_key).strip()
            downloaded_status = []
            if model_key == selected.get("chat"):
                downloaded_status.append("chat")
            if model_key == selected.get("analysis"):
                downloaded_status.append("analysis")
            if model_key in loaded_keys:
                downloaded_status.append("loaded")
            if not downloaded_status:
                downloaded_status.append("downloaded")
            self.downloaded_tree.insert("", "end", values=(display, model_key, ", ".join(downloaded_status)))

        for row in selection_presented.get("model_values") or []:
            model_key = str(row or "").strip()
            if not model_key or model_key in {self.NO_MODELS_LABEL, "No downloaded models"} or model_key in loaded_keys:
                continue
            if any(model_key == str(item.get("model_key") or "").strip() for item in downloaded):
                continue
            self.downloaded_tree.insert("", "end", values=(model_key, model_key, "provider-listed"))

        for row in loaded:
            identifier = str(row.get("identifier") or row.get("model_key") or "").strip()
            model_key = str(row.get("model_key") or identifier).strip()
            display = str(row.get("display_name") or model_key).strip()
            load_status = str(row.get("status") or "loaded").strip() or "loaded"
            role_flags = []
            if loaded_roles.get("chat") and model_key == selected.get("chat"):
                role_flags.append("chat")
            if loaded_roles.get("analysis") and model_key == selected.get("analysis"):
                role_flags.append("analysis")
            if role_flags:
                load_status = f"{load_status} ({', '.join(role_flags)})"
            self.loaded_tree.insert("", "end", values=(display, identifier, load_status))

        self.btn_start_server.configure(state="normal" if status == "SERVER_NOT_RUNNING" else "normal")
        self.btn_prepare_embedding.configure(state="normal" if status == STATUS_EMBEDDING_RUNTIME_NOT_READY else "normal")
        if show_popup:
            messagebox.showinfo("Runtime Manager", f"{status}: {message}", parent=self)
