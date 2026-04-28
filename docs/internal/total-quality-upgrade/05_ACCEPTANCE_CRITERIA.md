# 05 — Acceptance Criteria

## Purpose

This document defines what counts as a pass for each quality area. A packet is not complete because implementation looks correct; it must satisfy its acceptance criteria with proof.

## Global acceptance criteria

A packet passes only if:

1. required behavior exists,
2. behavior matches the approved scope,
3. proof is reproducible,
4. Windows portability is preserved,
5. packaging behavior is not affected unless explicitly approved,
6. documentation impact is handled,
7. no product doctrine is weakened,
8. rollback is understandable.

## Documentation acceptance

- README describes only current proven behavior.
- Roadmap separates current, next, later, and research.
- Limitations are current.
- Privacy claims are accurate.
- License posture is clear and owner-approved.
- Changelog captures user-visible changes.
- GitHub page does not overclaim.

## Extension matrix acceptance

- Every declared extension has support level, expected output, source lanes, evidence anchors, limitations, and user-visible label.
- Unsupported files fail gracefully.
- Partial support is labeled as partial.
- Experimental support is not described as stable.

## PDF acceptance

- Native text PDFs are not classified as scanned.
- Scanned PDFs are flagged as OCR-needed.
- Mixed PDFs are classified page-by-page.
- Vector/drawing PDFs produce drawing-oriented warnings or route recommendations.
- PDF quality reports are deterministic.

## OCR acceptance

- OCR output is separated from native extraction.
- OCR confidence and quality warnings are visible.
- Low-confidence OCR does not silently govern facts.
- Retry/preprocessing behavior is documented where implemented.

## Drawing acceptance

- Title block candidates are extracted or explicitly reported missing.
- Drawing ID/title/revision/status candidates retain evidence anchors.
- VLM interpretation is labeled as support only.
- Drawing quality warnings are visible.

## IFC / BIM acceptance

- Spatial hierarchy is reconstructable from persisted data where supported.
- GUID lineage is preserved.
- Property sets and quantities are extracted only when present and proven.
- IFC limitations are visible.

## P6 / XER acceptance

- WBS and activity records are parsed where supported.
- Relationships and lags are represented correctly where data exists.
- Critical path and float are not overclaimed when data is insufficient.
- Schedule quality limitations are visible.

## Office / register acceptance

- Excel sheets and tables preserve meaningful boundaries.
- Register-like files expose normalized columns where confidently detected.
- DOCX headings and clauses preserve hierarchy where supported.
- PPTX slide titles, bullets, tables, and notes are separated where supported.

## Document Center acceptance

- Four tabs exist and match their meanings.
- AI/VLM output is not mixed into raw deterministic extraction.
- Metadata tab exposes all available metadata, not only hash/date.
- Empty states are honest.

## Fact quality acceptance

- Facts are atomic.
- Facts preserve lineage.
- Candidate, validated, human-certified, rejected, and refused semantics are consistent.
- Non-governing facts do not govern answers.

## Chat quality acceptance

- Chat is active-project-bound.
- Chat refuses when required trusted truth is missing.
- Chat does not falsely claim no facts exist when trusted facts exist.
- Candidate facts and AI support do not govern final answers.
- Calculations are performed by deterministic tools only.

## Agentic workflow acceptance

- Tools have schemas and authority declarations.
- Unauthorized tools are rejected.
- Tool outputs are schema-valid.
- Tool calls are audited.
- Human approval is required for sensitive actions.
- Safe trace shows procedure, not private reasoning.

## Fixture acceptance

- Fixtures are non-confidential and redistributable.
- Expected outputs are deterministic.
- Regression failures explain the quality dimension that failed.

## Release acceptance

The release gate passes only when code, docs, tests, limitations, privacy, license, GitHub page, and release notes all match proven behavior.
