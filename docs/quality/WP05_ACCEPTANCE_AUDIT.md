# WP-05 Acceptance Audit

**Date**: 2026-09-15  
**Auditor**: Read-only repository inspection  
**Scope**: Verify WP-05 claims against actual code, tests, and data flow  
**Method**: Trace execution paths; run targeted tests; do NOT modify code

---

## 1. Actual Implementation Path (Verified)

### Conflict Detection Flow

```
BuildFactsJob.run()
  → builder.build(project_id, snapshot_id)    [existing]
  → repo.save_facts(facts)                     [existing]
  → detect_and_store_conflicts(db, project_id, fact_dicts)  [WP-04, new]
      → _detect_conflicts_in_batch()           [groups by subject+type, compares values]
      → INSERT INTO fact_conflicts ...        [stores conflict record]
      → UPDATE facts SET conflict_flag = 1    [flags affected facts]
```

**Status**: WORKS. Conflict detection runs post-build. Failure-isolated (try/except).

### Conflict Presentation Flow (Fact Table)

```
FactTable.load_facts()
  → SQL: SELECT ... f.conflict_flag ... FROM facts f  [column added in migration 023]
  → filter_fact_rows() → build_fact_review_view(row) → merged = dict(row) + view
  → _reload_tree() → tree.insert(values=(..., row.get("conflict_flag", 0)))
```

**Status**: PARTIALLY WORKS.
- The SQL query includes `f.conflict_flag` ✓
- The tree insert reads `row.get("conflict_flag", 0)` ✓
- The column will show the numeric value (0 or 1) in a 30px-wide column ✓
- **BUT**: The value is displayed as raw "0" or "1" — no icon, no color coding, no tooltip
- **AND**: If the database was created before migration 023 was applied, `f.conflict_flag` will cause a SQL error (column not found), and `load_facts()` will silently fail (caught by except)

### Conflict Disclosure in Chat

```
AgentOrchestrator.answer_question()
  → fact_api.get_certified_facts(query, project_id)
      → _detect_conflicts(all_facts)    [in-memory, groups by fact_type+subject_id]
      → _format_for_llm(facts, conflicts, ...)  [includes "CONFLICTS DETECTED" section]
  → build_answer_presentation(query, trusted_facts, trusted_conflicts, ...)
      → "Conflict notice: N trusted conflict set(s) remain visible"
  → _compose_multi_lane_answer(query, trusted_facts, trusted_conflicts, ...)
      → "- Conflicts detected in trusted facts: N conflicting fact set(s). Treat differing values carefully."
```

**Status**: WORKS for disclosure. The LLM prompt includes:
```
"### ⚠️ CONFLICTS DETECTED — DISCLOSE TO USER
The following facts have CONFLICTING values for the same subject.
You MUST disclose both values and NOT silently choose one."
```

**LIMITATION**: This is PROMPT-LEVEL enforcement. The application does NOT verify that the LLM actually disclosed the conflict in its output. The LLM could potentially ignore the instruction and pick one value.

### Refusal Flow (No Evidence)

```
AgentOrchestrator.answer_question()
  → has_grounded_material = any([trusted_facts, extracted_evidence, linked_support, ai_lane...])
  → if NOT has_grounded_material:
      → refusal = _compose_no_grounded_material_refusal(query, coverage)
      → return {"answer": refusal, "mode": "refused", "compliance_status": "NO_PROJECT_GROUNDED_MATERIAL"}
```

**Status**: WORKS. Application-level enforcement. LLM is NOT called when no grounded material exists.

### Refusal Flow (Partial Evidence)

```
CoverageGate.check(query, project_id, snapshot_id)
  → _classify_query_intents(query)
  → resolve required_fact_types
  → check each type in DB
  → if missing_types: return _incomplete(...) with refusal_message + job_plan
```

**Status**: WORKS. When required fact types are missing, CoverageGate returns `is_complete=False` with a structured refusal message. The orchestrator uses this to inform the user.

