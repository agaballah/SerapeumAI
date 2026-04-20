from __future__ import annotations

from typing import Dict


def compute_fact_visibility_metrics(total_facts: int, valid_facts: int, human_facts: int, candidate_facts: int) -> Dict[str, int]:
    valid_facts = max(int(valid_facts), 0)
    human_facts = max(int(human_facts), 0)
    candidate_facts = max(int(candidate_facts), 0)
    built_facts = max(int(total_facts), 0)
    qualified_facts = valid_facts + human_facts
    pending_qualification = max(built_facts - qualified_facts, 0)
    return {
        "valid_facts": valid_facts,
        "human_facts": human_facts,
        "qualified_facts": qualified_facts,
        "built_facts": built_facts,
        "candidate_facts": candidate_facts,
        "pending_qualification": pending_qualification,
    }


def fact_ratio_health(metrics: Dict[str, int]) -> str:
    total = int(metrics.get("built_facts", 0))
    qualified = int(metrics.get("qualified_facts", 0))
    human = int(metrics.get("human_facts", 0))
    if total <= 0:
        return "EMPTY"
    if qualified <= 0:
        return "UNQUALIFIED"
    if human > 0 and qualified >= total:
        return "HUMAN_REVIEWED"
    if qualified >= max(1, total // 2):
        return "PARTIAL"
    return "EARLY"


def governance_status_label(count: int, *, trusted_label: str) -> str:
    return trusted_label if int(count) > 0 else "NONE"


def backlog_label(candidate_count: int) -> str:
    return "ACTION_REQUIRED" if int(candidate_count) > 0 else "CLEAR"


def throughput_label(run_count: int) -> str:
    return "OBSERVED" if int(run_count) > 0 else "STALE"


def assess_p6_truth(total_activities: int, activities_with_float: int, critical_count: int) -> Dict[str, str]:
    total_activities = max(int(total_activities), 0)
    activities_with_float = max(int(activities_with_float), 0)
    critical_count = max(int(critical_count), 0)
    if total_activities <= 0:
        return {
            "metric": "No P6 activities detected",
            "status": "N/A",
        }
    if activities_with_float <= 0:
        return {
            "metric": f"Float available 0/{total_activities}; critical path unknown",
            "status": "LIMITED",
        }
    if activities_with_float < total_activities:
        return {
            "metric": f"Float available {activities_with_float}/{total_activities}; critical path partial ({critical_count})",
            "status": "PARTIAL",
        }
    return {
        "metric": f"Float available {activities_with_float}/{total_activities}; critical path activities {critical_count}",
        "status": "VERIFIED",
    }
