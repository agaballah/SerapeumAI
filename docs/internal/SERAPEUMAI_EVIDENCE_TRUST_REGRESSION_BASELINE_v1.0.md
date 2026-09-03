# SerapeumAI Evidence Trust Regression Baseline v1.0

**Date:** 2026-09-02  
**Task:** TASK-014 — Evidence Trust Regression Baseline  
**Scope:** Read-only analysis of test coverage for the Evidence Authority Gate (TASK-013)  
**Status:** BASELINE — 761 tests passing, 0 failed  

---

## 1. Test Suite Summary

| Metric | Value |
|---|---|
| **Total tests** | 761 (744 existing + 17 new from TASK-013) |
| **Passed** | 761 |
| **Failed** | 0 |
| **Warnings** | 44 (all pre-existing DeprecationWarning) |
| **Schema migrations touched** | 0 |
| **New test files** | 2 |
| **Modified test files** | 1 |

### New Tests (TASK-013)

| File | Count | Focus |
|---|---|---|
| `test_fact_repository_governance.py` | 8 | Repository-level VALIDATED demotion gate |
| `test_placeholder_staging_isolation.py` | 6 | Extractor registry maturity isolation |
| `test_extractor_registry_reachability.py` (updated) | 5 (replaced 2) | Trust/staging split, maturity assertions |

---

## 2. Analysis: A — Placeholder Isolation

### 2.1 What Is Tested

| Test | Assertion | Coverage |
|---|---|---|
| `test_placeholder_extractor_not_in_trusted_registry` | `"field" not in EXTRACTORS` | ✅ Unit — registry membership |
| `test_placeholder_extractor_in_staging_registry` | `"field" in STAGING_EXTRACTORS` | ✅ Unit — staging placement |
| `test_placeholder_extractor_has_place_holder_maturity` | `FieldExtractor.maturity == "PLACEHOLDER"` | ✅ Unit — class attribute |
| `test_save_facts_demotes_system_completion_builder_validated_to_candidate` | `system_completion_builder_v1` VALIDATED → CANDIDATE | ✅ Integration — end-to-end gate |
| `test_save_facts_batch_mixed_statuses` (f1, f5) | Two system_completion facts demoted | ✅ Integration — batch path |

### 2.2 What Is NOT Tested

| Gap | Risk | Severity |
|---|---|---|
| **No test verifying `ExtractJob.run()` rejects `"field"` extractor** | If a job payload references `extractor_name="field"`, it would raise `ValueError("Unknown extractor")` — but this is implicit, not asserted | 🟡 Medium |
| **No end-to-end test: FieldExtractor.mock_data → DB → Chat answer** | The mock data path is blocked by TWO layers (registry + gate), but no single test proves both layers work together | 🟡 Medium |
| **No test asserting `builder_map` has no `"field"` entry** | The builder_map change is a string literal, not enforced by any assertion | 🟢 Low |

### 2.3 Proof Strength: **STRONG**

Two independent layers block PLACEHOLDER extractors:
1. **Registry layer:** `"field"` removed from `EXTRACTORS` — `ExtractJob.run()` raises `ValueError` if looked up
2. **Governance layer:** Even if a fact reaches `save_facts()` with `method_id="system_completion_builder_v1"`, the gate demotes it to `CANDIDATE`

The two-layer defense is tested independently but not as an integrated end-to-end flow.

---

## 3. Analysis: B — Experimental Isolation

### 3.1 What Is Tested

| Test | Assertion | Coverage |
|---|---|---|
| `test_extract_job_staging_registry_holds_experimental_and_placeholder` | `"excel_register"`, `"dgn"` in STAGING | ✅ Unit — registry placement |
| `test_staging_extractors_have_sub_verified_maturity` | All STAGING maturities in `{EXPERIMENTAL, PLACEHOLDER}` | ✅ Unit — maturity enforcement |
| `test_save_facts_demotes_unknown_builder_validated` | `unknown_future_builder_v1` VALIDATED → CANDIDATE | ✅ Future-proofing |
| `test_save_facts_batch_mixed_statuses` (f4) | `bim_builder_v1` VALIDATED → CANDIDATE | ✅ Proves non-allowlisted builders are blocked |

### 3.2 What Is NOT Tested