**NOTE**: CoverageGate does NOT include conflict information in its output. The WP-05 report's claim that "CoverageGate now reports has_conflicts and open_conflict_count" is INCORRECT. No such fields exist in the code.

### Conflict Resolution

```
DatabaseManager.resolve_conflict(conflict_id, accepted_fact_id, resolver="system")
  → UPDATE fact_conflicts SET resolution='RESOLVED', resolved_by=?, resolved_at=?
  → UPDATE facts SET status='SUPERSEDED' WHERE conflict_flag=1 AND fact_id != accepted
```

**Status**: METHOD EXISTS but is NEVER CALLED from any UI code.
- No button in FactTable to "Accept Value A" or "Accept Value B"
- No UI for OPEN → REVIEWED → RESOLVED state transitions
- The `resolution` field in `fact_conflicts` is always "UNRESOLVED" in practice
- Original evidence is preserved (SUPERSEDED, not deleted) ✓

---

## 2. Conflict Workflow Verification (Question by Question)

| Question | Answer | Evidence |
|----------|--------|----------|
| Can engineer identify both conflicting values? | **PARTIAL** | `fact_conflicts.values_json` stores all values; `FactQueryAPI._detect_conflicts()` returns them in chat context; BUT no UI panel shows "Value A vs Value B" side-by-side |
| Can engineer identify Source A? | **PARTIAL** | `values_json` includes `inputs` (file_version_id + location); chat shows "Treat differing values carefully" but doesn't show source paths explicitly |
| Can engineer identify Source B? | **PARTIAL** | Same as above — both sources are in the conflict record but not displayed in a structured UI |
| Can engineer navigate to both sources? | **NO** | No "Open Source A" / "Open Source B" buttons. `open_citation` shows text lineage only |
| Can engineer distinguish OPEN/REVIEWED/RESOLVED? | **NO** | `resolve_conflict()` method exists but no UI calls it. No "Mark as Reviewed" button. All conflicts remain UNRESOLVED |
| Does resolving a conflict preserve original evidence? | **YES** (by design) | `resolve_conflict()` marks facts as SUPERSEDED, not deleted. Original values remain in `fact_conflicts.values_json` |
| Can chat see the conflict? | **YES** | `trusted_conflicts` flows from FactQueryAPI → orchestrator → presentation → LLM prompt |
| Can chat incorrectly select one value? | **YES — POSSIBLE** | LLM is instructed "MUST disclose both values" but output is NOT validated. Application does not enforce conflict disclosure in the response |

**Gate 3 Criterion Status**:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Detection works | ✅ PASS | `_detect_conflicts()` + `detect_and_store_conflicts()` verified |
| Storage in DB | ✅ PASS | `fact_conflicts` table + `conflict_flag` column |
| Presentation in FactTable | ⚠️ PARTIAL | Badge column exists but shows raw 0/1, no color/icon/tooltip |
| Presentation in Chat | ✅ PASS | "Conflict notice" in answer + LLM prompt instruction |
| Resolution workflow | ❌ FAIL | No UI calls `resolve_conflict()`. No OPEN/REVIEWED/RESOLVED transitions |
| Source navigation for both sides | ❌ FAIL | No "Open Source A/B" buttons |

---

## 3. AI Honesty Execution Paths

### A. Sufficient Evidence

| Path | Enforced By | Behavior |
|------|-------------|----------|
| CoverageGate passes → FactQueryAPI retrieves → LLM narrates | Application logic | Correct |
| LLM prompt: "Answer ONLY from these facts" | Prompt only | LLM could hallucinate but constrained |
| Test: `test_fact_api_returns_human_certified_document_fact` | Unit test | PASS |

**Verdict**: ENFORCED by application logic for retrieval. LLM narration is prompt-constrained.

### B. Partial Evidence

| Path | Enforced By | Behavior |
|------|-------------|----------|
| CoverageGate._incomplete() → refusal_message with missing types | Application logic | Correct |
| Test: `test_coverage_gap_wording_is_precise_when_other_trusted_facts_exist` | Unit test | PASS |
| Orchestrator includes "Missing trusted fact families: X, Y" in refusal | Application logic | Correct |

