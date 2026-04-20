# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
from pathlib import Path

# Minimal stubs for trimmed repo.
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

models_spec = importlib.util.spec_from_file_location(
    'src.domain.facts.models', str((Path(__file__).resolve().parents[2] / 'src/domain/facts/models.py'))
)
models = importlib.util.module_from_spec(models_spec)
sys.modules['src.domain.facts.models'] = models
models_spec.loader.exec_module(models)

fact_api_spec = importlib.util.spec_from_file_location(
    'src.application.api.fact_api', str((Path(__file__).resolve().parents[2] / 'src/application/api/fact_api.py'))
)
fact_api_mod = importlib.util.module_from_spec(fact_api_spec)
sys.modules['src.application.api.fact_api'] = fact_api_mod
fact_api_spec.loader.exec_module(fact_api_mod)

FactStatus = models.FactStatus
TRUSTED_FACT_STATUSES = models.TRUSTED_FACT_STATUSES
AI_GENERATED_PROVENANCE = models.AI_GENERATED_PROVENANCE
canonicalize = models.normalize_rejection_status
is_trusted = models.is_trusted_fact_status
FactQueryAPI = fact_api_mod.FactQueryAPI


class FakeRows(list):
    def fetchall(self):
        return self
    def fetchone(self):
        return self[0] if self else None


class FakeDB:
    def execute(self, sql, params=()):
        if 'FROM facts' in sql and "status = 'CANDIDATE'" in sql:
            return FakeRows([
                {
                    'fact_id': 'cand1',
                    'project_id': 'proj1',
                    'fact_type': 'document.profile',
                    'subject_kind': 'query',
                    'subject_id': 'query_1',
                    'status': FactStatus.CANDIDATE.value,
                    'value_json': '"summary"',
                    'method_id': 'query_derivation_v1',
                }
            ])
        if 'FROM fact_inputs' in sql:
            return FakeRows([])
        return FakeRows([])


def test_trusted_core_is_exactly_validated_and_human_certified():
    assert TRUSTED_FACT_STATUSES == (
        FactStatus.VALIDATED.value,
        FactStatus.HUMAN_CERTIFIED.value,
    )
    assert is_trusted('VALIDATED') is True
    assert is_trusted('HUMAN_CERTIFIED') is True
    assert is_trusted('CANDIDATE') is False
    assert is_trusted('AI_GENERATED') is False


def test_legacy_refused_maps_to_canonical_rejected():
    assert canonicalize('REFUSED') == FactStatus.REJECTED.value
    assert canonicalize('REJECTED') == FactStatus.REJECTED.value


def test_candidate_support_is_non_governing_and_ai_generated():
    api = FactQueryAPI(FakeDB())
    result = api.get_candidate_facts('summarize document', project_id='proj1')
    assert result['governs_answers'] is False
    assert result['supporting_only'] is True
    assert result['provenance_class'] == AI_GENERATED_PROVENANCE
    assert result['requires_trust_promotion'] is True
    assert 'NOT ANSWER-GOVERNING' in result['formatted_context']


def test_main_answer_path_uses_sourced_multi_lane_sections_and_non_governing_ai_labeling():
    source = (Path(__file__).resolve().parents[2] / 'src/application/orchestrators/agent_orchestrator.py').read_text()
    start = source.index('def answer_question(')
    end = source.index('def _derive_candidate_facts_from_evidence(')
    answer_source = source[start:end]
    assert '## Trusted Facts' in answer_source
    assert '## Extracted Evidence' in answer_source
    assert '## Linked Support' in answer_source
    assert '## AI-Generated Synthesis' in answer_source
    assert 'non-governing' in answer_source
