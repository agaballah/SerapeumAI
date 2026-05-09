from types import MethodType

from src.application.orchestrators.agent_orchestrator import AgentOrchestrator


class FakeDB:
    def get_or_create_snapshot(self, project_id):
        return "snapshot-1"


class FakeCoverageGate:
    def check(self, **kwargs):
        return {
            "is_complete": False,
            "required_fact_types": ["document.scope_item"],
            "missing_fact_types": ["document.scope_item"],
            "job_plan": [{"action": "Certify extracted scope facts"}],
        }


class FakeFactAPI:
    def get_certified_facts(self, **kwargs):
        return {"facts": [], "conflicts": []}


def _make_orchestrator_with_extracted_support():
    orchestrator = object.__new__(AgentOrchestrator)
    orchestrator.db = FakeDB()
    orchestrator.coverage_gate = FakeCoverageGate()
    orchestrator.fact_api = FakeFactAPI()
    orchestrator.llm = None
    orchestrator.rag = None

    orchestrator._retrieve_extracted_evidence = MethodType(
        lambda self, query, project_id: [
            {
                "source_path": "C:/proj/Scope.pdf",
                "page_index": 4,
                "text": (
                    "The project scope includes generator room ventilation "
                    "and underground diesel fuel tank works."
                ),
                "provenance": "deterministic extraction",
            }
        ],
        orchestrator,
    )
    orchestrator._retrieve_linked_support = MethodType(
        lambda self, query, project_id: [],
        orchestrator,
    )
    orchestrator._build_ai_generated_lane = MethodType(
        lambda self, query, project_id, trusted_facts, extracted_evidence, linked_support: {
            "analysis_support": [],
            "synthesis": "",
        },
        orchestrator,
    )
    return orchestrator


def test_chat_answers_from_extracted_evidence_when_certified_facts_are_missing():
    orchestrator = _make_orchestrator_with_extracted_support()

    result = orchestrator.answer_question(
        "what is the project scope",
        project_id="project-a",
        snapshot_id="snapshot-1",
    )

    assert result["mode"] == "answered"
    assert result["supporting_only"] is True
    assert result["truth_authority"] == "PROJECT_GROUNDED_SUPPORT_ONLY"
    assert result["compliance_status"] == "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT"
    assert result["source_lanes"]["trusted_facts"] == 0
    assert result["source_lanes"]["extracted_evidence"] == 1
    assert result["answer"].startswith("Support-only answer")
    assert "not certified trusted facts" in result["answer"]
    assert "generator room ventilation" in result["answer"]
    assert result["answer_presentation"]["details_button_label"] == "Show Evidence"
    assert result["candidate_fact_suggestions"]
