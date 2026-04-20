# Windows Release Proof Kit

This document captures the final Windows proof targets for the mounted shipped product in this repo artifact.

## Dashboard honesty
- Human Certified must not show `GOLDEN` when the count is zero.
- System Validated must not show `TRUSTED` when the count is zero.
- P6 quality must surface a limitation when float data is missing and critical path is therefore unknown.

## File Inspector semantics
- Tab 1: Consolidated Review
- Tab 2: Full Metadata
- Tab 3: Raw Deterministic Extraction
- Tab 4: AI Output Only

## Expert Chat
- Positive sourced answer when grounded project material exists.
- Full refusal only when no project-grounded material exists in any lane.
- project-only retrieval on the mounted answer path.
- main visible response is answer-first.
- evidence stays behind the optional **Show Evidence** surface.
- Chat history should reset when the active project closes or changes.
- Chat history should reset when the active project closes or changes.

## Facts review
- Facts page remains the mounted review workspace.
- Certify and Reject remain meaningful and evidence-informed.

## P6 truth
- predecessor / successor logic must be preserved.
- float and critical-path output must be materially correct when source float exists.
- if source float is absent, the limitation must be surfaced honestly.

## Packaging and runtime parity
This repo artifact does not include packaging scripts or spec files in the root, so packaged-run proof must be executed against the maintained packaging assets used by the operator. The runtime parity checks still apply to the built package:
- LM Studio contract
- dashboard honesty
- project-only retrieval
- Facts-page review behavior
- File Inspector semantics
- answer-first Expert Chat behavior
- Show Evidence behind-the-scenes evidence view


## Clean shutdown
- Red-X close should internally close the project before destroying the app window.
- Closing the app should end the live session cleanly.
- No continued page analysis after the window is destroyed.
- No repeated Tk callback errors after close.

## Schedule interaction
- Clicking a schedule/Gantt bar must not crash.
- If linked schedule facts exist, they should be shown.
- If they do not exist, the app must degrade gracefully and say so honestly.


## Interactive responsiveness
- Interactive chat should stay responsive even when background ingest/extract work exists.
- Background backlog should yield to active chat use in the mounted workflow.


## Interactive priority over backlog
- While Expert Chat is active, background backlog should yield instead of effectively stalling the chat experience.
- Low-VRAM backoff loops from background work should not dominate the user-facing chat session.


- Mounted chat history resets when the active project closes or changes.