| Gap | Risk | Severity |
|---|---|---|
| **No test for ExcelRegisterExtractor behavior post-migration** | Moved from trusted to staging; no test confirms it no longer triggers `BuildFactsJob("register")` | 🟡 Medium |
| **No test for DGNExtractor behavior post-migration** | Moved from trusted to staging; no test confirms no builder trigger | 🟡 Medium |
| **No integration test: DGN/Excel extraction through ExtractJob.run()** | Verify that running `extractor_name="dgn"` or `"excel_register"` via ExtractJob now fails with `ValueError` | 🟡 Medium |
| **No test for `RegisterBuilder`** | `RegisterBuilder` exists, produces CANDIDATE facts, has zero dedicated tests | 🟢 Low |

### 3.3 Proof Strength: **MODERATE**

Experimental extractors are correctly placed in STAGING and their maturity is enforced. However, there is no active test that verifies the *consequence* of this placement — i.e., that the pipeline actually refuses to process them. The protection is structural (registry design) rather than behavioral (run-time assertion).

---

## 4. Analysis: C — Production Preservation

### 4.1 What Is Tested

| Test | Asserts | Coverage |
|---|---|---|
| `test_save_facts_preserves_document_builder_structural_validated` | `document_builder_v1` + VALIDATED → remains VALIDATED | ✅ Gate preserves allowed |
| `test_save_facts_preserves_document_builder_semantic_validated` | `document_builder.semantic_extract.v1` + VALIDATED → remains VALIDATED | ✅ Gate preserves allowed |
| `test_document_builder_builds_validated_facts_from_persisted_extraction_evidence` | DocumentBuilder emits VALIDATED for structural facts | ✅ Builder behavior intact |
| `test_build_facts_job_persists_document_facts_without_chat_or_runtime` | BuildFactsJob persists VALIDATED document facts | ✅ Full job path |
| `test_fact_query_api_can_retrieve_build_facts_output_as_trusted_context` | FactQueryAPI returns VALIDATED facts via `get_certified_facts()` | ✅ Query path intact |
| `test_document_builder_emits_semantic_document_facts` | Semantic facts (scope_item, area_approx, etc.) are VALIDATED | ✅ Builder detail |
| `test_pdf_routing_covers_empty_vector_scanned_and_combined_pages` | PDF routing unchanged | ✅ Upstream extraction |
| `test_pdf_metadata_completeness.py` (4 tests) | PDF metadata unchanged | ✅ Upstream extraction |

### 4.2 What Is NOT Tested

| Gap | Risk | Severity |
|---|---|---|
| **No test verifying `PPTXExtractor` preserves VERIFIED maturity** | VERIFIED → should stay in trusted registry | 🟢 Low |
| **No test verifying `WordExtractor` preserves VERIFIED maturity** | VERIFIED → should stay in trusted registry | 🟢 Low |
| **No full end-to-end: PDF extraction → DocumentBuilder → VALIDATED facts → Chat answer** | The `test_build_facts_evidence_closure.py` tests stop at FactQueryAPI; the chat synthesis path is tested separately but not as a single flow through the new gate | 🟡 Medium |
| **No test verifying `IFCExtractor` VERIFIED status is preserved** | IFC in trusted registry, but no maturity-specific assertion beyond set membership | 🟢 Low |

### 4.3 Proof Strength: **STRONG**

Production extractor paths (PDF → DocumentBuilder → VALIDATED facts) are well-tested through unit, integration, and query-layer tests. The governance gate explicitly preserves these paths with targeted tests.

---

## 5. Analysis: D — Human Certification Preservation

### 5.1 What Is Tested

| Test | Asserts | Coverage |
|---|---|---|
| `test_save_facts_preserves_human_certified_unchanged` | HUMAN_CERTIFIED facts pass through gate without modification | ✅ Gate non-interference |
| `test_authority_service_rejects_non_trusted_cert_type` | `authorize_certificate()` blocks non-TRUSTED cert types | ✅ AuthorityService guard |
| `test_coverage_gate_counts_human_certified_as_trusted` | HC facts satisfy CoverageGate | ✅ Gate consumption |
| `test_fact_api_returns_human_certified_document_fact` | HC facts returned by FactQueryAPI | ✅ API consumption |
| `test_certify_fact_promotes_candidate_to_human_certified` | Certify action works | ✅ Full lifecycle |
| `test_trusted_core_is_exactly_validated_and_human_certified` | `TRUSTED_FACT_STATUSES` constant is correct | ✅ Model integrity |

### 5.2 What Is NOT Tested

| Gap | Risk | Severity |
|---|---|---|
| **No test: human-certified fact survives `save_facts()` gate unchanged** | Already covered by `test_save_facts_preserves_human_certified_unchanged` — this IS tested | ✅ N/A |
| **No test: `AuthorityService.authorize_certificate()` bypasses `FactRepository.save_facts()`** | The AuthorityService uses `update_fact_status()` (a separate path), not `save_facts()` | ✅ Different code path, intentional |

