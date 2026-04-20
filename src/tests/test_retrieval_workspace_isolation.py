from pathlib import Path

from src.application.orchestrators.agent_orchestrator import AgentOrchestrator
from src.infra.persistence.database_manager import DatabaseManager
from src.domain.models.page_record import PageRecord


class _LLMStub:
    def chat(self, **kwargs):
        return {"choices": [{"message": {"content": "AI synthesis."}}]}


def test_extracted_and_ai_support_are_project_scoped(tmp_path):
    db = DatabaseManager(root_dir=str(tmp_path), project_id="ProjectA")
    db.upsert_document(doc_id="docA", project_id="ProjectA", file_name="a.pdf", rel_path="a.pdf", abs_path=str(tmp_path / "a.pdf"), file_ext=".pdf", created=db._ts(), updated=db._ts(), meta_json="{}", content_text="")
    db.upsert_document(doc_id="docB", project_id="ProjectB", file_name="b.pdf", rel_path="b.pdf", abs_path=str(tmp_path / "b.pdf"), file_ext=".pdf", created=db._ts(), updated=db._ts(), meta_json="{}", content_text="")
    db.upsert_page(PageRecord(doc_id='docA', page_index=0, py_text='Scope includes modular construction works.', page_summary_short='AI says modular construction is in scope.'))
    db.upsert_page(PageRecord(doc_id='docB', page_index=0, py_text='Scope includes foreign project content only.', page_summary_short='AI says foreign project content only.'))

    orch = AgentOrchestrator(db=db, llm=_LLMStub(), rag=None)
    extracted = orch._retrieve_extracted_evidence(query='scope', project_id='ProjectA')
    ai_support = orch._retrieve_ai_analysis_support(query='scope', project_id='ProjectA')

    assert extracted
    assert all('foreign project content only' not in item['text'].lower() for item in extracted)
    assert ai_support
    assert all('foreign project content only' not in item['text'].lower() for item in ai_support)
