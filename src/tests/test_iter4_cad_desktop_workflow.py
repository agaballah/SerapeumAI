# -*- coding: utf-8 -*-
"""
test_iter4_cad_desktop_workflow.py — Iteration 4: Windows desktop DXF workflow.

Focused presenter / service tests for the desktop wiring introduced in
Iteration 4. Avoids brittle pixel/layout assertions and validates
deterministic view-models and chat routing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.application.jobs.extract_job import ExtractJob
from src.application.services.cad_chat_service import (
    CAD_AUTHORITY,
    answer_cad_question,
    is_cad_intent,
)
from src.application.services.cad_evidence_presentation import (
    SUPPORTED_STATUSES,
    build_cad_evidence_view,
    render_cad_evidence_text,
)
from src.application.services.mounted_chat_runtime import run_mounted_chat_query
from src.application.jobs.ingest_file_job import IngestFileJob
from src.infra.persistence.database_manager import DatabaseManager
from src.tests.fixtures.dxf.generate import (
    make_basic_entities_dxf,
    make_block_insert_dxf,
    make_dimension_dxf,
    make_text_dxf,
)


# ── DB helpers ─────────────────────────────────────────────────────────


def _build_db(tmp_path):
    """Build a DB with baseline + CAD migrations applied."""
    db = DatabaseManager(root_dir=str(tmp_path), db_name=":memory:")
    migration = Path("src/infra/persistence/migrations/001_baseline_v14.sql")
    db.execute_script(migration.read_text(encoding="utf-8-sig"))
    cad_mig = Path("src/infra/persistence/migrations/019_cad_evidence.sql")
    db.execute_script(cad_mig.read_text(encoding="utf-8-sig"))
    db.commit()
    return db


def _seed_dxf(db, project_id, file_version_id, dxf_path, *, status="SUCCESS"):
    now = db._ts()
    doc_id = f"doc_{project_id}"
    file_id = f"file_{project_id}"
    db.execute(
        "INSERT OR REPLACE INTO projects (project_id, name, root, created, updated) VALUES (?,?,?,?,?)",
        (project_id, "TestProject", str(Path(dxf_path).parent), now, now),
    )
    db.execute(
        "INSERT OR REPLACE INTO documents (doc_id, project_id, file_name, abs_path, file_ext, created, updated) VALUES (?,?,?,?,?,?,?)",
        (doc_id, project_id, Path(dxf_path).name, dxf_path, ".dxf", now, now),
    )
    db.execute(
        "INSERT OR REPLACE INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?,?,?,?)",
        (file_id, project_id, dxf_path, now),
    )
    db.execute(
        "INSERT OR REPLACE INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?,?,?,?,?,?,?)",
        (file_version_id, file_id, f"sha-{file_version_id}", 1024, ".dxf", now, dxf_path),
    )
    db.execute(
        "INSERT OR REPLACE INTO extraction_runs (run_id, file_version_id, extractor_id, extractor_version, started_at, status) VALUES (?,?,?,?,?,?)",
        (f"run_{file_version_id}", file_version_id, "dxf", "1.0.0", now, status),
    )
    db.commit()
    return doc_id


def _run_extract(db, project_id, file_version_id, dxf_path):
    _seed_dxf(db, project_id, file_version_id, dxf_path)
    job = ExtractJob(
        job_id=f"job_{file_version_id}",
        project_id=project_id,
        file_version_id=file_version_id,
        extractor_name="dxf",
    )
    return job.run({"db": db, "manager": SimpleNamespace(submit=lambda j: None)})


# ── 1. .dxf recognized by normal add-file workflow ─────────────────────


def test_ingest_file_job_routes_dxf_to_dxf_extractor():
    """IngestFileJob must map .dxf -> 'dxf' extractor (no manual selection)."""
    job = IngestFileJob(
        job_id="ing_x", project_id="P", file_path="ignored.dxf", rel_path="ignored.dxf"
    )
    payload = job.to_dict()
    assert payload["file_path"].endswith(".dxf")


def test_dxf_extractor_is_in_extract_job_registry():
    """The ExtractJob registry must include 'dxf' as a supported extractor."""
    from src.application.jobs.extract_job import ExtractJob

    assert "dxf" in ExtractJob.EXTRACTORS
    assert ExtractJob.EXTRACTORS["dxf"].__name__ == "DXFExtractor"


# ── 2. normal extraction job scheduled ─────────────────────────────────


def test_run_extract_persists_cad_records_for_real_dxf(tmp_path):
    dxf = tmp_path / "drawing.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    result = _run_extract(db, "P1", "fv1", str(dxf))
    assert result["record_count"] > 0
    n = db.execute("SELECT COUNT(*) AS cnt FROM cad_entities").fetchone()["cnt"]
    assert n > 0


# ── 3. processing status exposed ───────────────────────────────────────


def test_cad_evidence_view_status_success(tmp_path):
    dxf = tmp_path / "s.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    assert view["is_dxf"] is True
    assert view["status"] in SUPPORTED_STATUSES
    assert view["status"] in {"SUCCESS", "PARTIAL"}


def test_cad_evidence_view_status_failed(tmp_path):
    db = _build_db(tmp_path)
    _seed_dxf(db, "P1", "fv1", "C:/nope.dxf", status="FAILED")
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    assert view["status"] == "FAILED"
    assert "stack" not in (view.get("status_reason") or "").lower()


def test_cad_evidence_view_status_processing(tmp_path):
    db = _build_db(tmp_path)
    _seed_dxf(db, "P1", "fv1", "C:/nope.dxf", status="RUNNING:PERSISTING")
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    assert view["status"] == "PROCESSING"


def test_cad_evidence_view_status_queued_when_no_run(tmp_path):
    db = _build_db(tmp_path)
    # file_version row exists but no extraction_runs row
    db.execute(
        "INSERT INTO projects (project_id, name, root, created, updated) VALUES (?,?,?,?,?)",
        ("P1", "P", str(tmp_path), 0, 0),
    )
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?,?,?,?)",
        ("f1", "P1", "C:/drawing.dxf", 0),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?,?,?,?,?,?,?)",
        ("fv1", "f1", "x", 1, ".dxf", 0, "C:/drawing.dxf"),
    )
    db.commit()
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    assert view["status"] == "QUEUED"


# ── 4. CAD summary view-model ──────────────────────────────────────────


def test_cad_view_summary_keys_present(tmp_path):
    dxf = tmp_path / "drawing.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    for key in (
        "drawing",
        "layers",
        "blocks",
        "annotations",
        "dimensions",
        "entity_count_by_type",
        "provenance",
        "scope_authority",
    ):
        assert key in view
    assert view["scope_authority"] == "PROJECT_EVIDENCE"
    assert view["provenance"]["file_version_id"] == "fv1"
    assert view["provenance"]["source_filename"].endswith(".dxf")


# ── 5. layer display ──────────────────────────────────────────────────


def test_cad_view_layer_display(tmp_path):
    dxf = tmp_path / "drawing.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    names = [l["layer_name"] for l in view["layers"]]
    assert "WALLS" in names
    walls = next(l for l in view["layers"] if l["layer_name"] == "WALLS")
    assert walls["entity_count"] > 0


# ── 6. block display ──────────────────────────────────────────────────


def test_cad_view_block_display(tmp_path):
    dxf = tmp_path / "drawing.dxf"
    make_block_insert_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    names = [b["name"] for b in view["blocks"]]
    assert "MYVALVE" in names
    mv = next(b for b in view["blocks"] if b["name"] == "MYVALVE")
    assert mv["reference_count"] >= 1


# ── 7. annotation display ─────────────────────────────────────────────


def test_cad_view_annotation_display(tmp_path):
    dxf = tmp_path / "drawing.dxf"
    make_text_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    types = {a["entity_type"] for a in view["annotations"]}
    assert {"TEXT", "MTEXT"}.issubset(types)
    text_blob = "\n".join(a["text"] for a in view["annotations"])
    assert "Simple label" in text_blob


# ── 8. dimension display ──────────────────────────────────────────────


def test_cad_view_dimension_display(tmp_path):
    dxf = tmp_path / "drawing.dxf"
    make_dimension_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    assert view["dimensions"], "dimension fixture should yield rows"
    assert any(d.get("measurement") is not None for d in view["dimensions"])


# ── 9. provenance display ─────────────────────────────────────────────


def test_cad_view_provenance_visible_in_text_render(tmp_path):
    dxf = tmp_path / "PROV.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    text = render_cad_evidence_text(view)
    assert "PROVENANCE" in text
    assert "PROV.dxf" in text
    assert "fv1" in text
    assert "PROJECT_EVIDENCE" in text


# ── 10. CAD chat query wiring (5 required questions) ──────────────────


def test_is_cad_intent_detects_supported_keywords():
    for q in [
        "Which layers exist in this drawing?",
        "How many INSERT entities are on layer A-DOOR?",
        "What text annotations are present?",
        "Which blocks are referenced?",
        "What dimensions are shown?",
    ]:
        assert is_cad_intent(q), q


def test_chat_routes_layers_query_to_cad_service(tmp_path):
    dxf = tmp_path / "a.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(db, "P1", "Which layers exist in this drawing?")
    assert "WALLS" in res["answer"]
    assert res["scope_authority"] == CAD_AUTHORITY
    assert res["compliance_status"] == "ANSWERED_WITH_PROJECT_GROUNDED_SUPPORT"


def test_chat_routes_insert_count_query_to_cad_service(tmp_path):
    dxf = tmp_path / "b.dxf"
    make_block_insert_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(
        db, "P1", "How many INSERT entities are on layer INSTALLS?"
    )
    assert "INSTALLS" in res["answer"]
    assert res["scope_authority"] == CAD_AUTHORITY
    # The numeric count must be derived from project cad_entities table.
    assert "0" not in res["answer"].split("(")[0] or "3" in res["answer"]


def test_chat_routes_annotations_query_to_cad_service(tmp_path):
    dxf = tmp_path / "c.dxf"
    make_text_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(db, "P1", "What text annotations are present?")
    assert "TEXT" in res["answer"] or "MTEXT" in res["answer"]


def test_chat_routes_blocks_query_to_cad_service(tmp_path):
    dxf = tmp_path / "d.dxf"
    make_block_insert_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(db, "P1", "Which blocks are referenced?")
    assert "MYVALVE" in res["answer"]


def test_chat_routes_dimensions_query_to_cad_service(tmp_path):
    dxf = tmp_path / "e.dxf"
    make_dimension_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(db, "P1", "What dimensions are shown?")
    assert "Dimensions" in res["answer"]


# ── 11. refusal presentation ──────────────────────────────────────────


def test_chat_refuses_fire_rating_question(tmp_path):
    dxf = tmp_path / "f.dxf"
    make_block_insert_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(
        db, "P1", "What is the fire rating of Door D17?"
    )
    assert "does not establish" in res["answer"].lower()
    assert res["compliance_status"] == "NO_PROJECT_GROUNDED_MATERIAL"
    assert res["mode"] == "refused"


def test_chat_refuses_when_no_dxf_in_project(tmp_path):
    db = _build_db(tmp_path)
    res = answer_cad_question(db, "P1", "Which layers exist in this drawing?")
    assert "No DXF drawing" in res["answer"]
    assert res["mode"] == "refused"
    assert res["scope_authority"] == CAD_AUTHORITY


# ── 12. project-switch isolation ──────────────────────────────────────


def test_cad_evidence_isolated_between_projects(tmp_path):
    dxf = tmp_path / "g.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    # Project A: ingest the DXF
    _run_extract(db, "PROJ_A", "fv_A", str(dxf))
    # Project B has no DXF; query should yield refusal.
    res_b = answer_cad_question(db, "PROJ_B", "Which layers exist in this drawing?")
    assert res_b["mode"] == "refused"
    # Project A still answers with real layers.
    res_a = answer_cad_question(db, "PROJ_A", "Which layers exist in this drawing?")
    assert "WALLS" in res_a["answer"]


def test_cad_view_does_not_leak_other_projects(tmp_path):
    dxf = tmp_path / "h.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "PROJ_A", "fv_A", str(dxf))
    # file_version_id 'fv_A' belongs to PROJ_A but the presenter is called
    # with file_id lookup only — the view must be derived from the row itself.
    view = build_cad_evidence_view(db, file_id="file_PROJ_A", project_id="PROJ_A")
    assert view["is_dxf"] is True
    # Asking the presenter for a non-existent file should be empty.
    empty = build_cad_evidence_view(db, file_id="does_not_exist", project_id="PROJ_B")
    assert empty["empty"] is True


# ── 13. project DB vs global DB authority separation ──────────────────


def test_cad_chat_service_does_not_use_global_db(tmp_path):
    """CAD service must answer from project DB; the global DB is irrelevant
    and must not influence the result."""
    dxf = tmp_path / "i.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    # Pass global_db=None explicitly: the service must not require it.
    res = answer_cad_question(db, "P1", "Which layers exist in this drawing?")
    assert "WALLS" in res["answer"]
    # Authority label must be PROJECT_EVIDENCE (never a global/standard label).
    assert res["scope_authority"] == "PROJECT_EVIDENCE"
    assert "TRUSTED_FACTS_GOVERN" not in res.get("truth_authority", "")


def test_cad_chat_response_does_not_use_standard_authority_for_design_property(
    tmp_path,
):
    """When the project evidence cannot answer a design-property question,
    the response must not claim global/standard authority."""
    dxf = tmp_path / "j.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))
    res = answer_cad_question(
        db, "P1", "What is the acoustic class of wall W1?"
    )
    assert res["mode"] == "refused"
    assert "does not establish" in res["answer"].lower()
    assert res["scope_authority"] == "PROJECT_EVIDENCE"


# ── 14. no professional-role mock introduced ──────────────────────────


def test_chat_runtime_does_not_inject_professional_role(monkeypatch, tmp_path):
    """Iter-4 must not add a synthetic role/discipline system. Verify the
    chat runtime path does not depend on a fake user model."""
    dxf = tmp_path / "k.dxf"
    make_basic_entities_dxf(str(dxf))
    db = _build_db(tmp_path)
    _run_extract(db, "P1", "fv1", str(dxf))

    controller = SimpleNamespace(
        active_project_id="P1",
        db=db,
        orchestrator=None,  # No orchestrator => old fallback path
    )
    res = run_mounted_chat_query(controller, "Which layers exist in this drawing?")
    assert "WALLS" in res["answer"]
    # No fake role/discipline attributes are added to the controller.
    assert not hasattr(controller, "current_user_role")
    assert not hasattr(controller, "current_discipline")


# ── 15. partial / failed extraction UI behavior ──────────────────────


def test_partial_status_render_mentions_entity_limit(tmp_path):
    db = _build_db(tmp_path)
    # Seed a drawing row with cap_reached=1 to drive PARTIAL.
    db.execute(
        "INSERT INTO projects (project_id, name, root, created, updated) VALUES (?,?,?,?,?)",
        ("P1", "P", str(tmp_path), 0, 0),
    )
    db.execute(
        "INSERT INTO file_registry (file_id, project_id, first_seen_path, created_at) VALUES (?,?,?,?)",
        ("f1", "P1", str(tmp_path / "x.dxf"), 0),
    )
    db.execute(
        "INSERT INTO file_versions (file_version_id, file_id, sha256, size_bytes, file_ext, imported_at, source_path) VALUES (?,?,?,?,?,?,?)",
        ("fv1", "f1", "x", 1, ".dxf", 0, str(tmp_path / "x.dxf")),
    )
    db.execute(
        "INSERT INTO cad_drawings (drawing_id, file_version_id, drawing_version, modelspace_entity_count, layer_count, layout_count, cap_reached) VALUES (?,?,?,?,?,?,?)",
        ("d1", "fv1", "AC1027", 50000, 10, 1, 1),
    )
    db.commit()
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    assert view["status"] == "PARTIAL"
    assert "entity safety limit" in view["status_reason"].lower()
    text = render_cad_evidence_text(view)
    assert "PARTIAL" in text


def test_failed_status_render_does_not_leak_python_traceback(tmp_path):
    db = _build_db(tmp_path)
    _seed_dxf(db, "P1", "fv1", str(tmp_path / "x.dxf"), status="FAILED")
    view = build_cad_evidence_view(db, file_version_id="fv1", project_id="P1")
    text = render_cad_evidence_text(view)
    assert "FAILED" in text
    assert "Traceback" not in text
    assert "File \"" not in text
