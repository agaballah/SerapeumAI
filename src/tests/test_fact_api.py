# -*- coding: utf-8 -*-
"""
test_fact_api.py — Unit tests for FactQueryAPI._infer_fact_types()

Covers:
  - Required positive cases: document queries must infer document.*
  - Required negative cases: ambiguous words must NOT overfire on document.*
  - Existing domain routing preservation (schedule/BIM/compliance/cost)
"""
import pytest
from src.application.api.fact_api import FactQueryAPI


@pytest.fixture
def api():
    return FactQueryAPI(db=None)


_DOC_TYPES = {"document.page_count", "document.has_text", "document.profile"}


# ── Positive: these MUST route to document.* ─────────────────────────────────

@pytest.mark.parametrize("query", [
    "what is this document",
    "summarize this document",
    "tell me about this file",
    "how many pages does this pdf have",
    "does this PDF have text",
    "document profile",
    "what is this pdf",
    "tell me about this document",
    "about this file",
    "page count of the document",
    "does this document has text",
])
def test_positive_document_intent(api, query):
    """Document-style queries must infer document.* fact types."""
    inferred = set(api._infer_fact_types(query))
    assert _DOC_TYPES.issubset(inferred), (
        f"Expected document.* for: {query!r} — got: {inferred}"
    )


# ── Negative: these must NOT blindly route to document.* ─────────────────────

@pytest.mark.parametrize("query", [
    "summarize schedule delays",
    "page layout issue",
    "text extraction pipeline failed",
    "profile settings",
    "cost summary",
    "text in a bim element",
    "schedule page report",
    "summarize costs",
    "profile of the BIM model",
    "extract text from database",
    "page numbering in drawings",
])
def test_negative_no_document_bleed(api, query):
    """Ambiguous generic terms must NOT route to document.* unless there is a clear document cue."""
    inferred = api._infer_fact_types(query)
    has_doc = any("document." in t for t in inferred)
    assert not has_doc, (
        f"ROUTING BLEED: {query!r} incorrectly inferred document.* => {inferred}"
    )


# ── Existing domain preservation ─────────────────────────────────────────────

def test_schedule_routing_preserved(api):
    inferred = api._infer_fact_types("schedule risk")
    assert "schedule.activity" in inferred or "schedule.milestone" in inferred

def test_delay_routing_preserved(api):
    inferred = api._infer_fact_types("what are the delay risks")
    assert "schedule.activity" in inferred

def test_cost_routing_preserved(api):
    inferred = api._infer_fact_types("cost breakdown")
    assert "cost.line_item" in inferred or "cost.summary" in inferred

def test_bim_routing_preserved(api):
    inferred = api._infer_fact_types("bim element clash")
    assert "bim.element" in inferred

def test_compliance_routing_preserved(api):
    inferred = api._infer_fact_types("compliance check required")
    assert "compliance.check" in inferred

def test_schedule_not_bleed_to_document(api):
    """'summarize schedule delays' must go to schedule.*, not document.*"""
    inferred = api._infer_fact_types("summarize schedule delays")
    assert "schedule.activity" in inferred or "schedule.milestone" in inferred
    assert not any("document." in t for t in inferred)
