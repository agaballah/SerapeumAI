import os
import logging
import json
import threading
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from src.ui.pages.base_page import BasePage
from src.ui.styles.theme import Theme
from src.application.services.dashboard_honesty import (
    compute_fact_visibility_metrics,
    fact_ratio_health,
    governance_status_label,
    backlog_label,
    throughput_label,
    assess_p6_truth,
)

logger = logging.getLogger(__name__)



class DashboardPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._refresh_after_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Scrollable Body
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_DARKEST, bg_color=Theme.BG_DARKEST)
        self.scroll_body.grid(row=0, column=0, sticky="nsew")
        self.scroll_body.grid_columnconfigure(0, weight=1)

        # Header Section
        self.frame_header = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKEST)
        self.frame_header.grid(row=0, column=0, pady=(40, 20), padx=40, sticky="ew")

        self.lbl_title = tk.Label(self.frame_header, text="Project Intelligence Dashboard",
                                  font=Theme.FONT_H1, fg=Theme.TEXT_MAIN, bg=Theme.BG_DARKEST,
                                  borderwidth=0, highlightthickness=0)
        self.lbl_title.pack(side="left")

        # Stats Grid
        self.grid_stats = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKEST)
        self.grid_stats.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        self.grid_stats.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_files = self._create_stat_card(self.grid_stats, "Files Ingested", "0", 0)
        self.card_facts = self._create_stat_card(self.grid_stats, "Facts Qualified", "0", 1)
        self.card_links = self._create_stat_card(self.grid_stats, "Knowledge Links", "0", 2)

        # Activity & Diagnostics Section
        self.frame_activity = ctk.CTkFrame(self.scroll_body, fg_color=Theme.BG_DARKER, corner_radius=15,
                                         border_width=1, border_color=Theme.BG_DARK)
        self.frame_activity.grid(row=2, column=0, sticky="nsew", padx=40, pady=30)
        self.frame_activity.grid_columnconfigure(0, weight=1)

        tk.Label(self.frame_activity, text="Pipeline Diagnostics & Mission Control",
                 font=Theme.FONT_H2, fg=Theme.TEXT_MAIN,
                 bg=Theme.BG_DARKER, borderwidth=0, highlightthickness=0).grid(row=0, column=0, pady=(25, 15), padx=25, sticky="w")

        # Three-Tier Diagnostic Tree
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dash.Treeview", background=Theme.BG_DARKEST, foreground=Theme.TEXT_MAIN, 
                        fieldbackground=Theme.BG_DARKEST, borderwidth=0, font=Theme.FONT_MONO)
        style.map("Dash.Treeview", background=[('selected', Theme.PRIMARY)])
        
        self.tree_status = ttk.Treeview(self.frame_activity, columns=("value", "status"), 
                                      show="tree headings", height=15, style="Dash.Treeview")
        self.tree_status.heading("#0", text="Diagnostic Category")
        self.tree_status.heading("value", text="Metric")
        self.tree_status.heading("status", text="Health")
        self.tree_status.column("#0", width=300)
        self.tree_status.column("value", width=250)
        self.tree_status.column("status", width=150)
        self.tree_status.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 25))

    def _create_stat_card(self, master, title, value, col):
        card = ctk.CTkFrame(master, fg_color=Theme.BG_DARKER, corner_radius=12,
                           border_width=1, border_color=Theme.BG_DARK)
        card.grid(row=0, column=col, sticky="nsew", padx=5)

        lbl_t = tk.Label(card, text=title, font=Theme.FONT_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG_DARKER,
                         borderwidth=0, highlightthickness=0)
        lbl_t.pack(pady=(20, 0), padx=20)

        lbl_v = tk.Label(card, text=value, font=Theme.FONT_H1, fg=Theme.PRIMARY, bg=Theme.BG_DARKER,
                         borderwidth=0, highlightthickness=0)
        lbl_v.pack(pady=(5, 20), padx=20)

        card.lbl_v = lbl_v
        return card

    def on_show(self):
        if not self.controller or not self.controller.db:
            self.reset_view()
            return
        self.update_stats()

    def on_app_close(self):
        super().on_app_close()
        self._cancel_refresh()

    def _safe_after(self, delay_ms: int, callback):
        return self.safe_ui_after(delay_ms, callback)

    def _cancel_refresh(self):
        if self._refresh_after_id is not None:
            try:
                self.after_cancel(self._refresh_after_id)
            except Exception:
                pass
            self._refresh_after_id = None

    def reset_view(self):
        if not self.winfo_exists():
            return

        self.card_files.lbl_v.configure(text="0")
        self.card_facts.lbl_v.configure(text="0")
        self.card_links.lbl_v.configure(text="0")

        self.tree_status.delete(*self.tree_status.get_children())
        self.tree_status.insert(
            "",
            "end",
            text="No project loaded",
            values=("Open a project to view diagnostics", "IDLE"),
        )

    def update_stats(self):
        if not self.winfo_exists():
            return
        self._cancel_refresh()
        threading.Thread(target=self._fetch_stats_bg, daemon=True).start()
        self._refresh_after_id = self._safe_after(5000, self.update_stats)

    def _table_exists(self, db, table_name: str) -> bool:
        try:
            row = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            return bool(row)
        except Exception:
            return False

    def _column_exists(self, db, table_name: str, column_name: str) -> bool:
        try:
            rows = db.execute(f"PRAGMA table_info({table_name})").fetchall()
            return any(r[1] == column_name for r in rows)
        except Exception:
            return False

    def _count_rows(self, db, table_name: str) -> int:
        if not self._table_exists(db, table_name):
            return 0
        try:
            row = db.execute(f"SELECT count(*) FROM {table_name}").fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def _fetch_extraction_runtimes(self, db):
        if not self._table_exists(db, "extraction_runs"):
            return []

        name_col = None
        if self._column_exists(db, "extraction_runs", "extractor_name"):
            name_col = "extractor_name"
        elif self._column_exists(db, "extraction_runs", "extractor_id"):
            name_col = "extractor_id"

        if not name_col:
            return []

        has_started = self._column_exists(db, "extraction_runs", "started_at")
        end_col = None
        if self._column_exists(db, "extraction_runs", "ended_at"):
            end_col = "ended_at"
        elif self._column_exists(db, "extraction_runs", "finished_at"):
            end_col = "finished_at"

        has_status = self._column_exists(db, "extraction_runs", "status")

        try:
            if has_started and end_col:
                where_clause = "WHERE status='SUCCESS'" if has_status else ""
                query = f"""
                    SELECT {name_col}, AVG({end_col} - started_at)
                    FROM extraction_runs
                    {where_clause}
                    GROUP BY {name_col}
                """
                return db.execute(query).fetchall()

            query = f"SELECT {name_col}, count(*) FROM extraction_runs GROUP BY {name_col}"
            return db.execute(query).fetchall()
        except Exception as exc:
            logger.debug("Dashboard extraction runtime fallback activated: %s", exc)
            return []

    def _fetch_recent_logs(self, db):
        required = ["type_name", "status", "updated_at"]
        if not self._table_exists(db, "job_queue"):
            return []
        if not all(self._column_exists(db, "job_queue", c) for c in required):
            return []

        try:
            rows = db.execute(
                "SELECT type_name, status, updated_at FROM job_queue ORDER BY updated_at DESC LIMIT 5"
            ).fetchall()
            return [(r[2], r[0], r[1]) for r in rows]
        except Exception as exc:
            logger.debug("Dashboard recent-log fallback activated: %s", exc)
            return []

    def _fetch_latest_failure(self, db):
        required = ["type_name", "status", "updated_at", "error_text"]
        if not self._table_exists(db, "job_queue"):
            return None
        if not all(self._column_exists(db, "job_queue", c) for c in required):
            return None

        try:
            row = db.execute(
                """
                SELECT updated_at, error_text
                FROM job_queue
                WHERE type_name='ANALYZE_DOC' AND status='FAILED' AND error_text IS NOT NULL AND trim(error_text) != ''
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            return (row[0], row[1])
        except Exception as exc:
            logger.debug("Dashboard failure-summary fallback activated: %s", exc)
            return None

    def _format_timestamp(self, value) -> str:
        if value is None or value == "":
            return "N/A"

        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value)).strftime("%H:%M:%S")
            except Exception:
                return str(value)

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return "N/A"
            try:
                return datetime.fromtimestamp(float(raw)).strftime("%H:%M:%S")
            except Exception:
                pass

            normalized = raw.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

            return raw[:32]

        return str(value)

    def _fetch_stats_bg(self):
        if not self.controller or not self.controller.db:
            self._safe_after(0, self.reset_view)
            return

        db = self.controller.db
        try:
            f_count = self._count_rows(db, "file_versions")
            fact_count = self._count_rows(db, "facts")
            link_count = self._count_rows(db, "links") or self._count_rows(db, "entity_links")

            ext_data = self._fetch_extraction_runtimes(db)

            valid_facts = 0
            human_facts = 0
            candidate_facts = 0
            if self._table_exists(db, "facts") and self._column_exists(db, "facts", "status"):
                valid_facts = db.execute("SELECT count(*) FROM facts WHERE status='VALIDATED'").fetchone()[0]
                human_facts = db.execute("SELECT count(*) FROM facts WHERE status='HUMAN_CERTIFIED'").fetchone()[0]
                candidate_facts = db.execute("SELECT count(*) FROM facts WHERE status='CANDIDATE'").fetchone()[0]

            recent_logs = self._fetch_recent_logs(db)
            latest_failure = self._fetch_latest_failure(db)

            p6_activity_count = self._count_rows(db, "p6_activities")
            p6_float_count = 0
            p6_critical_count = 0
            if self._table_exists(db, "p6_activities") and self._column_exists(db, "p6_activities", "total_float"):
                p6_float_count = int((db.execute("SELECT count(*) FROM p6_activities WHERE total_float IS NOT NULL").fetchone() or [0])[0])
                p6_critical_count = int((db.execute("SELECT count(*) FROM p6_activities WHERE total_float IS NOT NULL AND total_float <= 0").fetchone() or [0])[0])

            fact_metrics = compute_fact_visibility_metrics(
                total_facts=fact_count,
                valid_facts=valid_facts,
                human_facts=human_facts,
                candidate_facts=candidate_facts,
            )

            self._safe_after(0, lambda: self._update_ui_elements(
                f_count,
                link_count,
                ext_data,
                fact_metrics,
                recent_logs,
                latest_failure,
                {"activity_count": p6_activity_count, "float_count": p6_float_count, "critical_count": p6_critical_count},
            ))
        except Exception as e:
            logger.error(f"Dashboard Refresh Error: {e}")
            self._safe_after(0, self.reset_view)

    def _update_ui_elements(self, f_count, link_count, ext_runtimes, fact_metrics, recent_logs, latest_failure=None, p6_truth=None):
        if not self.winfo_exists(): return
        
        # Stats Update
        self.card_files.lbl_v.configure(text=str(f_count))
        self.card_facts.lbl_v.configure(text=str(fact_metrics["qualified_facts"]))
        self.card_links.lbl_v.configure(text=str(link_count))

        # Three-Tier Tree Refresh
        self.tree_status.delete(*self.tree_status.get_children())
        
        # Tier 1: Extraction Throughput
        t1 = self.tree_status.insert("", "end", text="Extraction Engine Throughput", open=True)
        for name, avg_time in ext_runtimes:
            ms = round(avg_time * 1000, 2) if avg_time and isinstance(avg_time, (int, float)) else 0
            self.tree_status.insert(t1, "end", text=f"Pipeline: {name}", values=(f"{ms}ms / run", throughput_label(len(ext_runtimes))))
        if not ext_runtimes:
            self.tree_status.insert(t1, "end", text="No successful runs detected", values=("0ms", "STALE"))

        # Tier 2: Truth Mapping & Early Fact Visibility
        t2 = self.tree_status.insert("", "end", text="Truth Mapping & Coverage", open=True)
        total = fact_metrics["built_facts"]
        qualified = fact_metrics["qualified_facts"]
        ratio = f"{round((qualified / total) * 100, 1)}%" if total > 0 else "0%"
        self.tree_status.insert(t2, "end", text="Qualified Ratio", values=(ratio, fact_ratio_health(fact_metrics)))
        self.tree_status.insert(t2, "end", text="Facts Built (All States)", values=(str(total), "VISIBLE" if total > 0 else "EMPTY"))
        self.tree_status.insert(t2, "end", text="Candidate Backlog", values=(str(fact_metrics["candidate_facts"]), backlog_label(fact_metrics["candidate_facts"])))
        p6_truth = p6_truth or {"activity_count": 0, "float_count": 0, "critical_count": 0}
        p6_view = assess_p6_truth(
            p6_truth.get("activity_count", 0),
            p6_truth.get("float_count", 0),
            p6_truth.get("critical_count", 0),
        )
        self.tree_status.insert(t2, "end", text="P6 Schedule Truth", values=(p6_view["metric"], p6_view["status"]))

        # Tier 3: Governance & Certification
        t3 = self.tree_status.insert("", "end", text="Governance Certification Status", open=True)
        self.tree_status.insert(t3, "end", text="System Validated", values=(str(fact_metrics["valid_facts"]), governance_status_label(fact_metrics["valid_facts"], trusted_label="TRUSTED")))
        self.tree_status.insert(t3, "end", text="Human Certified", values=(str(fact_metrics["human_facts"]), governance_status_label(fact_metrics["human_facts"], trusted_label="GOLDEN")))
        if fact_metrics["pending_qualification"] > 0:
            self.tree_status.insert(t3, "end", text="Built Awaiting Qualification", values=(str(fact_metrics["pending_qualification"]), "IN_PROGRESS"))

        # Tier 4: Real-time Mission Control (Recent Logs)
        t4 = self.tree_status.insert("", "end", text="Recent Pipeline Activity", open=True)
        for ts, label, status in recent_logs:
            dt = self._format_timestamp(ts)
            self.tree_status.insert(t4, "end", text=f"Job: {label}", values=(dt, status))
        if not recent_logs:
            self.tree_status.insert(t4, "end", text="No recent jobs detected", values=("N/A", "IDLE"))

        # Tier 5: Latest runtime failure surfaced to the operator
        t5 = self.tree_status.insert("", "end", text="Latest Runtime Alert", open=True)
        if latest_failure:
            fail_ts, fail_msg = latest_failure
            fail_dt = self._format_timestamp(fail_ts)
            fail_msg = str(fail_msg or "Unknown runtime error").strip().replace("\n", " ")
            self.tree_status.insert(t5, "end", text="LM Studio preflight", values=(fail_dt, "FAILED"))
            self.tree_status.insert(t5, "end", text=fail_msg[:120], values=("Operator action required", "ERROR"))
        else:
            self.tree_status.insert(t5, "end", text="No runtime alerts", values=("N/A", "STABLE"))
