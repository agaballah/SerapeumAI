# DOCS_AUDIT — Snapshot vs Updated Canonical Docs

This audit is based on `combined_docs_snapshot.md` (your provided snapshot) and explains:
- what’s current vs obsolete,
- what was upgraded to match the current product intent,
- what was previously aligned but got downgraded by later docs.

> Important: This audit does **not** try to “perfect” the product story. It identifies contradictions and removes user-facing claims that are not aligned with the current documentation rules.

---

## A) Snapshot contradictions (what cannot all be true)

### 1) Installation & model runtime conflicts
The snapshot presents **multiple incompatible** install stories:

- Story A: “Install LM Studio” and “start the local server on port 1234”, plus “run SerapeumAI_Setup.exe”. (snapshot)  
- Story B: “Run python run.py”, plus CLI helpers and seed scripts. (snapshot)  
- Story C: “Model download is automatic / embedded, no manual setup required.” (snapshot)

Only one of these can be the canonical user path.

---

## B) What we treat as CURRENT (and keep in the updated docs)

Based on recurring themes in the snapshot:
- Projects + document ingestion
- Chat with citations
- Compliance tab flow (select standard → analyze → review findings)
- Graph tab/view for cross-document links
- Vision/OCR support for scanned PDFs/drawings

These are explicitly described in the snapshot’s user-facing feature sections and release notes.

---

## C) What we treat as OBSOLETE for user-facing docs (and removed)

### 1) EXE installer steps
Anything describing `SerapeumAI_Setup.exe` is removed from canonical user docs because your current doc rules require a single run path.

### 2) Terminal/CLI-heavy quick reference
The archived quick reference includes multiple CLI-only flows (dependency install commands, headless pipeline runner, seeding scripts, etc.).  
Those are not user documentation and conflict with your current “no CLI language” direction for the README.

### 3) Internal architecture proposals and phase roadmaps
The snapshot includes extensive architecture plans and roadmaps under `docs/archive/`.  
These are internal, not user docs, and they actively confuse the product boundary.

---

## D) What we UPGRADED to match the intent (without over-promising)

### 1) One canonical run path
Updated docs only describe running the app via `python run.py`.

### 2) Removed internal implementation references
Updated docs contain **no module names, no code snippets, no internal file paths**, and no architecture diagrams.

### 3) Tightened claims around compliance
Updated docs treat compliance output as “review assistance with evidence”, not certification.

---

## E) What was aligned before but got downgraded in later docs

### “User-first flow” got polluted by internal engineering guidance
Some snapshot docs are written for developers/maintainers and include:
- dependency install commands
- seeding scripts
- headless execution
- internal troubleshooting steps

That content tends to leak into user docs, making them harder to follow.

---

## F) Result: canonical user-facing documentation set

The updated “public” doc set is now:
- README.md
- docs/USER_MANUAL.md
- docs/SYSTEM_REQUIREMENTS.md
- docs/TROUBLESHOOTING.md
- PRODUCT_INTENT.md

Everything else should be considered internal, archival, or future-facing unless explicitly maintained.
