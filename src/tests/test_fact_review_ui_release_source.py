from pathlib import Path


def test_fact_table_keeps_core_review_actions_near_selected_fact_detail():
    source = Path("src/ui/widgets/fact_table.py").read_text(encoding="utf-8")
    assert "Engineer-readable fact" in source
    assert "Source / evidence" in source
    assert "Engineer decision" in source
    assert "What this fact says" in source
    assert "Evidence to check" in source
    assert "Before certifying" in source
    assert "Certify This Fact" in source
    assert "Reject This Fact" in source
    assert "btn_detail_approve" in source
    assert "btn_detail_reject" in source


def test_fact_review_presentation_exposes_engineer_review_fields():
    source = Path("src/application/services/fact_review_presentation.py").read_text(encoding="utf-8")
    assert "review_question" in source
    assert "evidence_excerpt" in source
    assert "source_warning" in source
    assert "certification_checklist" in source
    assert "do not certify unless lineage/evidence confirms the source" in source
