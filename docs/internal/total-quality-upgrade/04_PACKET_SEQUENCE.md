# 04 — Packet Sequence

## Purpose

This document defines the execution order and the required packet contract for the Total Quality Upgrade.

## Execution order

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

## Packet template

Every packet must define:

```text
Task class:
Owner:
Objective:
Why now:
Allowed scope:
Forbidden scope:
Likely touched files:
Documentation impact:
License/dependency impact:
Packaging risk:
Windows risk:
Rollback risk:
Proof required:
Exit condition:
```

## Packet result template

Every completed packet must return:

```text
Task:
Verdict: PASS / PARTIAL / BLOCKED
Files touched:
What changed:
Tests run:
Results:
Documentation impact handled:
License/dependency impact:
Risks:
Diff summary:
Rollback notes:
Next recommended packet:
```

## Dependency rules

- TQ-01 must precede extractor quality changes.
- TQ-02 must precede OCR and drawing quality packets.
- TQ-03 must precede reviewer-facing AI/VLM display changes.
- TQ-04 must precede tool-using chat integration.
- TQ-05 must precede deep extractor regression work.
- TQ-06 through TQ-09 must precede TQ-10.
- TQ-17 and TQ-18 remain controlled labs only.
- DOC-FINAL must precede any release decision.

## Execution discipline

Implementation can be small. Diagnosis can be broad. No packet may widen into packaging, dependency upgrades, or architecture substitution without explicit approval.
