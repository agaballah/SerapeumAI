# -*- coding: utf-8 -*-
import pytest
import os
import sqlite3
from src.infra.persistence.database_manager import DatabaseManager
from src.domain.intelligence.template_router import TemplateRouter
from src.domain.intelligence.truth_graph import TruthGraphService
from src.domain.facts.authority_service import AuthorityService
from src.domain.facts.models import Fact, FactStatus, ValueType

@pytest.fixture
def test_db():
    # Use in-memory for fast v2 logic verification
    db = DatabaseManager(root_dir="tmp_tests", db_name=":memory:")
    
    # 1. Load Baseline v14
    baseline_path = "d:/SerapeumAI/src/infra/persistence/migrations/001_baseline_v14.sql"
    with open(baseline_path, "r", encoding="utf-8") as f:
        db.execute_script(f.read())
        
    # 2. Load v16 (missing columns fix)
    v16_path = "d:/SerapeumAI/src/infra/persistence/migrations/016_fix_missing_column.sql"
    if os.path.exists(v16_path):
        with open(v16_path, "r", encoding="utf-8") as f:
            db.execute_script(f.read())

    # 3. Load v17 (Truth Engine v2)
    migration_path = "d:/SerapeumAI/src/infra/persistence/migrations/017_truth_engine_v2.sql"
    with open(migration_path, "r", encoding="utf-8") as f:
        db.execute_script(f.read())
    
    return db

def test_template_router():
    router = TemplateRouter()
    
    # Test routing
    matches = router.route_query("What is the risk for the Phase 1 handover?")
    assert len(matches) > 0
    assert matches[0]["id"] == "milestone_risk"
    
    # Test requirement aggregation
    reqs = router.get_required_facts(["milestone_risk"])
    assert "SCHEDULE" in reqs
    assert "PROCUREMENT" in reqs
    assert "schedule_milestone_date" in reqs["SCHEDULE"]

def test_truth_graph_traversal(test_db):
    graph = TruthGraphService(test_db)
    
    # Setup mock graph
    # 1. Activities
    test_db.execute("INSERT INTO entity_nodes (project_id, entity_type, value) VALUES (?, ?, ?)", ("p1", "activity", "A1020"))
    # 2. Drawings
    test_db.execute("INSERT INTO entity_nodes (project_id, entity_type, value) VALUES (?, ?, ?)", ("p1", "drawing", "D-001"))
    
    # 3. Link them
    test_db.execute("INSERT INTO entity_links (project_id, from_entity_id, to_entity_id, rel_type, confidence_tier) VALUES (?, ?, ?, ?, ?)", ("p1", 1, 2, "documented_by", "AUTO_VALIDATED"))
    
    # Test neighbors
    neighbors = graph.get_neighbors(1)
    assert len(neighbors) == 1
    assert neighbors[0]["value"] == "D-001"
    
    # Test domain search
    results = graph.find_path_to_domain(1, "DOC_CONTROL")
    assert len(results) == 1
    assert results[0]["entity"]["value"] == "D-001"

def test_authority_certification(test_db):
    auth = AuthorityService(test_db)
    
    # Setup a fact
    test_db.execute("""
        INSERT INTO facts (fact_id, project_id, fact_type, subject_kind, subject_id, status, domain, created_at, updated_at, value_type, as_of_json, method_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("f1", "p1", "date", "activity", "A101", "CANDIDATE", "SCHEDULE", 0, 0, "TEXT", "{}", "test"))
    
    # Non-authorized role
    success = auth.authorize_certificate("f1", "JUNIOR_ENG")
    assert success is False
    
    # Authorized role (Baseline says PLANNER for SCHEDULE)
    success = auth.authorize_certificate("f1", "PLANNER")
    assert success is True
    
    # Verify status change
    row = test_db.execute("SELECT status FROM facts WHERE fact_id = ?", ("f1",)).fetchone()
    assert row["status"] == "HUMAN_CERTIFIED"
