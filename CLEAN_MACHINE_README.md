# Clean-Machine Acceptance Test — README

## What This Is

A two-stage acceptance test for the frozen SerapeumAI v0.3 portable package.
It proves the EXE runs correctly on a genuinely clean Windows machine with no
Python, Git, or development tooling present.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  STAGE 1 — GitHub Actions (automated, headless)       │
│  • Downloads frozen ZIP from release asset            │
│  • Verifies ZIP SHA-256                               │
│  • Verifies EXE SHA-256                               │
│  • Checks for prohibited content in package           │
│  • Launches SerapeumAI.exe on runner                  │
│  • Measures startup time                              │
│  • Parses serapeum.log for errors / exceptions        │
│  • Checks filesystem before/after for contamination   │
│  • Uploads logs + FS snapshots as artifacts           │
│  • GATES Stage 2                                      │
└──────────────────────────────────────────────────────┘
                          │
                          ▼ (Stage 1 must PASS)
┌──────────────────────────────────────────────────────┐
│  STAGE 2 — Disposable Windows VM (GUI, interactive)   │
│  • Fresh Windows 11 Pro VM (Azure / AWS / local)     │
│  • Copy 7-item acceptance packet                     │
│  • Run Phase 0 baseline script                        │
│  • Execute Phases 1–12 per CLEAN_MACHINE_TEST_PLAN    │
│  • Capture screenshots at each gate                   │
│  • Compile report using CLEAN_MACHINE_TEST_REPORT     │
│  • Destroy VM                                         │
└──────────────────────────────────────────────────────┘
```

## File Inventory

| File | Purpose |
|------|---------|
| `.github/workflows/clean-machine-acceptance.yml` | Stage 1 GitHub Actions workflow |
| `CLEAN_MACHINE_TEST_PLAN.md` | Full 12-phase test procedure |
| `CLEAN_MACHINE_TEST_CHECKLIST.md` | Printable step-by-step tracker |
| `CLEAN_MACHINE_TEST_REPORT_TEMPLATE.md` | Final report template |
| `CLEAN_MACHINE_OPERATOR_PROCEDURE.md` | Operator instructions for Stage 2 |
| `scripts/CLEAN_MACHINE_PHASE0_BASELINE.ps1` | Phase 0 automated baseline collection |
| `CLEAN_MACHINE_ARCHITECTURE_RECOMMENDATION.md` | Route analysis and recommendation |
| `CLEAN_MACHINE_ARCHITECTURE_INVESTIGATION.md` | Detailed investigation findings |

## Frozen Artifacts (Untouched)

| Item | Location | SHA-256 |
|------|----------|---------|
| Portable ZIP | `dist/SerapeumAI_v0.3_colleague_test.zip` | `69457B13...` |
| EXE (inside ZIP) | `SerapeumAI.exe` | `8D521DDA...` |
| Test corpus | `_LOCAL_TEST_CORPUS/RELEASE_ACCEPTANCE_V1/` | 23 files |

## How to Trigger Stage 1

### On a new release (automatic)

Publish a GitHub release and attach `SerapeumAI_v0.3_colleague_test.zip` as a release asset named exactly `SerapeumAI_v0.3_colleague_test.zip`. The workflow triggers automatically.

### Manually (dispatch)

```
Actions tab → Clean-Machine Acceptance Test (Stage 1 — Automated) → Run workflow
```

Optional inputs:
- `zip_path` — if the ZIP is already in the repo at an unusual path
- `expected_zip_sha256` — override the expected hash
- `expected_exe_sha256` — override the expected EXE hash

### From the command line (gh CLI)

```powershell
gh workflow run clean-machine-acceptance.yml \
  -f zip_path=dist/SerapeumAI_v0.3_colleague_test.zip
```

## How to Trigger Stage 2

Stage 2 requires a disposable Windows VM. Follow the procedure in
`CLEAN_MACHINE_OPERATOR_PROCEDURE.md`.

Prerequisites for the VM:
- Windows 11 Pro (22H2 or later stable build)
- RDP access
- No Python, Git, or development tools pre-installed
- ≥ 40 GB disk, ≥ 8 GB RAM recommended

## Evidence Collection Summary

| Channel | Stage 1 (headless) | Stage 2 (GUI VM) |
|---------|--------------------|------------------|
| Startup time | ✅ Process timing | ✅ Stopwatch |
| Filesystem changes | ✅ FS snapshot diff | ✅ FS snapshot diff |
| Application logs | ✅ Log file parse | ✅ Log file parse |
| Dependency detection | ⚠️ `where.exe` (runner has Python+Git) | ✅ `where.exe` (clean env) |
| Import/extraction results | ❌ Not automated in Stage 1 | ✅ SQLite query + UI |
| Database integrity | ❌ Not automated in Stage 1 | ✅ PRAGMA check |
| Exceptions/errors | ✅ Log pattern search | ✅ Log + UI error dialogs |
| Shutdown / exit code | ✅ `$LASTEXITCODE` | ✅ Exit code + data persistence |
| Screenshots | ❌ No display | ✅ At each phase boundary |
| GUI interaction | ❌ Not possible | ✅ Full File Inspector / Facts / Chat |

**Known Stage 1 deviation:** GitHub-hosted `windows-latest` runners have Python and Git pre-installed. The workflow records their presence but does not treat them as failures — they are documented as a known headless-environment limitation. A truly clean machine check requires Stage 2.

## Gate Reference

Stage 1 gates apply to the automated headless checks; Stage 2 gates apply to the full GUI acceptance run.

| Gate | Stage 1 Check | Stage 2 Condition | Action if FAIL |
|------|---------------|-------------------|----------------|
| 1 — ZIP | Hash matches, extraction succeeds | Same | STOP — artifact issue |
| 2 — Launch | EXE starts within 90s, no unhandled exception | Main window renders within 60s, no fatal dialog | STOP — app failure |
| 3 — Init | `.serapeum/` created, `serapeum.log` written | `.serapeum/` created, global DB initialized | STOP — app failure |
| 4 — Project | N/A (not applicable) | New project opens, SQLite created | STOP — app failure |
| 5 — Import | N/A (not applicable) | All supported formats import | Continue with per-doc notes |
| 6 — Inspector | N/A (requires GUI) | File Inspector opens | STOP — app failure |
| 7 — Provenance | N/A (requires GUI) | Non-null provenance on records | STOP — app failure |
| 8 — Facts | N/A (requires GUI) | Certification/rejection succeeds | STOP — app failure |
| 9 — Chat | N/A (requires GUI) | No crash when LM Studio absent | STOP — app failure |
| 10 — Shutdown | Clean process termination recorded | Clean exit, data persists on reopen | STOP — app failure |

## Running on This Repository

To enable automatic Stage 1 execution on every release:

1. Ensure `dist/SerapeumAI_v0.3_colleague_test.zip` is the artifact produced by `build_portable.bat`
2. Attach the ZIP as a release asset named exactly `SerapeumAI_v0.3_colleague_test.zip`
3. The workflow reads the asset, verifies hashes, launches the EXE, and reports

No other repository changes are required.

---

*No source code was modified. No dependencies were changed. No frozen artifacts were altered.*