### 5.3 Proof Strength: **STRONG**

Human certification flows through a completely separate code path (`update_fact_status()` / `authorize_certificate()`) that does not touch `save_facts()`. The gate is proven to not interfere with this path, and the authoritative tests in `test_truth_state_enforcement.py` and `test_fact_review_truth_state_closure.py` confirm the full HC lifecycle.

---

## 6. Analysis: E — Regression Safety

### 6.1 Existing Tests That Protect Against Rollback

| Test File | Tests | Protects Against |
|---|---|---|
| `test_truth_state_enforcement.py` | 9 | VALIDATED/HUMAN_CERTIFIED constants, CoverageGate trust filtering, AuthorityService rejection of invalid certs |
| `test_truth_spine_contract_guardrails.py` | 4 | TRUSTED_FACT_STATUSES definition, candidate non-governing semantics, answer path structure |
| `test_build_facts_evidence_closure.py` | 4 | DocumentBuilder VALIDATED output, BuildFactsJob persistence, FactQueryAPI retrieval, unknown builder rejection |
| `test_document_builder_semantic_facts.py` | 1 | Semantic fact emission from DocumentBuilder |
| `test_fact_review_truth_state_closure.py` | 6 | Certify/Reject actions, CoverageGate after certification, unknown status rejection |
| `test_verify_doc_facts.py` | 4 | Document intent inference, certified fact retrieval, orchestrator refusal behavior |
| `test_multi_lane_answer_path.py` | 2 | Multi-lane answer path with VALIDATED facts |
| `test_truth_path_inconsistency_closure.py` | 4 | Mounted Facts page truth consistency, chat refusal wording |
| `test_p6_truth.py` | 2 | P6 float normalization, ScheduleBuilder usage |
| `test_p6_relation_fidelity.py` | 2 | Parallel TASKPRED relation preservation |
| `test_p6_critical_path_unknown_honesty.py` | 6 | Critical path honesty with missing/malformed float |
| `test_pdf_routing.py` | 3 | PDF composition sniffing (vector/scanned) |
| `test_pdf_metadata_completeness.py` | 4 | PDF metadata extraction |
| `test_pdf_routing_fixture_pack.py` | 4 | Full PDF routing + OCR boundaries + VLM lock |
| `test_ifc_extractor_persistence_contract.py` | 2 | IFC record persistence to correct tables |
| `test_ifc_dependency_contract.py` | 4 | IFC honest failure, no regex fallback, source scan |
| `test_office_dgn_flattened_extraction_contract.py` | 6 | Office/DGN flattened output contract, no typed persistence claims |
| `test_excel_register_extractor_hygiene.py` | 1 | No absolute debug path write |
| `test_early_build_visibility.py` | 2 | Job queue priority, BuildFactsJob round-trip |

**Total regression-protecting tests: ~56 tests across 18 files**

### 6.2 Full Suite Status

```
761 passed, 0 failed, 44 warnings in 10.17s
```

All 744 original tests continue to pass. No regressions introduced.

---

## 7. Missing Scenarios

### 7.1 High-Priority Gaps

| # | Scenario | Why It Matters |
|---|---|---|
| 1 | **End-to-end: ExtractJob("field") → ValueError** | Proves the registry gate works at run time, not just at definition time |
| 2 | **End-to-end: ExtractJob("excel_register") → ValueError** | Same for EXPERIMENTAL extractor |
| 3 | **End-to-end: ExtractJob("dgn") → ValueError** | Same for EXPERIMENTAL extractor |
| 4 | **Full pipeline: PDF extraction → DocumentBuilder → VALIDATED facts → CoverageGate passes** | Proves the entire production path works through the gate |
| 5 | **Full pipeline: IFC extraction (with ifcopenshell) → BIMBuilder → CANDIDATE facts** | IFC is VERIFIED; BIMBuilder produces CANDIDATE; verify end-to-end still works |

### 7.2 Medium-Priority Gaps

| # | Scenario | Why It Matters |
|---|---|---|
| 6 | **RegisterBuilder behavior test** | Zero tests exist for RegisterBuilder despite being a real builder |
| 7 | **WordExtractor content extraction test** | Only contract test exists; no behavioral test for complex docs |
| 8 | **PPTXExtractor content extraction test** | Only contract test exists; no behavioral test |
| 9 | **DGNProcessor error handling test** | Integration tests exist but focus on availability, not error paths |
| 10 | **Gate warning log assertion** | The gate logs `logger.warning(...)` on demotion; no test asserts the log output |

