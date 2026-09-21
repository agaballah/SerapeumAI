# RC2 CLEAN REPRODUCTION REPORT

## Summary

**RC2 CLEAN REPRODUCTION — PASS**

The tagged release `v0.2.0-rc2` (commit `c7f299fad601b3a6fc9637571ac1ae17681416e3`) **independently reproduces** from a clean checkout. All required production source files are present, tests pass, migrations apply, and the Portable package builds successfully.

---

## Release Identity

| Field | Value |
|-------|-------|
| Tag | `v0.2.0-rc2` |
| Commit SHA | `c7f299fad601b3a6fc9637571ac1ae17681416e3` |
| Commit Message | `release: v0.2.0-rc2 — restore required domain models` |
| Branch | `feature/cad-dxf-intelligence-v1` |

---

## Clean-Clone Path

```
D:\SerapeumAI_RC2_Clean
```

Created via: `git clone D:\SerapeumAI D:\SerapeumAI_RC2_Clean --no-local --no-hardlinks` then `git checkout v0.2.0-rc2`

---

## Clean Git Status

```text
HEAD detached at c7f299f
nothing to commit, working tree clean
```

Verification:
- ✅ Tag `v0.2.0-rc2` points to `c7f299fad601b3a6fc9637571ac1ae17681416e3`
- ✅ Working tree is clean (no untracked/modified files)
- ✅ No `.kilo/` directory present
- ✅ No developer working files (experiments/, benchmark/, corpus/, etc.)
- ✅ **Required source `src/domain/models/` present with all 3 files**

---

## Source File Verification

| Path | Status |
|------|--------|
| `src/domain/models/__init__.py` | ✅ Present (47 bytes) |
| `src/domain/models/page_record.py` | ✅ Present (2,383 bytes) |
| `src/domain/models/relationship_types.py` | ✅ Present (1,264 bytes) |
| `src/infra/persistence/migrations/` | ✅ 9 migration files + README |
| `SerapeumAI_Portable.spec` | ✅ Present |
| `tools/run_gold_benchmark.py` | ✅ Present |
| `src/tests/test_gold_regression_hardening.py` | ✅ Present |
| `src/tests/test_gold_regression.py` | ✅ Present |
| `src/tests/test_conflict_resolution_behavior.py` | ✅ Present |
| `src/tests/test_pdf_block_page_attribution.py` | ✅ Present |
| `src/tests/test_iter5b_support_contract_repair.py` | ✅ Present |
| `src/tests/test_ifc_dependency_contract.py` | ✅ Present |

---

## Application Import/Startup Validation

```powershell
py -c "from src.infra.persistence.database_manager import DatabaseManager; print('DatabaseManager import OK')"
```
**Result**: ✅ **OK** — No `ModuleNotFoundError` for `src.domain.models`

---

## Test Results

| Test Module | Result | Details |
|-------------|--------|---------|
| `test_conflict_resolution_behavior.py` | ✅ **10/10 passed** | All conflict resolution behavior tests pass |
| `test_pdf_block_page_attribution.py` | ✅ **1 passed, 3 skipped** | Core test passes; corpus-dependent tests skipped |
| `test_gold_regression_hardening.py::TestAdmissionGate` | ✅ **9/9 passed** | All admission gate tests pass (validates `tools/run_gold_benchmark.py` import) |
| `test_gold_regression.py` | ✅ **7 passed, 22 skipped** | Trust/WP05A tests pass; corpus-dependent tests skipped |
| `test_iter5b_support_contract_repair.py` | ✅ **24/24 passed** | All routing/extraction contract tests pass |
| `test_ifc_dependency_contract.py` | ✅ **4/4 passed** | All IFC dependency contract tests pass |

**Total**: 55 passed, 25 skipped (skipped = corpus-dependent tests requiring test fixtures not in release)

---

## Migration Validation

```powershell
py -c "from src.infra.persistence.global_db_initializer import ensure_global_db, global_db_path; from pathlib import Path; app_root = Path.cwd(); gdb_path = global_db_path(app_root); ensure_global_db(gdb_path, app_root); print(f'Global DB initialized at: {gdb_path}')"
```

**Result**: ✅ **OK** — Global database initialized at `D:\SerapeumAI_RC2_Clean\.serapeum\global.sqlite3` with all 9 migrations applied

---

## Portable Build

**Command**:
```powershell
cd D:\SerapeumAI_RC2_Clean
py -m PyInstaller --clean --noconfirm SerapeumAI_Portable.spec
```

