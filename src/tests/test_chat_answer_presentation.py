from src.application.services.chat_answer_presentation import build_answer_presentation
def test_presentation_starts_with_direct_answer_and_readable_sections():
    presentation = build_answer_presentation(
        query="provide project scope summary",
        trusted_facts=[
            {
                "fact_id": "f1",
                "fact_type": "document.requirement",
                "value": {"statement": "Provide generator room ventilation."},
                "status": "VALIDATED",
                "lineage": [{"source_path": "C:/proj/Scope.pdf", "location": {"page_index": 10}}],
            },
            {
                "fact_id": "f2",
                "fact_type": "document.scope_item",
                "value": {"statement": "Install an underground diesel fuel tank for standby generation."},
                "status": "VALIDATED",
                "lineage": [{"source_path": "C:/proj/Scope.pdf", "location": {"page_index": 11}}],
            },
        ],
        trusted_conflicts=[],
        extracted_evidence=[
            {
                "source_path": "C:/proj/Scope.pdf",
                "page_index": 11,
                "text": "The project scope includes an underground diesel tank and generator room.",
                "provenance": "deterministic extraction",
            }
        ],
        linked_support=[
            {
                "entity_type": "requirement",
                "entity_value": "Generator room ventilation",
                "relation": "linked_to",
                "neighbor_type": "component",
                "neighbor_value": "Generator room",
                "confidence_tier": "CANDIDATE",
            }
        ],
        ai_lane={
            "analysis_support": [
                {
                    "source_path": "C:/proj/Scope.pdf",
                    "page_index": 0,
                    "text": "AI analysis notes a generator room with dedicated ventilation.",
                }
            ],
            "synthesis": "AI synthesis says the scope appears to include generator room ventilation and fuel storage.",
        },
        coverage={"is_complete": False, "missing_fact_types": ["document.vendor_basis"]},
    )
    assert presentation["summary_block"]["title"] == "Direct Answer"
    assert presentation["summary_block"]["source_label"] == "Trusted Facts"
    summary_lines = presentation["summary_block"]["text"].splitlines()
    assert 1 <= len(summary_lines) <= 5
    assert "trusted facts" not in presentation["summary_block"]["text"].lower()
    assert "Strongest grounded answer" not in presentation["summary_block"]["text"]
    assert presentation["main_answer_text"] == presentation["copy_text"]
    assert presentation["details_button_label"] == "Show Evidence"
    assert presentation["source_basis_banner"] == "Based on trusted facts, extracted evidence, linked support + AI synthesis."
    assert "## Direct Answer" in presentation["details_copy_text"]
    assert "## Trusted Facts" in presentation["details_copy_text"]
    assert "## Extracted Evidence" in presentation["details_copy_text"]
    assert "## Linked Support" in presentation["details_copy_text"]
    assert "## AI-Generated Synthesis" in presentation["details_copy_text"]
    trusted = next(section for section in presentation["sections"] if section["title"] == "Trusted Facts")
    assert trusted["items"][0]["is_group_heading"] is True
    assert trusted["items"][0]["text"] in {
        "Project scope",
        "Systems / works included",
        "Additional trusted facts",
    }