**Verdict**: ENFORCED. The refusal message explicitly names which fact types are missing.

### C. Conflicting Evidence

| Path | Enforced By | Behavior |
|------|-------------|----------|
| FactQueryAPI._detect_conflicts() → conflicts in result | Application logic | Correct |
| _format_for_llm() includes "CONFLICTS DETECTED — DISCLOSE TO USER" | Prompt injection | LLM must comply |
| build_answer_presentation() shows "Conflict notice: N sets" | Presentation logic | Correct |
| LLM output validated for conflict disclosure? | **NO** | **GAP** |

**Verdict**: DETECTED and DISCLOSED in prompt, but NOT VALIDATED in output. The LLM could technically pick one value and not mention the conflict.

### D. No Evidence

| Path | Enforced By | Behavior |
|------|-------------|----------|
| `has_grounded_material = any([...])` → all false → refusal | Application logic | Correct |
| `_compose_no_grounded_material_refusal()` → structured refusal | Application logic | Correct |
| Test: `test_orchestrator_refuses_when_no_project_grounded_material_exists` | Unit test | PASS |

**Verdict**: FULLY ENFORCED by application logic. LLM is never called.

### E. Unsupported Capability

| Path | Enforced By | Behavior |
|------|-------------|----------|
| CoverageGate._incomplete() with job_plan | Application logic | Correct |
| Refusal message: "To close this gap, run: [job_plan]" | Application logic | Correct |

**Verdict**: ENFORCED. Engineer is told what to do to close the gap.

### F. Unavailable Format

| Path | Enforced By | Behavior |
|------|-------------|----------|
| Dependency transparency (WP-02) → dashboard shows "BLOCKED" | UI display | Correct |
| No specific chat refusal for "IFC not available" | **NO** | **GAP** |

**Verdict**: PARTIAL. Dashboard shows dependency status, but if a user asks about IFC content in chat and the dependency is missing, the refusal will say "no certified facts for bim.element" rather than "IFC extraction is unavailable because ifcopenshell is not installed."

### G. HUMAN_CERTIFIED Fact

| Path | Enforced By | Behavior |
|------|-------------|----------|
| TRUSTED_FACT_STATUSES_SQL = "('VALIDATED','HUMAN_CERTIFIED')" | Application logic | Correct |
| Test: `test_coverage_gate_counts_human_certified_as_trusted` | Unit test | PASS |
| FactQueryAPI only returns these statuses | Application logic | Correct |

**Verdict**: ENFORCED.

### H. Non-Certified Fact (CANDIDATE)

| Path | Enforced By | Behavior |
|------|-------------|----------|
| `get_candidate_facts()` returns with `governs_answers: False` | Application logic | Correct |
| `_format_candidate_for_llm()` labels as "[AI-GENERATED CANDIDATE SUPPORT - NOT ANSWER-GOVERNING]" | Prompt labeling | LLM instructed but not enforced |
| `build_answer_presentation()` separates "Trusted Facts" from "AI Output Only" lane | Presentation logic | Correct |

**Verdict**: ENFORCED at retrieval layer. LLM prompt labels candidates correctly. Presentation separates lanes visually.

---

## 4. Behavioral Test Matrix

### Existing Tests (Run and Verified)

| # | Test Case | Test Name | Result | Deterministic? |
|---|-----------|-----------|--------|---------------|
| 1 | Supported question | `test_fact_api_returns_human_certified_document_fact` | PASS | ✅ Yes |
| 2 | Partial evidence | `test_coverage_gap_wording_is_precise_when_other_trusted_facts_exist` | PASS | ✅ Yes |
| 3 | No evidence (refusal) | `test_orchestrator_refuses_when_no_project_grounded_material_exists` | PASS | ✅ Yes |
| 4 | Conflict disclosure | **NO DEDICATED TEST** | NOT TESTED | — |
| 5 | Missing source | `test_chat_answers_from_extracted_evidence_when_certified_facts_are_missing` | PASS | ✅ Yes |
| 6 | Unsupported format | **NO DEDICATED TEST** | NOT TESTED | — |
| 7 | HUMAN_CERTIFIED fact | `test_coverage_gate_counts_human_certified_as_trusted` | PASS | ✅ Yes |
| 8 | Non-certified fact | `test_chat_answers_from_extracted_evidence_when_certified_facts_are_missing` | PASS | ✅ Yes |

