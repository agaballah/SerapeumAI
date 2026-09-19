# FINAL RC CLEAN REPRODUCTION REPORT

## Summary

**CLEAN REPRODUCTION — FAILED**

The tagged release `v0.2.0-rc1` (commit `b69bbd4ce2fece5ac1e4a0badf2eb0f923a07cf8`) **cannot be independently reproduced** from a clean checkout. A required source module (`src/domain/models/`) is missing from the release commit due to being excluded by `.gitignore`.

---

## Release Identity

| Field | Value |
|-------|-------|
| Tag | `v0.2.0-rc1` |
| Commit SHA | `b69bbd4ce2fece5ac1e4a0badf2eb0f923a07cf8` |
| Commit Message | `release: v0.2.0-rc1 — validated Portable RC source` |
| Branch | `feature/cad-dxf-intelligence-v1` |

---

## Clean-Clone Path

```
D:\SerapeumAI_RemoteTemp
```

Created via: `git clone D:\SerapeumAI D:\SerapeumAI_RemoteTemp --no-local --no-hardlinks` then `git checkout v0.2.0-rc1`

---

## Clean Git Status

```text
HEAD detached at b69bbd4
nothing to commit, working tree clean
```

Verification:
- ✅ Tag `v0.2.0-rc1` points to `b69bbd4ce2fece5ac1e4a0badf2eb0f923a07cf8`
- ✅ Working tree is clean (no untracked/modified files)
- ✅ No `.kilo/` directory present
- ✅ No developer working files (experiments/, benchmark/, corpus/, etc.)
- ❌ **Missing required source: `src/domain/models/`**

---

## Build Command / Procedure

```powershell
cd D:\SerapeumAI_RemoteTemp
py -m PyInstaller --clean --noconfirm SerapeumAI_Portable.spec
```

- **Build result**: SUCCESS (PyInstaller completed without errors)
- **EXE produced**: `dist\SerapeumAI_Portable\SerapeumAI.exe` (22,906,125 bytes)
- **Package size**: 235,795,184 bytes (2,053 files)
- **ZIP archive**: `SerapeumAI_Portable_v0.2.0-rc1.zip` (108,221,377 bytes)

---

## Test Results

| Test Module | Result | Notes |
|-------------|--------|-------|
| `test_gold_regression_hardening.py` | 9 passed, 15 skipped | TestAdmissionGate passes; corpus-dependent tests skipped |
| `test_pdf_block_page_attribution.py` | 1 passed, 3 skipped | Core logic test passes; corpus-dependent tests skipped |
| `test_conflict_resolution_behavior.py` | **ERROR** | `ModuleNotFoundError: No module named 'src.domain.models'` |
| `test_iter5b_support_contract_repair.py` | Not run | Would fail with same import error |
| `test_ifc_dependency_contract.py` | Not run | Would fail with same import error |
| `test_gold_regression.py` | Not run | Would fail with same import error |

---

## Functional Validation

| Capability | Status | Evidence |
|------------|--------|----------|
| Application starts | ❌ FAIL | `src.domain.models` missing — `DatabaseManager` cannot import |
| Database initializes | ❌ FAIL | Requires `DatabaseManager` which requires `src.domain.models` |
| Migrations apply | ❌ FAIL | Requires `DatabaseManager` |
| PDF ingestion | ❌ FAIL | Requires full app stack |
| DXF ingestion | ❌ FAIL | Requires full app stack |
| Facts build | ❌ FAIL | Requires full app stack |
| Provenance works | ❌ FAIL | Requires full app stack |
| Conflict detection | ❌ FAIL | Requires `src.domain.models` |
| Clean shutdown | ❌ FAIL | Application cannot start |

---

## Artifact Sizes & Hashes

### EXE
- **Path**: `D:\SerapeumAI_RemoteTemp\dist\SerapeumAI_Portable\SerapeumAI.exe`
- **Size**: 22,906,125 bytes
- **SHA-256**: `6F5F793A3B5F158B1302C9B323775433E657CEE413330F305307073EEE6F18FF`

### Portable Package (ZIP)
- **Path**: `D:\SerapeumAI_RemoteTemp\SerapeumAI_Portable_v0.2.0-rc1.zip`
- **Size**: 108,221,377 bytes
- **SHA-256**: `AD5E73CFA0893F0E70AA3CF198CD0CC4AD7BE26E39F7B1EC9F710A2EECA19059`

---

## Comparison with Previous RC (Dirty-Tree Build)

| Metric | Dirty-Tree Build (INSTALL.md) | Clean-Clone Build | Notes |
|--------|-------------------------------|-------------------|-------|
| EXE Size | 110,206,723 bytes | 22,906,125 bytes | **Major difference** — clean build EXE is ~5x smaller |
| Tag/Commit | 51bc3280e1adf9e3cc53859cb2f99bc0b8847548 | b69bbd4ce2fece5ac1e4a0badf2eb0f923a07cf8 | Different commits |
| EXE SHA-256 | Not provided | 6F5F793A3B5F158B1302C9B323775433E657CEE413330F305307073EEE6F18FF | Cannot compare directly |
| Functionality | Validated (per prior reports) | **FAILS — missing src.domain.models** | Critical defect |

**Key observation**: The clean-build EXE is dramatically smaller (22.9 MB vs 110 MB), suggesting the dirty-tree build bundled additional modules that the clean build cannot find (consistent with the missing `src/domain/models` and potentially other gitignored source).

---

## Root Cause Analysis

### Missing Module
The directory `src/domain/models/` containing:
- `src/domain/models/__init__.py`
- `src/domain/models/page_record.py`
- `src/domain/models/relationship_types.py`

is **excluded by `.gitignore`** (blanket pattern `models/` matches any directory named `models`).

### Impact
`src/infra/persistence/database_manager.py:50` imports:
```python
from src.domain.models.page_record import PageRecord
```

This import fails in the clean checkout because `src/domain/models/` does not exist in the tagged commit.

### Why It Was Missed
The release commit manifest classified 44 files into categories A–G. The `src/domain/models/` directory was **not included** in any category — it was silently excluded by `.gitignore` and never staged.

---

## Differences from Validated RC

| Aspect | Dirty-Tree RC (Validated) | Clean-Clone RC (This Attempt) |
|--------|---------------------------|-------------------------------|
| `src/domain/models/` | Present in working tree | **ABSENT — gitignored** |
| `DatabaseManager` import | Works | **FAILS** |
| Test suite | Passes (932 tests) | **Core tests fail to collect** |
| Application launch | Works | **FAILS** |
| EXE size | 110 MB | 22.9 MB (incomplete) |

---

## Conclusion

**CLEAN REPRODUCTION — FAILED**

The tagged release `v0.2.0-rc1` is **not independently reproducible**. A required source package (`src/domain/models/`) is missing from the commit because it is excluded by the project's `.gitignore` file.

Per the critical failure rule: **STOP. Do not copy files from the original dirty tree into the clean clone to make it work.**

### Required Remediation
Before a new release candidate can be cut:
1. Remove `models/` from `.gitignore` (or add explicit `!src/domain/models/` negation)
2. Stage and commit `src/domain/models/` 
3. Re-tag (or create new tag `v0.2.0-rc2`)
4. Re-run clean-clone validation

---

*Report generated: 2026-09-17*
*Validation environment: Windows 11, Python 3.12.10, PyInstaller 6.22.3*