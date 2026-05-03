# Contributing

SerapeumAI is a Windows-first, local-first AECO review workspace. Contributions must preserve the product's truth, evidence, and packaging discipline.

## Repository rules

- Treat `src/**` as the primary editable code surface.
- Edit `run.py` and `run_tests.py` only when needed.
- Treat these packaging files as sensitive:
  - `SerapeumAI_Portable.spec`
  - `build_portable.ps1`
  - `build_portable.bat`
- Do not treat these as normal editing targets:
  - `build/**`
  - `dist/**`
  - `.serapeum/**`
  - `models/**`
  - `**/__pycache__/**`
- Avoid dependency additions or upgrades unless explicitly approved.
- Preserve Windows portability and packaged-app behavior.
- Prefer minimal, reviewable diffs.

## Product rules

- Deterministic extraction and AI-generated support must remain separated.
- Trusted facts are stronger than retrieval/vector support.
- Vector stores are derived support, not truth authority.
- AI Output Only is non-governing unless promoted through review/certification.
- Do not introduce claims of guaranteed legal, contractual, regulatory, or compliance approval.

## Pull request expectations

Each PR should include:

- task class;
- files touched;
- risk frame;
- verification steps;
- whether packaging or Windows behavior is affected;
- rollback notes.

## Verification

Use focused tests for bounded changes. For release-sensitive changes, include Windows-specific proof when relevant.