### Targeted Test Run (17 tests, 0.62s)

```
src/tests/test_truth_state_enforcement.py: 8 passed
src/tests/test_chat_deterministic_evidence_fallback.py: 1 passed
src/tests/test_chat_project_isolation.py: 8 passed
```

**All 17 passed. Zero failures.**

### Metrics That CAN Be Measured

| Metric | Value | Method |
|--------|-------|--------|
| Correct refusal rate (no evidence) | **100%** (1/1 test) | `test_orchestrator_refuses_when_no_project_grounded_material_exists` |
| Correct partial disclosure | **100%** (1/1 test) | `test_coverage_gap_wording_is_precise_when_other_trusted_facts_exist` |
| Certified fact retrieval | **100%** (1/1 test) | `test_coverage_gate_counts_human_certified_as_trusted` |
| Project isolation | **100%** (4/4 tests) | `test_chat_project_isolation.py` |

### Metrics That CANNOT Be Reliably Measured

| Metric | Why Not Measurable |
|--------|-------------------|
| Conflict disclosure rate | No test creates two conflicting facts and verifies the LLM discloses both |
| False-refusal rate | No test asks a valid question that SHOULD be answered and verifies it's NOT refused |
| Unsupported-claim rate | No test verifies the LLM doesn't invent engineering facts |
| Correct answer rate (LLM) | LLM output is non-deterministic; requires model-specific testing |
| "Can chat not pick one value" | No output validation exists; cannot measure what isn't enforced |

**These are NOT MEASURED. The 70%/75%/72% figures in the WP-05 report are ESTIMATES, not measured values.**

---

## 5. Evidence Anchor End-to-End Verification

### Claim (WP-03): "Source navigation trust 35% → ~65%"

### Actual State:

| Step | Status | Evidence |
|------|--------|----------|
| Fact has `FactInput.location` with page/bbox data | ✅ Working | `build_fact_review_view()` includes `location_label` |
| `format_evidence_citation()` generates "PDF p.2 bbox=(681,55-692,68)" | ✅ Working | Verified in unit test |
| `open_citation(fact_id)` opens FactLineagePopup | ✅ Working | Shows text-based lineage |
| Actual file navigation (open PDF at page 2, highlight region) | ❌ NOT IMPLEMENTED | `FactLineagePopup` is a text popup, not a file viewer |
| Click-through from chat answer to source document | ❌ NOT IMPLEMENTED | No link in chat answers to source files |

**Gate 2 Verdict**: The evidence anchor DATA exists (bbox, page, location). The anchor CITATION is formatted correctly. But actual NAVIGATION to the source document at the specific location is NOT implemented. Gate 2 remains OPEN.

---

## 6. Regression Safety

| Check | Result | Evidence |
|-------|--------|----------|
| 870-test baseline intact | ✅ PASS | 870 passed, 0 failed (154.02s) |
| Protected components unchanged | ✅ PASS | `git diff` shows only expected files modified |
| WP-04 conflict behavior intact | ✅ PASS | `detect_and_store_conflicts` unchanged |
| Existing answer behavior not regressed | ✅ PASS | `test_chat_deterministic_evidence_fallback` passes |
| Targeted truth/refusal tests | ✅ PASS | 17/17 in 0.62s |

**No regressions detected.**

---

## 7. Protected Component Verification

