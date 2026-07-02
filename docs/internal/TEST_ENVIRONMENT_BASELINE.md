# R2 - Test Environment and Dependency Baseline Audit

## Task class

test task / release hygiene task

## Status

R2 baseline recorded after issue #146.

This document is an internal control note. It records repository and environment observations from the R1 follow-up audit only. It does not implement the Runtime Setup Wizard, benchmarks, provider adapters, packaging behavior, or dependency upgrades.

## Why this exists

R1 exposed that the repository did not yet have a controlled local test/dependency baseline for wider Windows test runs.

Observed during R1 verification:

- `pytest` was not initially available in the active Python environment.
- A temporary local virtual environment was created and then removed by owner instruction.
- Collection failures surfaced missing runtime/test imports such as `requests`, `customtkinter`, `PyYAML`/`yaml`, `pandas`, `pypdf`, `PyMuPDF`/`fitz`, and `pytesseract`.
- The original R1 test imported `MainApp` and pulled the full UI/runtime/extraction stack.
- PR #145 repaired that specific R1 test by making it dependency-light.

## Current repo truth

The public `README.md` and `INSTALL.md` currently document local development as:

```powershell
python run.py
```

This checkout does not contain `requirements-dev.txt`.

This audit did not add or modify `src/domain/models`; that package is part of the existing tracked repository layout.

Python and pytest verification are currently blocked in this local session because invoking `python.exe` fails with a Windows logon-session error before the requested checks can start.

This note is not a reproducible setup recipe and should not be cited as proof that wider local pytest coverage is available on every Windows machine. For current reporting lanes and honest test-result wording, use `docs/internal/DEVELOPER_TEST_BOOTSTRAP.md`.
