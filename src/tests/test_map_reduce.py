from unittest.mock import MagicMock
from src.application.orchestrators.agent_orchestrator import AgentOrchestrator

def test_map_reduce_flow():
    # Setup Mocks
    db = MagicMock()
    llm = MagicMock()
    
    # Mock EvidencePackBuilder output
    mock_pack = {
        "documents": [
            {
                "doc_id": "1",
                "file_name": "Doc A.pdf",
                "status": "Found Evidence",
                "excerpts": [{"source_field": "text", "text": "The voltage is 220V."}]
            },
            {
                "doc_id": "2",
                "file_name": "Doc B.pdf",
                "status": "Found Evidence",
                "excerpts": [{"source_field": "text", "text": "The frequency is 60Hz."}]
            }
        ]
    }
    
    # Mock LLM responses
    # 1. Map: Doc A -> ["Voltage is 220V"]
    # 2. Map: Doc B -> ["Frequency is 60Hz"]
    # 3. Reduce: "system voltage is 220V at 60Hz [Doc A.pdf][Doc B.pdf]"
    
    def chat_json_side_effect(system, user, **kwargs):
        if "Doc A" in user:
            return {"facts": ["Voltage is 220V"]}
        if "Doc B" in user:
            return {"facts": ["Frequency is 60Hz"]}
        return {}

    llm.chat_json.side_effect = chat_json_side_effect
    
    llm.chat.return_value = {
        "choices": [{"message": {"content": "The system voltage is 220V at 60Hz [Doc A.pdf][Doc B.pdf]"}}]
    }
    
    orchestrator = AgentOrchestrator(db=db, llm=llm)
    # Patch the evidence builder on the instance since we can't easily mock the constructor's internal creation without more complex patching
    orchestrator.evidence_builder = MagicMock()
    orchestrator.evidence_builder.build_pack.return_value = mock_pack
    
    # Execute
    result = orchestrator.answer_question_map_reduce(query="What is the power spec?", doc_ids=["1", "2"])
    
    # Verify
    orchestrator.evidence_builder.build_pack.assert_called_once()
    assert len(result["map_results"]) == 2
    assert "220V" in result["answer"]
    assert "60Hz" in result["answer"]
    
def test_map_reduce_escape_hatch():
    # Setup Mocks
    db = MagicMock()
    llm = MagicMock()
    
    # Mock EvidencePackBuilder output - NO EVIDENCE
    mock_pack = {
        "documents": [
            {
                "doc_id": "1", 
                "file_name": "Doc A.pdf", 
                "status": "No Evidence", 
                "excerpts": []
            }
        ]
    }
    
    orchestrator = AgentOrchestrator(db=db, llm=llm)
    orchestrator.evidence_builder = MagicMock()
    orchestrator.evidence_builder.build_pack.return_value = mock_pack
    
    # Execute
    result = orchestrator.answer_question_map_reduce(query="Something obscure", doc_ids=["1"])
    
    # Verify Escape Hatch
    assert "could not find sufficient evidence" in result["answer"]
    assert len(result["map_results"]) == 0

if __name__ == "__main__":
    try:
        test_map_reduce_flow()
        print("Flow Test Passed")
        test_map_reduce_escape_hatch()
        print("Escape Hatch Test Passed")
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