def test_presentation_uses_operator_readable_provenance_chips_and_candidate_scaffold():
    presentation = build_answer_presentation(
        query="scope",
        trusted_facts=[],
        trusted_conflicts=[],
        extracted_evidence=[
            {
                "source_path": "C:/proj/Scope.pdf",
                "page_index": 3,
                "text": "Scope includes chiller replacement and balancing work for the chilled water system.",
                "provenance": "OCR / parser output",
            }
        ],
        linked_support=[
            {
                "entity_type": "system",
                "entity_value": "Chilled water",
                "relation": "depends_on",
                "neighbor_type": "component",
                "neighbor_value": "Chiller",
                "confidence_tier": "HIGH_CONFIDENCE",
            }
        ],
        ai_lane={
            "analysis_support": [
                {
                    "source_path": "C:/proj/Scope.pdf",
                    "page_index": 0,
                    "text": "AI analysis indicates chiller replacement is in scope.",
                }
            ],
            "synthesis": "The scope appears to include chiller replacement.",
        },
        coverage={"is_complete": False, "missing_fact_types": ["document.scope_item"]},
    )
    sections = {section["title"]: section for section in presentation["sections"]}
    assert presentation["source_basis_banner"] == "Based on extracted evidence, linked support + AI synthesis."
    assert sections["Trusted Facts"]["empty_message"] == "No trusted facts found for this question."
    assert sections["Extracted Evidence"]["items"][0]["chip"] == "Extraction p.4"
    assert sections["Linked Support"]["items"][0]["chip"] == "Linked Support"
    assert "Candidate support" in sections["Linked Support"]["items"][0]["text"]
    assert sections["AI-Generated Synthesis"]["items"][0]["chip"] == "AI Analysis p.1"
    assert sections["AI-Generated Synthesis"]["items"][1]["chip"] == "AI Synthesis"
    assert presentation["candidate_fact_suggestions"]
    assert any(item["source_class"] == "extracted_evidence" for item in presentation["candidate_fact_suggestions"])
    assert any(item["source_class"] == "ai_synthesis" for item in presentation["candidate_fact_suggestions"])
    assert all("candidate_fact_suggestions" not in section for section in presentation["sections"])
def test_direct_answer_prefers_coherent_synthesis_over_clause_fragments_when_available():
    presentation = build_answer_presentation(
        query="provide project scope summary",
        trusted_facts=[
            {
                "fact_id": "f1",
                "fact_type": "document.requirement",
                "value": {"statement": "shall satisfy or"},
                "status": "VALIDATED",
                "lineage": [{"source_path": "C:/proj/Scope.pdf", "location": {"page_index": 10}}],
            },
            {
                "fact_id": "f2",
                "fact_type": "document.scope_item",
                "value": {"statement": "Must provide the most cost effective proposal, whilst observing all."},
                "status": "VALIDATED",
                "lineage": [{"source_path": "C:/proj/Scope.pdf", "location": {"page_index": 11}}],
            },
        ],
        trusted_conflicts=[],
        extracted_evidence=[],
        linked_support=[],
        ai_lane={"analysis_support": [], "synthesis": "The scope covers delivery of the required works in satisfactory operating condition, with contractor obligations for cost-effective delivery and compliance with the project requirements."},
        coverage={"is_complete": False, "missing_fact_types": []},
    )
    assert presentation["main_answer_text"].startswith("The scope covers delivery")
    assert "shall satisfy or" not in presentation["main_answer_text"]
    assert "Trusted coverage is partial" not in presentation["main_answer_text"]
    assert "\n" not in presentation["main_answer_text"]


def test_direct_answer_prefers_ai_analysis_when_trusted_facts_are_fragmentary():
    presentation = build_answer_presentation(
        query="scope",
        trusted_facts=[
            {
                "fact_id": "f1",
                "fact_type": "document.requirement",
                "value": {"statement": "shall satisfy or"},
                "status": "VALIDATED",
                "lineage": [{"source_path": "C:/proj/Scope.pdf", "location": {"page_index": 10}}],
            }
        ],
        trusted_conflicts=[],
        extracted_evidence=[],
        linked_support=[],
        ai_lane={
            "analysis_support": [
                {
                    "source_path": "C:/proj/Scope.pdf",
                    "page_index": 0,
                    "text": "The scope covers delivery of the required works in satisfactory operating condition with defined contractor obligations.",
                }
            ],
            "synthesis": "",
        },
        coverage={"is_complete": False, "missing_fact_types": []},
    )
    assert presentation["main_answer_text"].startswith("The scope covers delivery")
    assert "shall satisfy or" not in presentation["main_answer_text"]
