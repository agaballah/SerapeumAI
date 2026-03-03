# Documentation audit findings (contradictions, gaps, and drift)

Scope: compare the **canonical user-facing set** (see [`README.md`](README.md:1)) against root-level working notes and `docs/archive/`.

Primary constraint: the red lines in [`PRODUCT_INTENT.md`](PRODUCT_INTENT.md:1) define what should appear in user docs.

## 1) Major contradictions (cannot all be true)

### A. Product model: truth-engine vs RAG-style assistant

- Working notes and specs (notably [`build bible.txt`](build bible.txt:1), [`full user journey  user flow.txt`](full user journey  user flow.txt:1)) describe a strict system:
  - answers only from certified facts
  - coverage checks
  - validation queue
  - job plan on refusal

- Canonical user manual ([`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1)) describes a more conventional pipeline + chat + citations model and does **not** introduce certified facts, coverage gating, or a validation workflow.

Risk: stakeholders may assume strict fact gating exists (because multiple journey docs say it), but users will not see it in the manual.

### B. Run and install story

Canonical rule: one run path for user-facing docs: `python run.py`.

- Canonical docs follow this (see [`README.md`](README.md:17), [`PRODUCT_INTENT.md`](PRODUCT_INTENT.md:51)).
- Archive documents include multiple incompatible stories: installer exe, CLI-heavy flows, and “automatic model download” claims.
  - Example: [`docs/archive/QUICK_REFERENCE.md`](docs/archive/QUICK_REFERENCE.md:14) claims automatic model download and includes CLI commands.

Risk: users/devs copy archive steps and end up with mismatched expectations.

### C. LLM runtime and model management

- Archive FAQ suggests LM Studio is the supported model host (see [`docs/archive/FAQ.md`](docs/archive/FAQ.md:21)).
- Archive technical docs suggest embedded inference (see [`docs/archive/TECHNICAL_OVERVIEW.md`](docs/archive/TECHNICAL_OVERVIEW.md:30)).
- Current repo includes local model files under [`models/`](models/README.md:1) and a download instructions file [`models/DOWNLOAD_INSTRUCTIONS.md`](models/DOWNLOAD_INSTRUCTIONS.md:1), but the canonical user docs do not clearly define:
  - where models live
  - whether the app downloads them
  - how model selection relates to those files

Risk: confusion around model setup and “model not detected” failures.

### D. Feature claims vs canonical scope

Examples of archive claims that are not substantiated in the canonical user docs:

- Role and discipline selection (appears in archive docs; only hinted in user manual as optional controls) (see [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:165)).
- “Verified calculations” and webhook tools (appears in [`docs/archive/TECHNICAL_OVERVIEW.md`](docs/archive/TECHNICAL_OVERVIEW.md:15)).
- Hard promises like “production ready” and “tests passing” in [`docs/archive/DOCUMENTATION_INDEX.md`](docs/archive/DOCUMENTATION_INDEX.md:4).

Risk: marketing-like claims leak into user expectations.

## 2) Gaps in canonical docs (what a user might still not understand)

### A. Storage location and project data footprint

User manual mentions confirming a default storage location (see [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:57)) but does not document:

- what is stored where
- rough disk growth drivers (indexes, OCR caches)
- what can be deleted safely

System requirements covers storage size but not the layout.

### B. Processing stages and terminology alignment

The manual uses high-level stage terms (ingest, vision, indexing, analysis) (see [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:103)) but does not define:

- what each stage produces
- what “done” means
- which features depend on which stages (chat vs compliance vs graph)

### C. Exports

Export is described as “depending on build” (see [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:268)) without:

- clear availability matrix
- file formats and where exports go

## 3) Drift signals across docs (things to quarantine)

These archive docs are high-risk to be misread as current user guidance:

- CLI quick reference: [`docs/archive/QUICK_REFERENCE.md`](docs/archive/QUICK_REFERENCE.md:1)
- FAQ with strong claims: [`docs/archive/FAQ.md`](docs/archive/FAQ.md:1)
- Phase status docs with numeric claims: [`docs/archive/DOCUMENTATION_INDEX.md`](docs/archive/DOCUMENTATION_INDEX.md:1)
- Older technical overview: [`docs/archive/TECHNICAL_OVERVIEW.md`](docs/archive/TECHNICAL_OVERVIEW.md:1)

Recommendation: mark them as historical at the top, and ensure canonical docs are the only ones linked from `README`.

## 4) Alignment notes (what is already consistent)

- Canonical docs are consistent on:
  - Windows-first
  - local-first / privacy-first framing
  - evidence and citations as safety rails
  - compliance is assistance not certification

Sources: [`README.md`](README.md:1), [`PRODUCT_INTENT.md`](PRODUCT_INTENT.md:61), [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:220)

