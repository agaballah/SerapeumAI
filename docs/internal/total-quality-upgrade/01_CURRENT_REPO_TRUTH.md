# 01 — Current Repo Truth

## Status

Template to complete before Total Quality Upgrade implementation starts.

## Purpose

This document freezes what the app actually is before the upgrade begins. It prevents planning from drifting into assumptions, roadmap ambition, or detached code paths.

## Required audit sections

### 1. Visible product surfaces

Record which UI surfaces are mounted and usable today.

- Dashboard:
- Documents:
- File Inspector / Document Center:
- Facts / review:
- Chat:
- Schedule:
- DB inspector:
- Settings/runtime setup:

### 2. Current extension support

For each extension, record whether behavior is supported, partial, experimental, unsupported, or unknown.

- PDF:
- DOCX/DOC:
- XLSX/XLS:
- PPTX/PPT:
- IFC:
- XER:
- DGN/DWG/DXF:
- PNG/JPG/JPEG:
- TXT/CSV:
- Unknown:

### 3. Current truth behavior

Record evidence for:

- fact states available,
- fact retrieval behavior,
- coverage/refusal behavior,
- candidate fact containment,
- human certification behavior,
- lineage visibility,
- snapshot/as-of behavior.

### 4. Current chat behavior

Record whether mounted chat is:

- active-project-bound,
- snapshot-aware,
- facts-first,
- evidence-linked,
- refusal-capable,
- protected from cross-project leakage,
- protected from unsupported fluent answers.

### 5. Current documentation state

Record public and internal documentation status:

- README:
- LICENSE:
- ROADMAP:
- CHANGELOG:
- LIMITATIONS:
- PRIVACY:
- SYSTEM_REQUIREMENTS:
- TROUBLESHOOTING:
- docs/:
- .github/:

### 6. Current packaging/runtime state

Record what is proven and what is not:

- run path:
- packaged path:
- LM Studio/runtime assumptions:
- local model assumptions:
- dependency assumptions:
- Windows-specific risks:

### 7. Current tests

Record test surfaces that already exist and what they prove.

### 8. Known blockers

List verified blockers only. Do not include guesses without evidence.

## Exit condition

This document is complete only when every major repo claim used by the upgrade is backed by current source/runtime/documentation evidence.
