# -*- coding: utf-8 -*-
import builtins
import sys
import types
from pathlib import Path

from src.engine.extractors.ifc_extractor import IFCExtractor


def test_ifc_extractor_supported_extension_remains_ifc():
    assert IFCExtractor().supported_extensions == [".ifc"]


def test_missing_ifcopenshell_fails_honestly_without_records(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "ifcopenshell" or name.startswith("ifcopenshell."):
            raise ImportError("simulated missing ifcopenshell")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    result = IFCExtractor().extract("model.ifc")

    assert result.success is False
    assert result.records == []
    diagnostic_text = "\n".join(result.diagnostics).lower()
    assert "ifcopenshell" in diagnostic_text
    assert "missing" in diagnostic_text
    assert "no fallback" in diagnostic_text
    assert "regex" not in diagnostic_text


def test_ifc_extractor_source_does_not_claim_regex_text_fallback():
    source = Path("src/engine/extractors/ifc_extractor.py").read_text(encoding="utf-8-sig").lower()

    assert "regex/text" not in source
    assert "good enough for phase 1" not in source
    assert "no text/regex fallback" in source
    assert "no fallback ifc parser is enabled" in source


class FakeEntity:
    def __init__(self, entity_type, global_id, name=None):
        self._entity_type = entity_type
        self.GlobalId = global_id
        self.Name = name
        self.IsDecomposedBy = []

    def is_a(self, entity_type=None):
        if entity_type is None:
            return self._entity_type
        return self._entity_type == entity_type


class FakeConnection:
    def __init__(self):
        self.RelatingElement = FakeEntity("IfcWall", "wall-guid-001", "Wall")
        self.RelatedElement = FakeEntity("IfcSlab", "slab-guid-002", "Slab")

    def is_a(self, entity_type=None):
        if entity_type is None:
            return "IfcRelConnectsElements"
        return entity_type == "IfcRelConnectsElements"


class FakeModel:
    def __init__(self):
        self.project = FakeEntity("IfcProject", "project-guid-001", "Project")
        self.site = FakeEntity("IfcSite", "site-guid-001", "Site")
        self.product = FakeEntity("IfcWall", "wall-guid-001", "Wall")
        self.connection = FakeConnection()

    def by_type(self, entity_type):
        if entity_type == "IfcProject":
            return [self.project]
        if entity_type == "IfcSite":
            return [self.site]
        if entity_type == "IfcProduct":
            return [self.product]
        if entity_type == "IfcRelConnectsElements":
            return [self.connection]
        return []


def test_ifc_available_dependency_emits_only_known_contract_record_types(monkeypatch):
    fake_model = FakeModel()

    ifcopenshell_mod = types.ModuleType("ifcopenshell")
    util_mod = types.ModuleType("ifcopenshell.util")
    element_mod = types.ModuleType("ifcopenshell.util.element")

    ifcopenshell_mod.open = lambda file_path: fake_model
    element_mod.get_psets = lambda product: {
        "Pset_WallCommon": {"FireRating": "2HR"},
        "BaseQuantities": {"NetVolume": 12.5},
    }
    util_mod.element = element_mod
    ifcopenshell_mod.util = util_mod

    monkeypatch.setitem(sys.modules, "ifcopenshell", ifcopenshell_mod)
    monkeypatch.setitem(sys.modules, "ifcopenshell.util", util_mod)
    monkeypatch.setitem(sys.modules, "ifcopenshell.util.element", element_mod)

    result = IFCExtractor().extract("model.ifc")

    assert result.success is True
    record_types = {record["type"] for record in result.records}
    assert record_types == {
        "ifc_project",
        "ifc_spatial",
        "ifc_element_metadata",
        "ifc_connection",
    }

    assert all(record["provenance"].get("entity") for record in result.records)
    assert any("Successfully parsed" in item for item in result.diagnostics)
