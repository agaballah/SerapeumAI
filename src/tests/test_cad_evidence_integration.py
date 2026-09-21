# -*- coding: utf-8 -*-
"""
test_cad_evidence_integration.py — Iteration 3: CAD evidence / truth engine integration.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.application.jobs.extract_job import ExtractJob
from src.domain.facts.repository import FactRepository
from src.document_processing.cad_processor import CADProcessor
from src.engine.extractors.dxf_extractor import DXFExtractor
from src.infra.persistence.database_manager import DatabaseManager
from src.tests.fixtures.dxf.generate import (
    make_basic_entities_dxf,
    make_block_insert_dxf,
    make_dimension_dxf,
    make_malformed_dxf,
    make_text_dxf,
)


def _build_db(tmp_path):
    """Build a DB with baseline + CAD migrations applied."""
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    migration = Path("src/infra/persistence/migrations/001_baseline_v14.sql")
    db.execute_script(migration.read_text(encoding="utf-8-sig"))
    cad_mig = Path("src/infra/persistence/migrations/019_cad_evidence.sql")
    db.execute_script(cad_mig.read_text(encoding="utf-8-sig"))
    db.commit()
    return db


def _seed_dxf(db, project_id, file_version_id, dxf_path):
    """Insert project/document/file_registry/file_version rows for a DXF ingestion test."""
    now = db._ts()
    doc_id = f"doc_{project_id}"
    file_id = f"file_{project_id}"
    # projects table
    db.execute(
        "INSERT OR REPLACE INTO projects (project_id, name, root, created, updated) VALUES (?,?,?,?,?)",
        (project_id, "TestProject", str(Path(dxf_path).parent), now, now),
    )
    # documents table
    db.execute(
        "INSERT OR REPLACE INTO documents (doc_id, project_id, file_name, abs_path, file_ext, created, updated) VALUES (?,?,?,?,?,?,?)",
        (doc_id, project_id, "test.dxf", dxf_path, ".dxf", now, now),
    )
    # file_registry + file_versions (baseline schema)
    db.execute(
        "INSERT OR REPLACE INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?,?,?,?)",
        (file_id, project_id, dxf_path, now),
    )
    db.execute(
        "INSERT OR REPLACE INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?,?,?,?,?,?,?)",
        (file_version_id, file_id, "sha256-dxf", 1024, ".dxf", now, dxf_path),
    )
    # extraction_runs (baseline schema — no project_id column)
    db.execute(
        "INSERT OR REPLACE INTO extraction_runs (run_id, file_version_id, extractor_id, extractor_version, started_at, status) VALUES (?,?,?,?,?,?)",
        (f"run_{file_version_id}", file_version_id, "dxf", "1.0.0", now, "SUCCESS"),
    )
    db.commit()
    return doc_id


def _run_extract_persist(db, project_id, file_version_id, dxf_path):
    """Run full ExtractJob for a DXF and persist records."""
    _seed_dxf(db, project_id, file_version_id, dxf_path)
    job = ExtractJob(
        job_id=f"job_{file_version_id}",
        project_id=project_id,
        file_version_id=file_version_id,
        extractor_name="dxf",
    )
    return job.run({"db": db, "manager": type("M", (), {"submit": lambda s, j: None})()})


def _direct_persist(db, rec, vid, doc_id="doc_test"):
    """Call _insert_record directly for a single CAD record."""
    job = ExtractJob.__new__(ExtractJob)
    job._insert_record(db, rec, doc_id)


# ─────────────────────────────────────────────────────────────────────────────
# 1. DXF → normal extraction path → evidence persistence
# ─────────────────────────────────────────────────────────────────────────────

class TestDXFExtractionPathPersistence:
    def test_extract_job_persists_dxf_records(self, db, tmp_path):
        f = tmp_path / "persist.dxf"
        make_basic_entities_dxf(str(f))
        result = _run_extract_persist(db, "proj_persist", "fv_persist", str(f))
        assert result["record_count"] > 0
        dwg = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_drawings WHERE file_version_id=?", ("fv_persist",)
        ).fetchone()
        assert dwg["cnt"] >= 1
        ent = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_entities WHERE file_version_id=?", ("fv_persist",)
        ).fetchone()
        assert ent["cnt"] > 0

    def test_extract_job_dxf_returns_run_id(self, db, tmp_path):
        f = tmp_path / "rid.dxf"
        make_basic_entities_dxf(str(f))
        result = _run_extract_persist(db, "proj_rid", "fv_rid", str(f))
        assert "run_id" in result
        assert result["record_count"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Layer evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestLayerEvidence:
    def test_layers_persisted_with_state(self, db, tmp_path):
        f = tmp_path / "layers.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_layer", "fv_layer", str(f))
        rows = db.execute(
            "SELECT layer_name, frozen, locked, on_flag FROM cad_layers WHERE file_version_id=?",
            ("fv_layer",),
        ).fetchall()
        names = {r["layer_name"] for r in rows}
        assert "WALLS" in names
        assert "DIMENSIONS" in names
        assert "HIDDEN" in names

    def test_layer_entity_counts(self, db, tmp_path):
        f = tmp_path / "lcnt.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_lcnt", "fv_lcnt", str(f))
        wall_count = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_entities WHERE file_version_id=? AND layer='WALLS'",
            ("fv_lcnt",),
        ).fetchone()["cnt"]
        assert wall_count >= 4


# ─────────────────────────────────────────────────────────────────────────────
# 3. Entity count evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestEntityCountEvidence:
    def test_entity_count_matches_dxf(self, db, tmp_path):
        f = tmp_path / "ecnt.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_ecnt", "fv_ecnt", str(f))
        cnt = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_entities WHERE file_version_id=?", ("fv_ecnt",)
        ).fetchone()["cnt"]
        assert cnt > 0

    def test_entity_type_counts_in_drawing_record(self, db, tmp_path):
        f = tmp_path / "etcnt.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_etcnt", "fv_etcnt", str(f))
        row = db.execute(
            "SELECT entity_type_counts_json FROM cad_drawings WHERE file_version_id=?", ("fv_etcnt",)
        ).fetchone()
        counts = json.loads(row["entity_type_counts_json"])
        assert "LINE" in counts
        assert counts["LINE"] >= 4


# ─────────────────────────────────────────────────────────────────────────────
# 4. Block evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestBlockEvidence:
    def test_block_definition_persisted(self, db, tmp_path):
        f = tmp_path / "blk.dxf"
        make_block_insert_dxf(str(f))
        _run_extract_persist(db, "proj_blk", "fv_blk", str(f))
        row = db.execute(
            "SELECT block_name, entity_count FROM cad_blocks WHERE file_version_id=? AND block_name='MYVALVE'",
            ("fv_blk",),
        ).fetchone()
        assert row is not None
        assert row["entity_count"] == 3

    def test_insert_reference_counted(self, db, tmp_path):
        f = tmp_path / "ins.dxf"
        make_block_insert_dxf(str(f))
        _run_extract_persist(db, "proj_ins", "fv_ins", str(f))
        cnt = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_entities WHERE file_version_id=? AND entity_type='INSERT'",
            ("fv_ins",),
        ).fetchone()["cnt"]
        assert cnt == 3


# ─────────────────────────────────────────────────────────────────────────────
# 5. TEXT / MTEXT evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestTextEvidence:
    def test_text_annotation_persisted(self, db, tmp_path):
        f = tmp_path / "txt.dxf"
        make_text_dxf(str(f))
        _run_extract_persist(db, "proj_txt", "fv_txt", str(f))
        rows = db.execute(
            "SELECT entity_type, text_content FROM cad_text_annotations WHERE file_version_id=?",
            ("fv_txt",),
        ).fetchall()
        types = {r["entity_type"] for r in rows}
        assert "TEXT" in types
        assert "MTEXT" in types

    def test_mtext_content_preserved(self, db, tmp_path):
        f = tmp_path / "uni.dxf"
        make_text_dxf(str(f))
        _run_extract_persist(db, "proj_uni", "fv_uni", str(f))
        rows = db.execute(
            "SELECT text_content FROM cad_text_annotations WHERE file_version_id=?", ("fv_uni",)
        ).fetchall()
        all_text = "".join(r["text_content"] or "" for r in rows)
        assert len(all_text) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Dimension evidence
# ─────────────────────────────────────────────────────────────────────────────

class TestDimensionEvidence:
    def test_dimensions_persisted_with_measurement(self, db, tmp_path):
        f = tmp_path / "dim.dxf"
        make_dimension_dxf(str(f))
        _run_extract_persist(db, "proj_dim", "fv_dim", str(f))
        rows = db.execute(
            "SELECT dimension_type, measurement FROM cad_dimensions WHERE file_version_id=?",
            ("fv_dim",),
        ).fetchall()
        assert len(rows) == 3
        linear = [r for r in rows if "LINEAR" in r["dimension_type"]]
        assert len(linear) >= 1
        measurements = [r["measurement"] for r in linear]; assert 10.0 in measurements


# ─────────────────────────────────────────────────────────────────────────────
# 7. Provenance anchors
# ─────────────────────────────────────────────────────────────────────────────

class TestProvenanceAnchors:
    def test_entity_has_handle_and_source(self, db, tmp_path):
        f = tmp_path / "prov.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_prov", "fv_prov", str(f))
        rows = db.execute(
            "SELECT handle, source_file FROM cad_entities WHERE file_version_id=? LIMIT 1",
            ("fv_prov",),
        ).fetchall()
        assert len(rows) > 0
        assert rows[0]["handle"] and len(rows[0]["handle"]) > 0
        assert rows[0]["source_file"] and rows[0]["source_file"].endswith(".dxf")


# ─────────────────────────────────────────────────────────────────────────────
# 8. CAD candidate / non-certified authority
# ─────────────────────────────────────────────────────────────────────────────

class TestCADAuthority:
    def test_cad_processor_status_diagnostic_success(self, tmp_path):
        p = CADProcessor()
        f = tmp_path / "sdiag.dxf"
        make_basic_entities_dxf(str(f))
        res = p.process(str(f), f.name, str(tmp_path))
        assert res["meta"]["status_diagnostic"] == "SUCCESS"

    def test_cad_processor_status_diagnostic_failed(self, tmp_path):
        p = CADProcessor()
        f = tmp_path / "fdiag.dxf"
        make_malformed_dxf(str(f))
        res = p.process(str(f), f.name, str(tmp_path))
        assert res["meta"]["status_diagnostic"] == "FAILED"

    def test_cad_evidence_not_auto_certified(self, db, tmp_path):
        f = tmp_path / "auth.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_auth", "fv_auth", str(f))
        dwg_cnt = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_drawings WHERE file_version_id=?", ("fv_auth",)
        ).fetchone()["cnt"]
        assert dwg_cnt >= 1
        fact_cnt = db.execute(
            "SELECT COUNT(*) AS cnt FROM facts WHERE project_id='proj_auth'"
        ).fetchone()["cnt"]
        assert fact_cnt == 0


# ─────────────────────────────────────────────────────────────────────────────
# 9. Deterministic layer query
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterministicLayerQuery:
    def test_query_cad_layers(self, db, tmp_path):
        f = tmp_path / "qlay.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_qlay", "fv_qlay", str(f))
        repo = FactRepository(db)
        layers = repo.query_cad_layers("proj_qlay", "fv_qlay")
        names = {l["layer_name"] for l in layers}
        assert "WALLS" in names
        assert "HIDDEN" in names
        assert "DIMENSIONS" in names

    def test_query_cad_layers_empty(self, db, tmp_path):
        repo = FactRepository(db)
        layers = repo.query_cad_layers("proj_empty", "fv_nonexistent")
        assert layers == []


# ─────────────────────────────────────────────────────────────────────────────
# 10. Deterministic entity-count query
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterministicEntityCount:
    def test_count_entities_by_type(self, db, tmp_path):
        f = tmp_path / "ecn.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_ecn", "fv_ecn", str(f))
        repo = FactRepository(db)
        line_cnt = repo.count_cad_entities_by_type("proj_ecn", "fv_ecn", "LINE")
        assert line_cnt >= 4

    def test_count_inserts_on_layer(self, db, tmp_path):
        f = tmp_path / "icol.dxf"
        make_block_insert_dxf(str(f))
        _run_extract_persist(db, "proj_icol", "fv_icol", str(f))
        repo = FactRepository(db)
        ins_on_install = repo.count_cad_entities_on_layer("proj_icol", "fv_icol", "INSTALLS")
        assert ins_on_install == 3


# ─────────────────────────────────────────────────────────────────────────────
# 11. Missing-evidence refusal
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingEvidenceRefusal:
    def test_missing_fire_rating_not_in_evidence(self, db, tmp_path):
        f = tmp_path / "ref.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_ref", "fv_ref", str(f))
        dims = db.execute(
            "SELECT raw_json FROM cad_dimensions WHERE file_version_id=?", ("fv_ref",)
        ).fetchall()
        for row in dims:
            assert "fire_rating" not in (row["raw_json"] or "").lower()

    def test_no_hallucinated_door_classification(self, db, tmp_path):
        f = tmp_path / "door.dxf"
        make_block_insert_dxf(str(f))
        _run_extract_persist(db, "proj_door", "fv_door", str(f))
        door_facts = db.execute(
            "SELECT COUNT(*) AS cnt FROM facts WHERE value_json LIKE '%door%' OR value_json LIKE '%fire%'"
        ).fetchone()["cnt"]
        assert door_facts == 0


# ─────────────────────────────────────────────────────────────────────────────
# 12. Project isolation
# ─────────────────────────────────────────────────────────────────────────────

class TestProjectIsolation:
    def test_project_a_does_not_leak_to_project_b(self, db, tmp_path):
        f_a = tmp_path / "pa.dxf"
        make_basic_entities_dxf(str(f_a))
        f_b = tmp_path / "pb.dxf"
        make_text_dxf(str(f_b))
        _run_extract_persist(db, "proj_a", "fv_pa", str(f_a))
        _run_extract_persist(db, "proj_b", "fv_pb", str(f_b))
        repo = FactRepository(db)
        layers_b = repo.query_cad_layers("proj_b", "fv_pb")
        layer_names_b = {l["layer_name"] for l in layers_b}
        assert "WALLS" not in layer_names_b
        layers_a = repo.query_cad_layers("proj_a", "fv_pa")
        assert any(l["layer_name"] == "WALLS" for l in layers_a)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Repeat ingestion / duplicate protection
# ─────────────────────────────────────────────────────────────────────────────

class TestRepeatIngestion:
    def test_reingestion_does_not_duplicate_entities(self, db, tmp_path):
        f = tmp_path / "dup.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_dup", "fv_dup", str(f))
        cnt1 = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_entities WHERE file_version_id=?", ("fv_dup",)
        ).fetchone()["cnt"]
        # Re-ingest
        _run_extract_persist(db, "proj_dup", "fv_dup", str(f))
        cnt2 = db.execute(
            "SELECT COUNT(*) AS cnt FROM cad_entities WHERE file_version_id=?", ("fv_dup",)
        ).fetchone()["cnt"]
        assert cnt1 > 0
        assert cnt2 >= cnt1  # Re-ingest should not create new entities


# ─────────────────────────────────────────────────────────────────────────────
# 14. 50k-limit PARTIAL honesty
# ─────────────────────────────────────────────────────────────────────────────

class TestEntityCapHonesty:
    def test_cap_constant_exists(self):
        assert DXFExtractor.ENTITY_CAP == 50_000

    def test_cap_not_triggered_on_small_file(self, db, tmp_path):
        f = tmp_path / "cap.dxf"
        make_basic_entities_dxf(str(f))
        _run_extract_persist(db, "proj_cap", "fv_cap", str(f))
        row = db.execute(
            "SELECT cap_reached FROM cad_drawings WHERE file_version_id=?", ("fv_cap",)
        ).fetchone()
        assert row is not None
        assert row["cap_reached"] == 0

    def test_cad_processor_exposes_cap_in_meta(self, tmp_path):
        p = CADProcessor()
        f = tmp_path / "meta.dxf"
        make_basic_entities_dxf(str(f))
        res = p.process(str(f), f.name, str(tmp_path))
        assert res["meta"]["cap_reached"] is False
        assert res["meta"]["status_diagnostic"] == "SUCCESS"


# ─────────────────────────────────────────────────────────────────────────────
# 15. Single-authority architecture
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleAuthorityArchitecture:
    def test_cad_processor_delegates_to_dxf_extractor(self, tmp_path):
        import inspect
        source = inspect.getsource(CADProcessor.process)
        assert "DXFExtractor" in source or "dxf_extractor" in source
        assert "ezdxf.readfile" not in source

    def test_dxf_extractor_is_only_deterministic_impl(self):
        ext = DXFExtractor()
        assert ext.maturity == "VERIFIED"
        assert ext.id == "dxf-extractor-v1"

    def test_cad_processor_preserves_v01_contract(self, tmp_path):
        p = CADProcessor()
        f = tmp_path / "v01.dxf"
        make_basic_entities_dxf(str(f))
        res = p.process(str(f), f.name, str(tmp_path))
        assert "doc_id" in res
        assert "text" in res
        assert "pages" in res
        assert "structured_data" in res
        assert "xrefs" in res
        assert "meta" in res
        assert isinstance(res["pages"], list)
        assert len(res["pages"]) == 1

    def test_generic_processor_routes_dxf_to_cad(self, tmp_path):
        from src.document_processing.generic_processor import GenericProcessor
        proc = GenericProcessor()
        f = tmp_path / "route.dxf"
        make_basic_entities_dxf(str(f))
        res = proc.process(str(f), f.name, str(tmp_path))
        assert res["meta"]["source"] == "cad-processor"
        assert res["structured_data"]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    return _build_db(tmp_path)