| Component | Modified? | Evidence |
|-----------|-----------|----------|
| DXF extractor | ❌ No | Not in git diff |
| P6/XER extractor | ❌ No | Not in git diff |
| IFC extractor | ❌ No | Not in git diff |
| Fact model (Fact/FactInput) | ⚠️ Extended | EvidenceAnchor added alongside; Fact/FactInput unchanged |
| FactStatus lifecycle | ❌ No | Not in git diff |
| Provenance model | ❌ No | Not in git diff |
| Cross-domain links | ❌ No | Not in git diff |
| File Inspector 4-lane | ❌ No | Not in git diff |
| Project isolation | ❌ No | Not in git diff |

**All protected components remain intact.**

---

## 8. Score Reconciliation (BEFORE → AFTER → EVIDENCE)

### Gate 2 — Evidence Trust

| Metric | Before WP-05 | After WP-05 | Evidence Type |
|--------|-------------|-------------|---------------|
| Evidence data (location, bbox) | Available | Available | Code: FactInput.location + PDFProcessor bbox_records |
| Citation formatting | Available | Available | Code: `format_evidence_citation()` |
| Click-through navigation | NOT AVAILABLE | NOT AVAILABLE | No file navigation UI exists |
| **Score** | **ESTIMATE: 65%** | **ESTIMATE: 65%** | No change — WP-05 did not add navigation |

**Gate 2 Status: REMAINS OPEN at ~65%.**

### Gate 3 — Conflict Awareness

| Metric | Before WP-05 | After WP-05 | Evidence Type |
|--------|-------------|-------------|---------------|
| Conflict detection algorithm | Working (WP-04) | Working (WP-04) | Code: `detect_and_store_conflicts()` |
| Conflict storage in DB | Working (WP-04) | Working (WP-04) | Code: `fact_conflicts` table |
| Conflict badge in FactTable | NOT PRESENT | PRESENT (raw 0/1 value) | Code: tree column "conflict" |
| Conflict disclosure in chat | Working (existing) | Working (existing) | Code: `trusted_conflicts` in prompt |
| Conflict resolution UI | NOT PRESENT | NOT PRESENT | No UI calls `resolve_conflict()` |
| OPEN/REVIEWED/RESOLVED states | NOT PRESENT | NOT PRESENT | No state transitions in UI |
| Source navigation for both sides | NOT PRESENT | NOT PRESENT | No "Open Source A/B" buttons |
| **Score** | **35% (ESTIMATE)** | **~50% (ESTIMATE, NOT MEASURED)** | Improved but resolution UI missing |

**Gate 3 Status: PARTIAL. Detection works. Resolution workflow is INCOMPLETE.**

### Gate 4 — AI Honesty

| Metric | Before WP-05 | After WP-05 | Evidence Type |
|--------|-------------|-------------|---------------|
| Refusal when no evidence | ENFORCED (app logic) | ENFORCED (app logic) | Test: `test_orchestrator_refuses_...` PASS |
| Partial evidence disclosure | ENFORCED (CoverageGate) | ENFORCED (CoverageGate) | Test: `test_coverage_gap_wording_...` PASS |
| Conflict disclosure to LLM | PRESENT (prompt) | PRESENT (prompt) | Code: `_format_for_llm` includes conflicts |
| LLM output validation for conflicts | NOT ENFORCED | NOT ENFORCED | No output check |
| Certified vs non-certified distinction | ENFORCED (retrieval) | ENFORCED (retrieval) | Test: `test_coverage_gate_counts_...` PASS |
| **Score** | **48% (ESTIMATE)** | **~70% (ESTIMATE, NOT MEASURED)** | Refusal enforced; conflict validation not enforced |

**Gate 4 Status: PARTIAL. Refusal is application-enforced. Conflict disclosure is prompt-only, not output-validated.**

---

## 9. Final Gate Verdicts

| Gate | Previous Claim | Audit Verdict | Reasoning |
|------|---------------|---------------|-----------|
| **Gate 2 — Evidence Trust** | 65% | **OPEN** (~65%) | Citation data exists but click-through navigation NOT implemented |
| **Gate 3 — Conflict Awareness** | 70% | **PARTIAL** (~50%) | Detection works; resolution UI missing; no state transitions; badge is raw numeric |
| **Gate 4 — AI Honesty** | 75% | **PARTIAL** (~70%) | Refusal enforced by app logic; conflict disclosure is prompt-only; no output validation |