### 7.3 Low-Priority Gaps

| # | Scenario | Why It Matters |
|---|---|---|
| 11 | **ExcelRegisterExtractor header detection test** | Header scoring heuristic has no behavioral tests |
| 12 | **CADProcessor entity listing test** | DXF processing via ezdxf has no tests |
| 13 | **ImageProcessor OCR test** | Image processing has zero tests |
| 14 | **DocumentClassifier stub verification** | Stub always returns "unknown" — should be documented or replaced |
| 15 | **Future builder allowlist expansion test** | If a new builder is added and incorrectly assigned VALIDATED, the gate catches it — but no test documents this policy |

---

## 8. Remaining Trust Risks

### 8.1 Known Acceptable Risks

| Risk | Status | Mitigation |
|---|---|---|
| **Semantic document facts are regex-based, not deterministic** | Accepted | DocumentBuilder method_id is in the allowlist; quality is a separate concern from authority |
| **No maturity check at ExtractJob.run() level** | Addressed | `ValueError` on unknown extractor name prevents PLACEHOLDER/EXPERIMENTAL from reaching the pipeline |
| **Gate only checks method_id prefix, not provenance depth** | Acceptable | method_id is set by builders; each builder maps to one extractor source. Indirect paths (e.g., query_derivation) produce CANDIDATE only |
| **STAGING_EXTRACTORS dict is untyped** | Acceptable | Structure is simple; maturity assertions on class attributes provide the invariant |

### 8.2 Residual Risks

| Risk | Severity | Description |
|---|---|---|
| **Method ID typo could bypass gate** | 🟡 Medium | A builder using a misspelled method_id (e.g., `"system_complation_builder_v1"` instead of `"system_completion_builder_v1"`) would NOT match the demotion prefix — but since the gate now uses an allowlist (not a denylist), this is actually safe: unknown method_ids get demoted |
| **Direct DB insert bypasses gate** | 🟡 Medium | Any code that inserts directly into the `facts` table (e.g., via raw SQL) bypasses `save_facts()`. Currently only tests do this; production code goes through builders |
| **Backfill of old VALIDATED facts** | 🟢 Low | Facts already persisted as VALIDATED before this gate was deployed will remain VALIDATED. This is intentional — the gate is forward-looking only |

---

## 9. Recommended Future Test Additions

### 9.1 Priority Order

1. **`test_extract_job_refuses_staging_extractors`** — Assert that `ExtractJob` with `extractor_name="field"`, `"excel_register"`, or `"dgn"` raises `ValueError`. This closes the highest-priority gap (#1-3).

2. **`test_full_pdf_to_trusted_fact_pipeline`** — End-to-end: PDF file → ExtractJob → DocumentBuilder → FactQueryAPI returns VALIDATED facts. Proves the complete production path through the gate.

3. **`test_full_ifc_to_candidate_fact_pipeline`** — End-to-end: IFC file → ExtractJob → BIMBuilder → facts are CANDIDATE. Proves VERIFIED extractors work through the full pipeline.

4. **`test_gate_warning_log_on_demotion`** — Assert that `logger.warning` is called when a fact is demoted. Uses `caplog` fixture.

5. **`test_register_builder_emits_candidate_facts`** — First behavioral test for RegisterBuilder.

### 9.2 Long-Term Test Health

| Area | Current Coverage | Target |
|---|---|---|
| **Extractor-level tests** | 36 tests | ≥50 (add image, DXF, register behavior) |
| **Builder-level tests** | 7 tests | ≥15 (add register, BIM integration) |
| **Pipeline integration tests** | 4 tests | ≥8 (full extract→build→query for each domain) |
| **Governance gate tests** | 14 tests | ≥20 (add log assertions, boundary conditions) |
| **Trust path tests** | 25 tests | ≥30 (add cross-domain consistency) |

---

## 10. Conclusion

The Evidence Authority Gate (TASK-013) is protected by **761 passing tests** with **zero regressions**. The gate correctly:

- **Blocks PLACEHOLDER extractors** from the trusted pipeline (two-layer defense)
- **Demotes unverified VALIDATED facts** at the single write path (`FactRepository.save_facts`)
- **Preserves PRODUCTION/VERIFIED paths** (PDF → DocumentBuilder → VALIDATED)
- **Does not interfere** with HUMAN_CERTIFIED certification workflows
- **Is future-proof** against unknown/new builders producing unauthorized VALIDATED facts

**Three high-priority gaps remain** — all related to end-to-end integration testing of the registry gate at runtime. These should be addressed in TASK-015.

---

*This report is read-only analysis. No code was modified.*
