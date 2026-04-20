from src.application.services.dashboard_honesty import assess_p6_truth, compute_fact_visibility_metrics, governance_status_label


def test_dashboard_governance_labels_require_real_trusted_counts():
    metrics = compute_fact_visibility_metrics(total_facts=10, valid_facts=0, human_facts=0, candidate_facts=10)
    assert governance_status_label(metrics["valid_facts"], trusted_label="TRUSTED") == "NONE"
    assert governance_status_label(metrics["human_facts"], trusted_label="GOLDEN") == "NONE"


def test_dashboard_p6_truth_marks_missing_float_as_limitation():
    view = assess_p6_truth(total_activities=12, activities_with_float=0, critical_count=0)
    assert view["status"] == "LIMITED"
    assert "critical path unknown" in view["metric"].lower()


def test_dashboard_p6_truth_marks_complete_float_coverage_as_verified():
    view = assess_p6_truth(total_activities=12, activities_with_float=12, critical_count=4)
    assert view["status"] == "VERIFIED"
    assert "critical path activities 4" in view["metric"].lower()
