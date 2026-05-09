from src.analysis_engine.adaptive_analysis import AdaptiveAnalysisEngine
from src.analysis_engine.health_tracker import HealthTracker, get_health_tracker
from src.analysis_engine.page_analysis import PageAnalyzer


class FakeLLMReturnsNoJson:
    def chat_json(self, **kwargs):
        return None


class FakeDB:
    def __init__(self):
        self.saved_pages = []

    def upsert_page(self, page_record):
        self.saved_pages.append(page_record)

    def get_document(self, doc_id):
        return {"project_id": "project-a"}

    def upsert_entity_node(self, *args, **kwargs):
        return "entity-1"

    def insert_entity_link(self, *args, **kwargs):
        return None


class FakeLLM:
    pass


class FakeAdaptiveFallbackEngine:
    def analyze_page(self, page):
        return {
            "summary": (
                "AI structured JSON analysis unavailable; deterministic extraction retained. "
                "Evidence preview: Pump schedule."
            ),
            "type": "spec",
            "entities": [],
            "relationships": [],
            "analyst_profile": "technical_spec",
            "status": "structured_json_failed",
            "error": "strict_json_parse_failed",
        }


def test_adaptive_analysis_returns_guarded_fallback_when_json_parse_fails():
    engine = AdaptiveAnalysisEngine(db=None, llm=FakeLLMReturnsNoJson())

    result = engine.analyze_page(
        {
            "doc_id": "doc-1",
            "page_index": 0,
            "py_text": "Technical specification for pump capacity, testing, and material requirements.",
        }
    )

    assert result["status"] == "structured_json_failed"
    assert result["error"] == "strict_json_parse_failed"
    assert result["evidence_basis"] == "deterministic_extraction"
    assert result["model_suitability"] == "not_approved_for_structured_analysis_until_benchmarked"
    assert "AI structured JSON analysis unavailable" in result["summary"]
    assert "pump capacity" in result["summary"].lower()
    assert result["type"] == "spec"


def test_health_tracker_partial_is_not_retry_candidate():
    tracker = HealthTracker()

    tracker.record_partial(
        "doc-1",
        0,
        "AI structured JSON analysis unavailable; deterministic extraction retained.",
        "strict_json_parse_failed",
        1.25,
    )

    stats = tracker.get_stats()

    assert stats["partial"] == 1
    assert stats["healthy"] == 0
    assert stats["unhealthy_parse"] == 0
    assert stats["unhealthy_llm"] == 0
    assert tracker.get_retry_candidates() == []


def test_page_analyzer_saves_structured_json_fallback_as_partial():
    tracker = get_health_tracker()
    tracker.pages.clear()
    tracker.metrics.clear()

    db = FakeDB()
    analyzer = PageAnalyzer(db, FakeLLM())
    analyzer.adaptive_engine = FakeAdaptiveFallbackEngine()

    analyzer._analyze_single_page(
        {
            "doc_id": "doc-1",
            "page_index": 0,
            "py_text": "Pump schedule with technical specification content, material requirements, testing notes, and equipment capacity data.",
        },
        [
            {
                "doc_id": "doc-1",
                "page_index": 0,
                "py_text": "Pump schedule with technical specification content, material requirements, testing notes, and equipment capacity data.",
            }
        ],
    )

    stats = tracker.get_stats()

    assert len(db.saved_pages) == 1
    assert stats["partial"] == 1
    assert stats["unhealthy_llm"] == 0
    assert stats["unhealthy_parse"] == 0
