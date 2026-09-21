# SerapeumAI Quality Scorecard

**Version**: 1.0  
**Date**: 2026-09-14  
**Purpose**: Measurable quality gate for all release decisions  
**Method**: Automated tests + manual verification against gold corpus

---

## Test Infrastructure

| Component | Count | Status |
|-----------|-------|--------|
| Test files | 123 | Active |
| Passing tests | 868 | ✅ All green except 2 IFC (expected) |
| Failing tests | 2 | ⚠️ Both IFC — ifcopenshell missing |
| Execution time | 163.92s | Normal |
| Warnings | 281 | Monitor (deprecation notices) |

---

## Format Quality Gates

Each format must meet minimum thresholds before release:

| Format | Minimum Score | Current | Pass? | Test Command |
|--------|--------------|---------|-------|-------------|
| PDF | ≥ 65 | 42 | ❌ | Run GOLD_0122–0126.pdf; verify text ≥8/10, tables ≥3/10 |
| DOCX | ≥ 75 | 68 | ❌ | Run GOLD_0117–0121.docx; verify text ≥9/10, links ≥5/10 |
| PPTX | ≥ 65 | 55 | ❌ | Run GOLD_0127–0131.pptx; verify slides ≥8/10, time ≤2s |
| XLSX | ≥ 70 | 60 | ❌ | Run GOLD_0142–0146.xlsx; verify rows ≥9/10, time ≤2s for 1K rows |
| DXF | ≥ 85 | 88 | ✅ | Run GOLD_0153–0155.dxf; verify entities ≥100, layers detected |
| IFC | ≥ 80 | 0 | ❌ BLOCKED | Install ifcopenshell → Run GOLD_0156–0158.ifc |
| P6/XER | ≥ 90 | 92 | ✅ | Run GOLD_0118–0120.xer; verify activities ≥50, relations ≥50 |
| Images | ≥ 55 | 45 | ❌ | Run GOLD_0082–0090.png/jpg; verify metadata + OCR |
| Structured | ≥ 65 | 70 | ✅ | Run GOLD_0008.txt through GOLD_0078.csv; verify content preserved |

### Release Gate Rule

**No release until**: All formats with gold corpus files pass their minimum score. Blocked formats (IFC, MPP, XLS) must either pass or have explicit owner waiver documenting why they're excluded.

---

## Trust Quality Gates

| Dimension | Minimum Score | Current | Pass? | Test |
|-----------|--------------|---------|-------|------|
| Evidence traceability | ≥ 80 | 65 | ❌ | Click any fact → navigate to source |
| Source navigation | ≥ 70 | 35 | ❌ | Bbox/handle/GlobalId click-through works |
| Conflict detection | ≥ 60 | 0 | ❌ | Two conflicting facts → conflict flagged |
| Refusal correctness | ≥ 70 | 48 | ❌ | Unsupported question → explicit refusal |
| Missing info handling | ≥ 65 | 22 | ❌ | Blocked format → clear warning shown |
| Revision awareness | ≥ 40 | 30 | ❌ | Re-ingest file → diff shown |
| Project isolation | ≥ 90 | 85 | ❌ | Cross-project query returns nothing |

### Trust Gate Rule

**No release until**: Overall trust score ≥ 70% (weighted average of all dimensions).

---

## AI Quality Gates

| Metric | Minimum | Current | Pass? | Test |
|--------|---------|---------|-------|------|
| Grounded answers | ≥ 85% | ~70% | ❌ | Manual review of 20 sample answers |
| Hallucination rate | ≤ 5% | ~10% | ❌ | Statistical sample testing |
| Citation correctness | ≥ 85% | ~70% | ❌ | Verify cited facts support claims |
| Project isolation | ≥ 99% | ~90% | ❌ | Automated cross-project test |
| Refusal accuracy | ≥ 75% | ~48% | ❌ | 30-scenario test suite |
| Calculation correctness | ≥ 95% | ~95% | ✅ | Tool call audit |

### AI Gate Rule

**No release until**: All AI metrics meet minimum thresholds.

---

## Regression Protection

| Test Suite | Required | Current | Pass? |
|-----------|----------|---------|-------|
| Full test suite | 868+ passing | 866 passing, 2 expected failures | ❌ (need 868+ passing after IFC unblock) |
| Gold regression | ≥ 90% pass rate | 0% (not implemented) | ❌ |
| Format-specific tests | Per-format threshold | Varies | See format gates above |

---

## Scorecard Calculation

### Weighted Overall Score

| Category | Weight | Current | Min Required |
|----------|--------|---------|-------------|
| Format quality | 30% | 56% | 80% |
| Trust | 30% | 41% | 70% |
| AI quality | 20% | 71% | 85% |
| Test coverage | 10% | 99% | 99% |
| Release readiness | 10% | 78% | 90% |
| **TOTAL** | **100%** | **60.1%** | **82%** |

**Current overall score: 60%**  
**Minimum release threshold: 82%**

---

## How to Improve Scores

| To Increase Score By | Action | Effort |
|---------------------|--------|--------|
| +15% (formats) | Unblock IFC/MPP/XLS (install deps) | 1 day |
| +10% (trust) | Add dependency transparency UI | 1 day |
| +20% (trust) | Add evidence anchors (bbox + click-through) | 3 days |
| +15% (trust) | Add conflict detection | 3 days |
| +12% (AI) | Add refusal policy | 2 days |
| +10% (regression) | Create gold regression suite | 2 days |
| +5% (AI) | Improve answer grounding | 2 days |
| **+22% total** | **All P0 trust upgrades** | **~2 weeks** |

**After all P0 upgrades: Expected score ~82% — release ready.**
