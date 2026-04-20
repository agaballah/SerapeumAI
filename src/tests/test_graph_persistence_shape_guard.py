from src.analysis_engine.page_analysis import PageAnalyzer, _normalize_graph_text_value


class FakeDB:
    def __init__(self):
        self.entity_values = []
        self.links = []
        self.page_upserts = []

    def upsert_page(self, page_rec):
        self.page_upserts.append(page_rec)

    def get_document(self, doc_id):
        return {"project_id": "project-1", "doc_id": doc_id}

    def upsert_entity_node(self, project_id, doc_id, entity_type, value):
        self.entity_values.append(value)
        return len(self.entity_values)

    def insert_entity_link(self, project_id, doc_id, src_id, dst_id, rtype):
        self.links.append((project_id, doc_id, src_id, dst_id, rtype))


def test_normalize_graph_text_value_sanitizes_list_shapes():
    assert _normalize_graph_text_value(["Pump", "AHU-01"]) == "Pump | AHU-01"
    assert _normalize_graph_text_value({"source": ["Panel A", "Panel B"]}) == "source: Panel A | Panel B"


def test_save_result_sanitizes_graph_values_before_persistence():
    db = FakeDB()
    analyzer = PageAnalyzer.__new__(PageAnalyzer)
    analyzer.db = db
    analyzer.llm = None

    analyzer._save_result(
        doc_id="doc-1",
        page_index=0,
        summary="summary",
        page_type="drawing",
        entities=[["Pump", "AHU-01"], "Chiller"],
        relationships=[
            {
                "source": ["Pump", "P-01"],
                "relation": ["feeds"],
                "target": ["AHU", "01"],
            }
        ],
    )

    assert db.page_upserts, "page result should still be persisted"
    assert "Pump | AHU-01" in db.entity_values
    assert "Chiller" in db.entity_values
    assert "Pump | P-01" in db.entity_values
    assert "AHU | 01" in db.entity_values
    assert db.links, "relationship links should still be persisted"