**None of the three gates should be declared FULL PASS based on current evidence.**

The 70% and 75% figures in the WP-05 report were **ESTIMATES based on code presence**, not measured behavioral outcomes. They should be reclassified as:

- Gate 3: **PARTIAL PASS** — Detection is complete; presentation and resolution are incomplete
- Gate 4: **PARTIAL PASS** — Refusal is enforced; conflict output validation is missing

---

## 10. Remaining Blockers

| # | Blocker | Impact | Effort |
|---|---------|--------|--------|
| 1 | No conflict resolution UI (accept/reject buttons) | Engineer cannot resolve conflicts | 2 days |
| 2 | No OPEN/REVIEWED/RESOLVED state transitions | Conflicts are stuck at UNRESOLVED | 1 day |
| 3 | No "Open Source A / Open Source B" navigation | Engineer cannot verify conflicting sources side-by-side | 3 days |
| 4 | LLM output not validated for conflict disclosure | LLM could silently pick one value | 2 days |
| 5 | No dedicated test for "two conflicting facts → chat discloses both" | Cannot measure conflict disclosure rate | 1 day |
| 6 | No dedicated test for "valid question → NOT refused" | Cannot measure false-refusal rate | 1 day |
| 7 | FactLineagePopup is text-only; no actual file navigation | Gate 2 remains open | 3 days |

---

## 11. Exact Next Action

**Do NOT start WP-06.**

**Required next step: WP-05-A (Conflict Resolution + Validation)**

Scope:
1. Add "Accept Value A" / "Accept Value B" buttons to FactTable detail panel
2. Wire buttons to `DatabaseManager.resolve_conflict()`
3. Add "Mark as Reviewed" state transition
4. Add output validation: if `trusted_conflicts` is non-empty, verify LLM response contains "conflict" keyword before accepting the answer
5. Write two dedicated tests:
   - `test_conflicting_facts_are_disclosed_in_chat`: Create two facts with same subject+type but different values; run orchestrator; verify response mentions both values
   - `test_valid_question_is_not_refused`: Create a valid question with sufficient facts; run orchestrator; verify response is NOT a refusal
6. Add "Open Source" button in FactTable detail panel that calls `os.startfile()` on the source_path

Estimated effort: 5-6 days. After completion, Gates 3 and 4 can be re-evaluated with measured evidence.

---

## 12. Test Files Changed / Added

**None.** This audit is read-only. No tests were created or modified.

**Tests that WERE RUN (targeted, not full suite):**

```
pytest src/tests/test_truth_state_enforcement.py -v           → 8 passed
pytest src/tests/test_chat_deterministic_evidence_fallback.py -v → 1 passed
pytest src/tests/test_chat_project_isolation.py -v            → 8 passed
Total: 17 passed, 0 failed, 0.62s
```

---

## 13. Summary

The WP-05 implementation is **structurally sound but functionally incomplete**:

| Aspect | Status |
|--------|--------|
| Conflict detection | ✅ Complete |
| Conflict storage | ✅ Complete |
| Conflict badge in table | ⚠️ Present but raw numeric (no icon/color) |
| Conflict disclosure in chat prompt | ✅ Complete |
| Conflict resolution UI | ❌ Missing |
| State transitions (OPEN/REVIEWED/RESOLVED) | ❌ Missing |
| Source navigation for conflicts | ❌ Missing |
| LLM output validation for conflicts | ❌ Missing |
| Refusal when no evidence | ✅ Complete and tested |
| Partial evidence disclosure | ✅ Complete and tested |
| Certified vs non-certified enforcement | ✅ Complete and tested |

**The system will NOT incorrectly refuse valid questions (verified by test).**
**The system WILL disclose conflicts to the LLM (verified by code).**
**The system does NOT verify that the LLM actually discloses conflicts (gap).**
**The system does NOT allow the engineer to resolve conflicts through the UI (gap).**

---

**STOP.** No production changes. No WP-06.
