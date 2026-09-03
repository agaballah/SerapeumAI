# SERAPEUMAI Development Environment Health Report v1.0
**Date:** 2026-09-02  
**Scope:** Audit and validation of local Windows development environment at `D:\SerapeumAI`  
**Validation:** After installing `ezdxf 1.4.4`, full test suite passes: 744 passed, 0 failed  
**Status:** HEALTHY — Environment is fully functional for development and testing

---

## 1. Executive Summary

The local development environment is healthier than previously assessed. The original
`TEST_ENVIRONMENT_BASELINE.md` (§"Current Status: BLOCKED") claimed that "Python and
pytest verification are currently blocked in this local session because invoking
python.exe fails with a Windows logon-session error." This assessment is **outdated and
inaccurate**. Verification reveals:

| Metric                        | Reported (Baseline)         | Actual (Audit)              |
|-------------------------------|-----------------------------|-----------------------------|
| `python` command              | Fails ("logon-session error")| Fails (App Execution Alias) |
| `py` launcher                 | Not mentioned               | Working — Python 3.12.10    |
| Python installation           | Blocked                     | Two installs: 3.11 + 3.12   |
| pytest                        | Blocked                     | Working — pytest 9.1.1      |
| Test suite                    | Unknown                     | 740 passed / 4 failed (99.5%) |
| App launch (`py run.py`)      | Unknown                     | Successfully launches       |

**Root cause of original issue:** The bare `python.exe` command on Windows 10/11 is
intercepted by the **Windows App Execution Alias** feature, which redirects to the
Microsoft Store download page. This was misidentified in the baseline document as a
"Windows logon-session error." The correct workaround is to use the `py` launcher or
to disable the alias in Windows Settings.

---

## 2. Environment Inventory

### 2.1 Python Installations

| Path                                                | Version   | Status        |
|-----------------------------------------------------|-----------|---------------|
| `C:\Users\ADWWA\AppData\Local\Programs\Python\Python312\` | 3.12.10  | **Active** (has packages) |
| `C:\Users\ADWWA\AppData\Local\Programs\Python\Python311\` | 3.11.x   | Legacy (no packages) |
| `C:\Users\ADWWA\AppData\Local\Microsoft\WindowsApps\python.exe` | N/A | App Execution Alias → Microsoft Store |

The `py` launcher resolves to Python 3.12.10 as the default (`py -0p` shows `-V:3.12 *`).

### 2.2 PATH Configuration

Both `Python311` and `Python312` directories are in PATH, which creates ambiguity.
No virtual environment is currently in use at the project root.

### 2.3 Package Manager

`uv` is **NOT installed** (`The term 'uv' is not recognized`).
`pip` is available via `py -m pip` (pip 25.0.1 on Python 3.12).

### 2.4 Installed Packages (Python 3.12)

**Core infrastructure (8 packages):**

| Package               | Version  | Status |
|-----------------------|----------|--------|
| customtkinter         | 6.0.0    | OK     |
| llama_cpp_python      | 0.3.30   | OK     |
| pandas                | 3.0.3    | OK     |
| PyMuPDF (fitz)        | 1.27.2.3 | OK     |
| pypdf                 | 6.14.2   | OK     |
| pytesseract           | 0.3.13   | OK     |
| pytest                | 9.1.1    | OK     |
| PyYAML                | 6.0.3    | OK     |
| requests              | 2.34.2   | OK     |

**Missing optional dependencies (affects specific features):**

| Package         | Impact                                      |
|-----------------|---------------------------------------------|
| `ezdxf`         | Installed (1.4.4) — was missing, resolved |
| `pynvml`        | GPU detection falls back to available: False  |
| `torch`         | GPU detection falls back to available: False  |
| `ifcopenshell`  | IFC file processing unavailable               |
| `paddleocr`     | PaddleOCR backend unavailable                |
| `Pillow (PIL)`  | Available (verified)                        |
| `numpy`         | Available (verified)                        |

### 2.5 Project Configuration Files

- `requirements.txt` — **NOT FOUND**
- `requirements-dev.txt` — **NOT FOUND**
- `pyproject.toml` — **NOT FOUND**
- `setup.py` — **NOT FOUND**
- `conftest.py` — **NOT FOUND**
- `run_tests.py` — **NOT FOUND**
- `run.py` — **FOUND** (app entry point, works correctly)

---

## 3. Test Suite Results

### 3.1 Collection

Test files: **113** in `src/tests/`  
Test collection via `py -m pytest src/tests --co -q` succeeds without errors.

### 3.2 Execution

```
py -m pytest src/tests/ -q --tb=line --no-header
```

**Result: 740 passed, 4 failed (99.5% pass rate) in 9.49s**

**Failures (all from missing `ezdxf`):**

```
FAILED src/tests/test_e2e_workflows.py::TestE2ECoreFeatures::test_xref_detector
FAILED src/tests/test_phase3_final_validation.py::TestPhase3Completion::test_phase3c3_xref_detector
FAILED src/tests/test_phase3_final_validation.py::TestPhase3Completion::test_phase3c3_xref_tree
FAILED src/tests/test_phase3_final_validation.py::TestPhase3Completion::test_phase3_all_components_present
```

All 4 failures trace to `ModuleNotFoundError: No module named 'ezdxf'` when importing
`src/document_processing/xref_detector.py`.

### 3.3 Warnings

44 deprecation warnings, all of the same form:
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal
in a future version. Use timezone-aware objects to represent datetimes in UTC.
```
These are Python 3.12+ deprecations in `job_base.py:27`, `job_queue.py:57/89`,
`ingest_file_job.py:92/115`, and `test_tool_execution_audit_contract.py:239`.
Not a blocker, but should be addressed in future cleanup.

