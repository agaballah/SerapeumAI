# SerapeumAI

SerapeumAI is a Windows-first, local-first AECO review workspace.

It helps engineers and reviewers:
- ingest project files into a project workspace
- inspect deterministic extraction and AI analysis separately
- review facts on the Facts page with lineage / evidence support
- ask questions in Expert Chat and get a direct answer first, with optional evidence behind it

SerapeumAI is **review assistance** with evidence and provenance. It is **not** a guaranteed-compliance or approval engine.

## Run

Use one clear dev run path:

```powershell
python run.py
```

## Runtime contract

- Windows is the baseline platform.
- LM Studio must be installed and running locally.
- The publish generative runtime is the single model `qwen2.5-coder-7b-instruct`.
- Embeddings remain separate from the generative model.

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
  - resets visible chat history when the active project closes or changes

Chat history should reset when the active project closes or changes.
  - exposes these evidence lanes only when expanded:
    - Trusted Facts
    - Extracted Evidence
    - Linked Support
    - AI-Generated Synthesis

## Trust and provenance

- Trusted Facts remain the strongest source class.
- AI-generated synthesis is clearly labeled non-governing.
- Linked Support is clearly labeled non-trusted candidate support.
- When trusted facts are incomplete, SerapeumAI may still answer from grounded extraction or linked support and will label that source class explicitly.


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

## Interactive priority over backlog
- Interactive chat should stay responsive even when background ingest/extract work exists.
- Background backlog should yield to active chat use in the mounted workflow.


- Mounted chat history resets when the active project closes or changes.
