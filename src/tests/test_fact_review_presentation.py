from src.application.services.fact_review_presentation import (
    build_fact_review_view,
    build_filter_options,
    filter_fact_rows,
)


def sample_row(**overrides):
    base = {
        "fact_id": "fact-1",
        "fact_type": "schedule.critical_path",
        "subject_id": "ACT_1000_MAIN_WORKS",
        "value_text": None,
        "value_num": None,
        "value_json": '{"start": "2026-01-10", "finish": "2026-03-22"}',
        "unit": None,
        "status": "CANDIDATE",
        "method_id": "document_builder",
        "source_path": r"D:\Projects\Scope.pdf",
        "location_json": '{"page": 7}',
        "input_kind": "deterministic",
    }
    base.update(overrides)
    return base


def test_build_fact_review_view_creates_plain_language_review_fields():
    view = build_fact_review_view(sample_row())
    assert view["title"].startswith("Critical Path")
    assert "schedule fact records critical path" in view["meaning"].lower()
    assert view["status_label"] == "Candidate"
    assert "awaiting human review" in view["status_explanation"]
    assert view["source_label"] == "Scope.pdf p.7"
    assert view["origin_label"] == "Deterministic extraction"


def test_build_fact_review_view_handles_human_certified_and_numeric_value():
    view = build_fact_review_view(
        sample_row(
            fact_type="document.area_approx",
            subject_id="scope_overview",
            value_text=None,
            value_num=1250,
            unit="m2",
            value_json=None,
            status="HUMAN_CERTIFIED",
            input_kind="structured",
        )
    )
    assert view["family_label"] == "Document"
    assert view["status_label"] == "Human Certified"
    assert "strongest trusted fact state" in view["status_explanation"]
    assert "1250 m2" in view["value_summary"]


def test_filter_fact_rows_supports_family_state_and_source_filters():
    rows = [
        sample_row(fact_id="a", fact_type="document.requirement", source_path=r"D:\A\SpecA.pdf", status="VALIDATED"),
        sample_row(fact_id="b", fact_type="schedule.activity", source_path=r"D:\B\Plan.xer", status="CANDIDATE"),
    ]
    filtered = filter_fact_rows(rows, family_filter="Document", status_filter="VALIDATED", source_filter="SpecA.pdf")
    assert [row["fact_id"] for row in filtered] == ["a"]


def test_build_filter_options_exposes_reviewable_groups():
    options = build_filter_options(
        [
            sample_row(fact_type="document.requirement", source_path=r"D:\A\SpecA.pdf", status="VALIDATED"),
            sample_row(fact_type="schedule.activity", source_path=r"D:\B\Plan.xer", status="CANDIDATE"),
        ]
    )
    assert "Document" in options["families"]
    assert "schedule.activity" in options["types"]
    assert "VALIDATED" in options["states"]
    assert "SpecA.pdf" in options["sources"]
