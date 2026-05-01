# SerapeumAI

SerapeumAI is a Windows-first, local-first AECO review workspace.

It helps engineers and reviewers:

- ingest project files into a project workspace
- inspect deterministic extraction and AI analysis separately
- review facts on the Facts page with lineage / evidence support
- ask questions in Expert Chat and get a direct answer first, with optional evidence behind it

SerapeumAI is **review assistance** with evidence and provenance. It is **not** a guaranteed-compliance, legal approval, or autonomous design-authoring engine.

## Run

Use one clear dev run path:

```powershell
python run.py
```

## Runtime contract

- Windows is the baseline platform.
- LM Studio must be installed and running locally for the current mounted runtime path.
- The publish generative runtime is the single model `qwen2.5-coder-7b-instruct`.
- Embeddings remain separate from the generative model.
- Calculations and deterministic checks must be performed by application code/tools, not by LLM arithmetic.

## Mounted workflow

- **Documents**: browse project documents and open the File Inspector.
- **Schedule page**: inspect the project schedule and click activities to open linked schedule fact/evidence detail where available.
- **File Inspector**:
  1. Consolidated Review
  2. Full Metadata
  3. Raw Deterministic Extraction
  4. AI Output Only
- **Facts page**: review facts, inspect meaning, inspect provenance, and certify or reject with evidence.
- **Expert Chat**:
  - shows a direct answer first
  - can show a compact source-basis banner when helpful
  - keeps behind-the-scenes evidence behind an optional **Show Evidence** action
  - exposes these evidence lanes only when expanded:
    - Trusted Facts
    - Extracted Evidence
    - Linked Support
    - AI-Generated Synthesis
  - resets visible chat history when the active project closes or changes
  - drops late responses/errors from old project sessions

## Trust and provenance

- Trusted Facts remain the strongest source class.
- `VALIDATED` and `HUMAN_CERTIFIED` facts are trusted answer sources.
- `CANDIDATE` facts are visible for review but do not govern answers.
- `REJECTED` facts are excluded from trusted answer paths.
- AI-generated synthesis is clearly labeled non-governing.
- Linked Support is clearly labeled support, not certified truth.
- When trusted facts are incomplete, SerapeumAI may answer from grounded extraction or linked support only when that source class is explicitly labeled.

## Evidence and inspection

- Deterministic extraction and parser/OCR output must remain separated from AI/VLM output.
- File Inspector separates:
  - consolidated review,
  - full metadata,
  - raw deterministic extraction,
  - AI output only.
- AI/VLM output does not become certified truth unless promoted through the review/certification workflow.
- Deterministic extraction evidence can build trusted document facts through the build-facts path.

## Storage and project isolation

- Persistent project storage is localized under the project `.serapeum` root.
- The normal SQLite database is the authority.
- Vector/retrieval stores are derived support, not governing truth.
- Project A must not answer from Project B.
- Mounted chat requests are bound to the active project/session.

## Dashboard honesty

- Dashboard labels must not overclaim health or trust.
- Qualified facts are counted separately from all built facts.
- Missing optional extractor/runtime columns must degrade safely.
- Schedule/P6 truth labels must not claim verified critical path unless deterministic float data supports it.

## Clean shutdown

- Red-X close should internally close the project before destroying the app window.
- Closing the main window should end the live session cleanly.
- Background analysis should stop cleanly when the app is closed.
- Reopening the app should not silently resume abandoned prior work without a new explicit user trigger.

## Schedule interaction

- The Schedule page should allow clicking a schedule/Gantt activity without crashing.
- If linked schedule facts are available, they should be shown.
- If evidence is unavailable, the app should degrade gracefully and say so honestly.

## Interactive responsiveness

- Interactive chat should stay responsive even when background ingest/extract work exists.
- Background backlog should yield to active chat use in the mounted workflow.

## Current release honesty checkpoint

Current authority after the latest evidence rail:

```text
main includes PR #121
latest main SHA: e5bdf53913cd25ac464ce36feb98ff3ab66b0065
latest completed packet: #120 / PR #121 — P6 relation uniqueness/fidelity proof
```

Completed and test-locked behavior includes:

- Workspace Honesty:
  - mounted chat is bound to the active project/session;
  - support-only answers are labeled as support, not certified truth;
  - snapshot/imported-date wording is informational only;
  - cross-project answer leakage has regression coverage.
- Engineering Evidence:
  - PDF metadata completeness and routing are test-locked;
  - IFC missing dependency behavior is honest and has no fallback parser claim;
  - Word/PPTX/DGN extraction is flattened deterministic extraction, not typed Office/CAD persistence;
  - Excel extraction is register/log-row oriented, not generic workbook semantic persistence;
  - P6 critical-path unknown handling does not convert unknown into false/zero facts;
  - P6 relation fidelity preserves distinct relation rows with different type or lag.

Current explicit limitations:

- No final publish pass has been issued.
- No packaging rebuild is authorized by this README.
- No CPM engine is implemented.
- No Schedule Truth Workspace implementation is complete.
- No PDF VLM routing is enabled.
- No typed Office/CAD persistence is implemented.
- No generic Excel workbook semantic persistence is implemented.
- No IFC fallback parser is enabled when `ifcopenshell` is missing.
- No autonomous chat tool execution, MCP integration, or runtime provisioning/download/control is enabled.
- `docs/total-quality-upgrade-v3-3` remains preserved as future planning only, not current release authority.

Before a publish pass, run the final local Windows release test and packaging proof.

See:

```text
docs/internal/PUBLISH_TRUTH_STATEMENT.md
```
