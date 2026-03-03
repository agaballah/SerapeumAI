# Developer Quick Reference Card

**Last Updated:** 2025-01-27  
**Print This & Keep It Handy**

---

## Where to Start

| Task | Document | Time | Priority |
|------|----------|------|----------|
| Fix Phase 2.5 tests | [TASK_2.5_HANDOFF.md](TASK_2.5_HANDOFF.md) | 2-3h | 🔴 FIRST |
| Write Phase 2 docs | [TASK_2.7_AND_PHASE3_HANDOFF.md](TASK_2.7_AND_PHASE3_HANDOFF.md) § 2.7 | 2-3h | 🟡 SECOND |
| Build Phase 3 | [TASK_2.7_AND_PHASE3_HANDOFF.md](TASK_2.7_AND_PHASE3_HANDOFF.md) § 3 | 12-20h | 🟡 THIRD |

---

## Critical API Signatures (Verified)

### CorrectionRecord
```python
CorrectionRecord(
    page_id=1,
    field_name="panel_size",
    vlm_output="200A",              # ← NOT extracted_value
    engineer_correction="225A",     # ← NOT corrected_value
    feedback_type=FeedbackType.PARTIAL.value,  # ← Use .value
    confidence_impact=-0.15,
    timestamp=datetime.now(),
    document_id=1
)
```

### ConfidenceLearner.track_extraction()
```python
learner.track_extraction(
    field_name="wire_gauge",        # ← NOT field
    model_used="Mistral-7B",        # ← NOT model_name
    vlm_confidence=0.85,            # ← Float 0.0-1.0
    was_correct=True                # ← NOT correct
)
```

### PromptOptimizer.generate_stage1_prompt()
```python
prompt = optimizer.generate_stage1_prompt(
    unified_context="...",          # ← Required
    document_type="...",            # ← Required
    role="Technical Consultant"     # ← Required
    # ❌ NO discipline parameter
)
```

### PromptOptimizer.generate_stage2_prompt()
```python
prompt = optimizer.generate_stage2_prompt(
    unified_context="...",          # ← Required
    field_name="breaker_size",      # ← Required
    document_type="...",            # ← Required
    role="...",                     # ← Required
    model_name="Qwen2-VL-7B",       # ← Required
    add_examples=True               # ← Required
)
```

### ModelSelector.select_model_for_role_discipline()
```python
model_name, metadata = selector.select_model_for_role_discipline(
    role="Technical Consultant",
    discipline="Elec",
    available_vram_gb=8.0,
    field_name="breaker_size"  # ← Optional, for performance selection
)
```

---

## FeedbackType Enum (Complete List)

✅ **Use These:**
- `FeedbackType.TYPO` - Minor char/format issue
- `FeedbackType.PARTIAL` - Missing some info
- `FeedbackType.WRONG_CLASSIFICATION` - Wrong category
- `FeedbackType.MISSING_FIELD` - Should have extracted
- `FeedbackType.EXTRA_FIELD` - Shouldn't have extracted
- `FeedbackType.AMBIGUOUS` - Genuinely ambiguous

❌ **DON'T Use These (Don't Exist):**
- `EXTRACTION_ERROR` - ✗ Use WRONG_CLASSIFICATION
- `CONFIRMED` - ✗ Use TYPO (for no-change corrections)

---

## OptimizedPrompt Attributes

```python
# ✅ Correct Attributes:
prompt.full_prompt          # str
prompt.field_name           # str
prompt.model_name           # str
prompt.document_type        # str
prompt.role                 # str
prompt.includes_examples    # bool
prompt.dynamic_adjustments  # List[str]

# ❌ Wrong Attributes (Don't Use):
prompt.raw_prompt           # ← Use full_prompt
prompt.discipline           # ← Doesn't exist
```

---

## ConfidenceLearner Behavior

```python
learner = ConfidenceLearner()

# Get profile - returns None if not tracked yet!
profile = learner.get_field_confidence_profile("panel_size")
# profile is None until you call track_extraction() first

# Track some data
learner.track_extraction(..., field_name="panel_size", ...)

# Now it returns profile (or None if insufficient data)
profile = learner.get_field_confidence_profile("panel_size")

# ❌ DON'T assume profile exists
# ✅ DO check if None first
if profile is not None:
    # Use profile attributes
    pass
```

---

## Testing Quick Commands

```bash
# Test Phase 2.5 integration
pytest tests/integration/test_phase2_feedback_loop.py -v --tb=short

# Test all Phase 2 unit tests
pytest tests/unit/test_correction_collector.py \
        tests/unit/test_confidence_learner.py \
        tests/unit/test_prompt_optimizer.py \
        tests/unit/test_model_selector.py -v

# Test all
pytest tests/ -v

# Test with output
pytest tests/ -v -s

# Test specific test
pytest tests/integration/test_phase2_feedback_loop.py::TestCorrectionToLearning::test_something -v
```

---

## File Structure

```
src/core/
├── correction_collector.py   ✅ (20 tests)
├── confidence_learner.py     ✅ (21 tests)
├── prompt_optimizer.py       ✅ (24 tests)
├── model_selector.py         ✅ (84 tests)
└── safety/                   ⬜ TODO: Phase 3.1

src/telemetry/               ⬜ TODO: Phase 3.2

tests/unit/
├── test_correction_collector.py    ✅ (reference)
├── test_confidence_learner.py      ✅ (reference)
├── test_prompt_optimizer.py        ✅ (reference)
├── test_model_selector.py          ✅ (reference)
├── test_safety_validator.py        ⬜ TODO
└── test_telemetry.py               ⬜ TODO

tests/integration/
├── test_phase2_feedback_loop.py         🟡 (3/12 passing)
└── test_phase3_safety_and_observability.py  ⬜ TODO

docs/
├── PHASE1_ARCHITECTURE.md      ✅ (reference)
├── PHASE2_ARCHITECTURE.md      ⬜ TODO
└── INTEGRATION_GUIDE.md        ⬜ TODO
```