### 3.4 Application Launch

`py run.py` successfully launches the SerapeumAI application. Verified:
- Session initialization
- Logging setup
- SQLite database creation (`global.sqlite3`)
- Migration system runs (18 migrations confirmed)
- Project database initialization
- LM Studio service connection attempt

---

## 4. Root Cause Analysis

### 4.1 The `python` Command Failure

**Issue:** `python` redirects to Microsoft Store.  
**Cause:** Windows App Execution Alias for `python.exe` is enabled at
`C:\Users\ADWWA\AppData\Local\Microsoft\WindowsApps\python.exe`.  
**Not caused by:** A Windows logon-session error (as stated in the baseline document).  
**Fix:** Use `py` launcher or disable App Execution Alias in
Settings → Apps → App execution aliases → `python` → toggle OFF.

### 4.2 Test Failures

The 4 test failures are caused by the missing `ezdxf` package, which is imported by
`src/document_processing/xref_detector.py:5` (`import ezdxf`). This is a legitimate
dependency gap — `ezdxf` is used for AutoCAD DXF file cross-reference detection.

### 4.3 GPU Detection

`src/utils/hardware_utils.py` imports `pynvml` and `torch` in try/except blocks.
Both fail with `ModuleNotFoundError`, causing GPU detection to return `available: False`.
This means the application falls back to CPU-only mode. No NVML or CUDA libraries are
available.

---

## 5. Environment Condition

**Overall: HEALTHY with minor gaps**

| Area                | Status   | Notes                              |
|---------------------|----------|------------------------------------|
| Python              | OK       | Use `py` launcher, not `python`    |
| pip/pytest          | OK       | Functional on Python 3.12.10       |
| Test collection     | OK       | All 113 test files collected       |
| Test execution      | OK (99.5%) | 740/744 pass; 4 fail (ezdxf)    |
| App launch          | OK       | `py run.py` works correctly        |
| Missing packages    | Minor    | ezdxf (tests), torch/pynvml (GPU), ifcopenshell (IFC), paddleocr (OCR) |
| Config files        | Gap      | No requirements.txt or pyproject.toml exist |
| PATH ambiguity      | Minor    | Python 3.11 and 3.12 both in PATH   |

---

## 6. Required Repair Actions

### High Priority

1. **Install `ezdxf`** — fixes 4 test failures:
   ```
   py -m pip install ezdxf
   ```

### Medium Priority

2. **Install GPU stack** (optional — only needed for GPU acceleration):
   ```
   py -m pip install pynvml torch
   ```
   Note: `torch` is large (~800MB+). Skip if CPU-only is acceptable.

3. **Install IFC processing** (optional — only needed for IFC file support):
   ```
   py -m pip install ifcopenshell
   ```

### Low Priority

4. **Install PaddleOCR** (optional — alternate OCR backend):
   ```
   py -m pip install paddleocr
   ```

5. **Create `requirements-dev.txt`** — codify the 8 installed packages as a development
   baseline. This was noted as a gap in `TEST_ENVIRONMENT_BASELINE.md` and
   `SERAPEUMAI_CURRENT_REALITY_REPORT_v1.0.md §7.4`.

6. **Disable App Execution Alias** (Windows settings) OR standardize on `py` launcher
   in documentation and CI scripts to prevent the `python` command confusion.

7. **Clean up PATH** — remove Python 3.11 from PATH (or uninstall it if no longer needed)
   to avoid ambiguity.

---

## 7. Validation Steps

To verify environment repair:

1. **Python check:**
   ```
   py --version           # Should show Python 3.12.10
   python --version       # Should also work after disabling alias
   ```

2. **Package check:**
   ```
   py -m pip list          # Verify installed packages
   py -c "import ezdxf, pynvml, torch, ifcopenshell, PIL, numpy, pytesseract, fitz"
   ```

3. **Test suite:**
   ```
   py -m pytest src/tests/ -q --tb=line --no-header
   # Expected: 744 passed, 0 failed
   ```

4. **App launch:**
   ```
   py run.py
   # Should complete initialization without import errors
   ```

---

## 8. Relevant Source References

- `src/document_processing/xref_detector.py:5` — `import ezdxf` (missing)
- `src/utils/hardware_utils.py` — imports `pynvml` and `torch` (missing, try/except)
- `src/infra/services/runtime_provider_discovery.py` — GPU detection chain
- `src/vision/ocr_backends.py` — OCR backend dispatch
- `src/tools/calculator_tool.py` — used in unit tests (working)
- `docs/internal/TEST_ENVIRONMENT_BASELINE.md` — outdated baseline (needs update)
- `docs/architecture/SERAPEUMAI_CURRENT_REALITY_REPORT_v1.0.md §7.4` — missing reqs-dev.txt noted

---

## 9. Conclusion

The development environment is **not blocked**. Python 3.12.10 is functional via the
`py` launcher, 740 of 744 tests pass, and the application launches successfully. The
original "Windows logon-session error" diagnosis in `TEST_ENVIRONMENT_BASELINE.md` is
incorrect — the actual issue is a Windows App Execution Alias redirect.

The 4 failing tests are caused by a single missing package (`ezdxf`) that can be
installed in seconds. Optional GPU/IFC/OCR packages exist for feature completeness
but are not required for core development.

**Recommendation:** Install `ezdxf` as the immediate repair. Create
`requirements-dev.txt` to prevent future recurrence. Update
`TEST_ENVIRONMENT_BASELINE.md` with corrected findings.
