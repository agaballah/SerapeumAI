# 14 — GitHub Rollout Plan

## Purpose

Define how the Total Quality Upgrade becomes visible and executable in GitHub without overclaiming or interrupting the currently active upgrade.

## Current status

The Total Quality Upgrade is planned, not active. This internal dossier may live in the repository so the upgrade can start cleanly later, but it must not be presented as shipped behavior.

## Immediate posture

- Do not announce the upgrade as active while another upgrade is running.
- Do not open release notes for this upgrade yet.
- Do not update public README with future behavior as if shipped.
- Do not create public marketing language around agent swarms, Revit replacement, or guaranteed compliance.
- Do not merge implementation packets before DOC-0 is complete.

## When current active upgrade finishes

After the current active upgrade lands and `main` is stable:

1. Sync/rebase or recreate the Total Quality planning branch from final `main`.
2. Verify all planning dossier files are present.
3. Complete `01_CURRENT_REPO_TRUTH.md` from actual repo behavior.
4. Run DOC-0 GitHub Truth Reset.
5. Create GitHub milestone only when ready to start.
6. Create issues from the packet backlog.
7. Start with `DOC-01`, not `TQ-01`.

## Suggested milestone

```text
Total Quality Upgrade
```

## Suggested labels

```text
tq-upgrade
quality
documentation-impact
extractor
evidence
chat
agentic-workflow
testing
risk-packaging
risk-license
risk-windows
lab-only
```

## Suggested issue sequence

Create issues in this order:

1. DOC-01 Documentation Inventory and Truth Audit
2. DOC-02 License Audit and Normalization Plan
3. DOC-03 README Truth Rewrite
4. DOC-04 Roadmap Reset
5. DOC-05 Public Support Docs
6. DOC-06 Documentation Governance Checklist
7. DOC-07 GitHub Repo Page Hygiene
8. TQ-01 Quality Contract + Extension Matrix
9. TQ-02 PDF Quality Baseline
10. TQ-03 Document Center Four-Tab Redesign
11. TQ-04 Chat Quality Gate
12. TQ-05 Gold Fixture Test Pack
13. TQ-06 Tool Registry + Policy Gate
14. TQ-07 Skill Registry
15. TQ-08 Agent Run State + Safe Trace
16. TQ-09 Memory Separation
17. TQ-10 Tool-Using Chat Integration
18. TQ-11 ToolBench / AgentBench
19. TQ-12 OCR / Scanned Document Quality
20. TQ-13 Drawing Sheet Quality
21. TQ-14 Office / Register Quality
22. TQ-15 IFC / BIM Quality
23. TQ-16 P6 / XER Schedule Quality
24. TQ-17 Bounded Review Swarm Lab
25. TQ-18 MCP / External Connector Lab
26. TQ-19 QuantBench + Model Fit Matrix
27. TQ-20 Local 3D Review Concepts Lab
28. TQ-21 SerapeumAI-Owned Spatial Scene Schema
29. TQ-22 Optional Local Viewer Decision
30. DOC-FINAL Documentation Reconciliation Gate
31. RELEASE-GATE Final Release Proof

## Public wording guidance

Acceptable public wording later:

```text
Planned: Total Quality Upgrade — a future upgrade focused on extraction quality, evidence separation, file support clarity, chat reliability, safe tool use, and regression fixtures.
```

Forbidden public wording:

```text
SerapeumAI now has autonomous agents, agent swarms, full BIM editing, Revit replacement, guaranteed compliance, or cloud-powered automation.
```

## PR strategy

- Planning dossier PR: docs-only, draft acceptable.
- DOC-0 PRs: public docs and governance, no source behavior changes unless explicitly scoped.
- TQ implementation PRs: one packet per PR where practical.
- Lab PRs: disabled by default, clearly marked experimental/lab-only.

## Branch strategy

Preferred future branch names:

```text
docs/github-truth-reset
tq/quality-contract-extension-matrix
tq/pdf-quality-baseline
tq/document-center-four-tab
tq/chat-quality-gate
tq/gold-fixtures
```

## Release communication rule

Release notes must be generated from passed gates and changelog entries. Do not write release notes from roadmap ambition.
