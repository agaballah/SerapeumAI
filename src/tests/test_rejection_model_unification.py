# -*- coding: utf-8 -*-
import sys
import types

# Minimal stubs required for importing FactQueryAPI in this trimmed repo snapshot.
rule_runner_mod = types.ModuleType('src.engine.validation.rule_runner')
class RuleRunner:
    def __init__(self, db):
        self.db = db
    def validate_fact(self, fact):
        return []
rule_runner_mod.RuleRunner = RuleRunner
sys.modules['src.engine.validation.rule_runner'] = rule_runner_mod

std_mod = types.ModuleType('src.compliance.standard_enricher')
class StandardEnricher:
    def lookup_clauses_by_concept(self, concept):
        return []
std_mod.StandardEnricher = StandardEnricher
sys.modules['src.compliance.standard_enricher'] = std_mod

from src.domain.facts.models import (
    CANONICAL_REJECTED_STATUS,
    FactStatus,
    canonicalize_fact_status,
    is_rejected_fact_status,
    is_trusted_fact_status,
)
from src.application.api.fact_api import FactQueryAPI


class _EmptyResult:
    def fetchall(self):
        return []


class FakeDB:
    def execute(self, sql, params=()):
        return _EmptyResult()


def test_legacy_refused_normalizes_to_canonical_rejected():
    assert CANONICAL_REJECTED_STATUS == FactStatus.REJECTED.value
    assert canonicalize_fact_status('REFUSED') == FactStatus.REJECTED.value
    assert canonicalize_fact_status('REJECTED') == FactStatus.REJECTED.value


def test_rejected_lane_is_not_trusted():
    assert is_rejected_fact_status('REFUSED') is True
    assert is_rejected_fact_status('REJECTED') is True
    assert is_trusted_fact_status('REFUSED') is False
    assert is_trusted_fact_status('REJECTED') is False


def test_fact_api_surfaces_canonical_rejected_status():
    api = FactQueryAPI(FakeDB())
    enriched = api._enrich_with_lineage({
        'fact_id': 'f1',
        'status': 'REFUSED',
        'value_json': '"value"',
    })
    assert enriched['status'] == FactStatus.REJECTED.value
