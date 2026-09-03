# -*- coding: utf-8 -*-
"""
Reusable IFC test doubles for unit-level isolation from ifcopenshell.

These classes replicate the minimal ifcopenshell API surface required by
IFCExtractor so that extraction logic can be tested without the real package.
They are NOT used for golden-fixture testing — golden fixtures use real .ifc files.
"""


class FakeEntity:
    """Minimal ifcopenshell-entity substitute."""

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
    """Substitute for IfcRelConnectsElements."""

    def __init__(self):
        self.RelatingElement = FakeEntity("IfcWall", "wall-guid-001", "Wall")
        self.RelatedElement = FakeEntity("IfcSlab", "slab-guid-002", "Slab")

    def is_a(self, entity_type=None):
        if entity_type is None:
            return "IfcRelConnectsElements"
        return entity_type == "IfcRelConnectsElements"


class FakeModel:
    """Minimal IFC model with one project, one site, one product, one connection."""

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


def make_fake_ifcopenshell(fake_model, psets=None):
    """Build monkeypatch-ready fake ifcopenshell modules."""
    import sys
    import types

    if psets is None:
        psets = {
            "Pset_WallCommon": {"FireRating": "2HR"},
            "BaseQuantities": {"NetVolume": 12.5},
        }

    ifcopenshell_mod = types.ModuleType("ifcopenshell")
    util_mod = types.ModuleType("ifcopenshell.util")
    element_mod = types.ModuleType("ifcopenshell.util.element")

    ifcopenshell_mod.open = lambda file_path: fake_model
    element_mod.get_psets = lambda product: psets
    util_mod.element = element_mod
    ifcopenshell_mod.util = util_mod

    # Register so the extractor's import resolution finds them
    sys.modules["ifcopenshell"] = ifcopenshell_mod
    sys.modules["ifcopenshell.util"] = util_mod
    sys.modules["ifcopenshell.util.element"] = element_mod

    return ifcopenshell_mod, util_mod, element_mod