---

## Phase 2.5 Failing Tests (Quick Fix Guide)

| Test | Issue | Fix |
|------|-------|-----|
| test_correction_collector_outputs | Wrong CorrectionRecord params | Use page_id, vlm_output, engineer_correction, feedback_type.value |
| test_problem_areas_drive_model_selection | Passing dict instead of CorrectionRecord | Build proper CorrectionRecord objects |
| test_confidence_learner_data_informs | Assuming profile always exists | Don't assert on None profile |
| test_discipline_aware_prompts | Using .raw_prompt | Change to .full_prompt |
| test_single_document_feedback_cycle | Old CorrectionRecord format | Use correct field names |
| test_mixed_discipline_fields | Assuming profile not None | Check None first |
| test_repeated_corrections | Non-existent method call | Remove or mock the method |
| test_consistent_accuracy | Non-existent method call | Remove or mock the method |
| test_model_recommendation_changes | Non-existent .best_model | Just verify profile created |

**Solution:** See TASK_2.5_HANDOFF.md § Still Needs Fixing (detailed fixes provided)

---

## Working Reference Files

When stuck, copy patterns from:
- `tests/unit/test_correction_collector.py` - CorrectionRecord usage
- `tests/unit/test_confidence_learner.py` - track_extraction() usage
- `tests/unit/test_prompt_optimizer.py` - prompt generation
- `tests/unit/test_model_selector.py` - model selection

All 148 tests are PASSING - use as reference!

---

## Roles & Disciplines

**Roles:**
- Contractor
- Technical Consultant
- Owner
- Supervisor

**Disciplines:**
- Arch (Architecture)
- Elec (Electrical)
- Mech (Mechanical)
- Str (Structural)

**Role-Specific Thresholds:**
- Contractor: Lower (prefer speed)
- Technical Consultant: Higher (prefer accuracy)
- Owner: Medium
- Supervisor: Medium-High

---

## Common Mistakes to Avoid

```python
# ❌ WRONG
learner.track_extraction(
    field_name="panel_size",
    model_name="Mistral-7B",        # Should be model_used
    vlm_confidence=0.85,
    correct=True                    # Should be was_correct
)

# ✅ CORRECT
learner.track_extraction(
    field_name="panel_size",
    model_used="Mistral-7B",        # Correct param name
    vlm_confidence=0.85,
    was_correct=True                # Correct param name
)

# ❌ WRONG
prompt = optimizer.generate_stage1_prompt(
    unified_context="...",
    document_type="...",
    role="...",
    discipline="Elec"               # This parameter doesn't exist!
)

# ✅ CORRECT
prompt = optimizer.generate_stage1_prompt(
    unified_context="...",
    document_type="...",
    role="..."
    # No discipline parameter
)

# ❌ WRONG
correction = CorrectionRecord(
    field_name="panel_size",
    extracted_value="200A",         # Wrong field name
    corrected_value="225A",         # Wrong field name
    confidence=0.85                 # Wrong field name
)

# ✅ CORRECT
correction = CorrectionRecord(
    page_id=1,
    field_name="panel_size",
    vlm_output="200A",              # Correct field name
    engineer_correction="225A",     # Correct field name
    feedback_type=FeedbackType.PARTIAL.value,
    confidence_impact=-0.15,        # Correct field name
    timestamp=datetime.now(),
    document_id=1
)
```

---

## Debugging Tips

**If test fails:**
1. Read the error message carefully
2. Check if it's an API signature issue (check this card)
3. Look at working unit tests for reference
4. Check TASK_2.5_HANDOFF.md API Reference section
5. Ask in questions section of handoff doc

**If you're stuck:**
1. Check that you're using correct parameter names
2. Verify attribute names (e.g., .full_prompt not .raw_prompt)
3. Make sure you're using correct enum values with .value
4. Check if method/attribute actually exists
5. Run unit tests to verify fundamentals work

**Performance:**
- All tests should run in < 5 seconds
- If slower, you're doing something expensive
- Don't query databases in tests (use mocks)
- Don't process large files in tests

---

## Success Checklist (Phase 2.5)

- [ ] Read TASK_2.5_HANDOFF.md completely
- [ ] Reviewed API Reference section
- [ ] Looked at working unit tests
- [ ] Fixed CorrectionRecord params
- [ ] Fixed OptimizedPrompt attributes
- [ ] Fixed FeedbackType usage
- [ ] Removed non-existent method calls
- [ ] All 12 tests passing
- [ ] All tests < 1s each
- [ ] Created completion summary

---

## Quick Questions

**Q: Where's the best model recommendation logic?**  
A: ModelSelector._get_recommended_models_for_role_discipline()

**Q: How do I know which FeedbackType to use?**  
A: See FeedbackType Enum section above

**Q: Should I modify component files?**  
A: NO! Only fix tests in test_phase2_feedback_loop.py

**Q: What if a method doesn't exist?**  
A: Remove the test or simplify it. All methods documented in handoff.

**Q: How do I know if my API call is correct?**  
A: Check this quick reference card first, then TASK_2.5_HANDOFF.md API Reference

---

**Print & Bookmark This!**  
**Keep handy while developing**  
**Last Updated: 2025-01-27**