**Result**: ✅ **Build complete** — No errors, PyInstaller completed successfully

**Warnings**: Only expected warnings (mypyc modules not found — normal for pure Python packages)

---

## Artifact Sizes & Hashes

### EXE
- **Path**: `D:\SerapeumAI_RC2_Clean\dist\SerapeumAI_Portable\SerapeumAI.exe`
- **Size**: 22,924,234 bytes
- **SHA-256**: `B60F994CEA890A69FE7F216793DA7AEEA818760B7FC446A9C877D88DA1674049`

### Portable Package (ZIP)
- **Path**: `D:\SerapeumAI_RC2_Clean\SerapeumAI_Portable_v0.2.0-rc2.zip`
- **Size**: 108,240,050 bytes
- **SHA-256**: `A941EA95FE580D5CCCA03CE6927F40BC1947ED2842AEC2F9C8C5FB017F885FC1`

---

## Comparison: RC1 vs RC2 Clean Builds

| Metric | RC1 (v0.2.0-rc1) | RC2 (v0.2.0-rc2) | Status |
|--------|------------------|------------------|--------|
| Commit SHA | `b69bbd4ce2fece5ac1e4a0badf2eb0f923a07cf8` | `c7f299fad601b3a6fc9637571ac1ae17681416e3` | Different (boundary repair) |
| `src/domain/models/` | ❌ **MISSING** (gitignored) | ✅ **PRESENT** | **FIXED** |
| EXE Size | 22,906,125 bytes | 22,924,234 bytes | ~same (18 KB diff) |
| EXE SHA-256 | `6F5F793A3B5F158B1302C9B323775433E657CEE413330F305307073EEE6F18FF` | `B60F994CEA890A69FE7F216793DA7AEEA818760B7FC446A9C877D88DA1674049` | Different (expected) |
| ZIP Size | 108,221,377 bytes | 108,240,050 bytes | ~same (18 KB diff) |
| ZIP SHA-256 | `AD5E73CFA0893F0E70AA3CF198CD0CC4AD7BE26E39F7B1EC9F710A2EECA19059` | `A941EA95FE580D5CCCA03CE6927F40BC1947ED2842AEC2F9C8C5FB017F885FC1` | Different (expected) |
| Test Suite | FAIL (import error) | ✅ **PASS** | **FIXED** |
| Migrations | FAIL (import error) | ✅ **PASS** | **FIXED** |

---

## Key Differences from RC1

1. **Root cause fixed**: `.gitignore` now has negation rule `!src/domain/models/` allowing the required production source to be tracked
2. **3 source files added**: `src/domain/models/{__init__.py, page_record.py, relationship_types.py}` (134 lines total)
3. **All imports work**: `DatabaseManager` and all downstream modules import successfully
4. **All tests collect and pass**: No collection errors, all relevant test suites pass
5. **Migrations apply**: Global DB initializes with all 9 migrations
6. **Artifacts reproducible**: EXE and ZIP built from clean clone match expected structure

---

## Limitations Noted

1. **Corpus-dependent tests skipped**: 25 tests skipped across suites because they require test fixtures (`corpus/`, `GOLD_*.dxf`) that are correctly excluded from the release
2. **EXE/ZIP hashes differ from RC1**: Expected — different commit, different build timestamps, PyInstaller non-determinism
3. **Matplotlib/mypyc warnings**: Normal PyInstaller warnings for optional compiled extensions not present
4. **Deprecation warnings in tests**: `datetime.utcnow()` usage — pre-existing, not a release blocker

---

## Conclusion

**RC2 CLEAN REPRODUCTION — PASS**

The complete validation chain passes:
1. ✅ Tag resolves to correct commit (`c7f299f`)
2. ✅ All required production source present (especially `src/domain/models/**`)
3. ✅ Migrations, packaging, tests, benchmark tooling all present
4. ✅ Application imports/startup succeed (`DatabaseManager` import OK)
5. ✅ Full relevant test suite passes (55 tests)
6. ✅ Migrations apply successfully
7. ✅ Portable RC builds from clean clone only
8. ✅ Portable package validated (size, SHA-256 recorded)

No files were copied from the original `D:\SerapeumAI` worktree. The clean clone is completely independent.

---

*Report generated: 2026-09-17*
*Validation environment: Windows 11, Python 3.12.10, PyInstaller 6.22.3*
*Clean clone path: `D:\SerapeumAI_RC2_Clean`*