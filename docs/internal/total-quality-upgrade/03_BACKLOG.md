# 03 — Backlog

## Purpose

This backlog defines the full planned packet set for Total Quality Upgrade v3.3. The upgrade is planned, not active.

## Phase DOC-0 — GitHub Truth Reset

### DOC-01 — Documentation Inventory and Truth Audit

Read-only audit of public-facing and internal documentation, risky claims, missing docs, and license posture.

### DOC-02 — License Audit and Normalization Plan

Verify intended license, top-level license file, source headers, copied assets/code, third-party notices, and GitHub license detection.

### DOC-03 — README Truth Rewrite

Rewrite README as a short, honest, user-facing landing page after DOC-01 and DOC-02.

### DOC-04 — Roadmap Reset

Separate current reality, publish closure, next upgrade, later platform work, research-only items, and explicit non-goals.

### DOC-05 — Public Support Docs

Create or repair user-facing support docs: system requirements, troubleshooting, privacy, limitations, changelog.

### DOC-06 — Documentation Governance Checklist

Add documentation impact discipline to future packets and PRs.

### DOC-07 — GitHub Repo Page Hygiene

Align repository description, topics, website link, screenshots, badges, license display, and release posture with public docs.

## Phase TQ-Foundation

### TQ-01 — Quality Contract + Extension Matrix

Define quality statuses, dimensions, source lanes, support levels, quality profiles, and the canonical extension support matrix.

### TQ-02 — PDF Quality Baseline

Add PDF pre-inspection, page-level classification, route recommendation, and deterministic quality reports.

### TQ-03 — Document Center Four-Tab Redesign

Separate consolidated review, full metadata, raw deterministic extraction, and AI/VLM output.

### TQ-04 — Chat Quality Gate

Make mounted chat measurable: active-project-bound, trusted-fact-aware, refusal-capable, and protected from unsupported fluent answers.

### TQ-05 — Gold Fixture Test Pack

Create non-confidential regression fixtures and expected outputs.

## Phase TQ-Agentic Spine

### TQ-06 — Tool Registry + Policy Gate

Define safe internal tools, schemas, authority, side effects, approval rules, and audit requirements.

### TQ-07 — Skill Registry

Define AECO skills with allowed tools, required inputs, refusal rules, and output contracts.

### TQ-08 — Agent Run State + Safe Trace

Track tool-using workflows with a safe procedural trace, not private reasoning.

### TQ-09 — Memory Separation

Separate session memory, project memory, user preferences, and tool/runtime memory. Prevent memory from becoming truth.

### TQ-10 — Tool-Using Chat Integration

Connect mounted chat to the safe tool/skill layer.

### TQ-11 — ToolBench / AgentBench

Benchmark schema validity, tool correctness, refusal, evidence preservation, calculation safety, routing, and repeatability.

## Phase TQ-Deep Evidence

### TQ-12 — OCR / Scanned Document Quality

Improve scan detection, OCR confidence, raw OCR separation, low-confidence warnings, and retry strategy.

### TQ-13 — Drawing Sheet Quality

Improve title block, revision table, general notes, callout, and drawing-quality extraction.

### TQ-14 — Office / Register Quality

Improve Excel, register, DOCX, and PPTX extraction quality.

### TQ-15 — IFC / BIM Quality

Improve spatial hierarchy, GUID lineage, property sets, quantities, materials, and IFC quality reporting.

### TQ-16 — P6 / XER Schedule Quality

Improve schedule graph, relationships, float/critical-path honesty, missing logic detection, and schedule quality reporting.

## Phase TQ-Controlled Labs

### TQ-17 — Bounded Review Swarm Lab

Evaluate multi-agent review only as a non-governing candidate-finding lane.

### TQ-18 — MCP / External Connector Lab

Evaluate external tool connectors only as disabled-by-default, allowlisted, consent-gated experiments.

### TQ-19 — QuantBench + Model Fit Matrix

Validate local model roles, quantization, tool calling, JSON validity, refusal, evidence preservation, and hardware fit.

### TQ-20 — Local 3D Review Concepts Lab

Study local-only spatial review concepts with dummy data. Do not adopt hosted 3D tools or packaging dependencies.

### TQ-21 — SerapeumAI-Owned Spatial Scene Schema

Define local spatial scene/evidence schema if the 3D review concept remains useful.

### TQ-22 — Optional Local Viewer Decision

Decide whether an external browser, local static viewer, WebView2, plugin, or no viewer is appropriate.

## Phase DOC-FINAL

### DOC-FINAL — Documentation Reconciliation Gate

Ensure README, roadmap, license, limitations, privacy, system requirements, troubleshooting, changelog, GitHub page, screenshots, and release notes match proven behavior.

## Phase RELEASE-GATE

Final release proof only after implementation, docs, tests, risks, and packaging implications are clean.
