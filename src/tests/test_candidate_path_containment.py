# -*- coding: utf-8 -*-
import ast
import importlib.util
import sys
import types
from pathlib import Path

# Stub missing dependencies so the trimmed repo copy can import FactQueryAPI.
rule_runner_mod = types.ModuleType('src.engine.validation.rule_runner')
class RuleRunner:
    def __init__(self, db):
        self.db = db
    def validate_facts(self, facts):
        return []
rule_runner_mod.RuleRunner = RuleRunner
sys.modules['src.engine.validation.rule_runner'] = rule_runner_mod

standard_enricher_mod = types.ModuleType('src.compliance.standard_enricher')
class StandardEnricher:
    def lookup_clauses_by_concept(self, fact_type):
        return []
standard_enricher_mod.StandardEnricher = StandardEnricher
sys.modules['src.compliance.standard_enricher'] = standard_enricher_mod

# Load modules directly from source files.
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
FactQueryAPI = fact_api_mod.FactQueryAPI
AI_GENERATED_PROVENANCE = models.AI_GENERATED_PROVENANCE
FactStatus = models.FactStatus


class FakeRows(list):
    def fetchall(self):
        return self
    def fetchone(self):
        return self[0] if self else None


class FakeDB:
    def __init__(self):
        self.queries = []
    def execute(self, sql, params=()):
        self.queries.append((sql, params))
        if 'FROM facts' in sql and "status = 'CANDIDATE'" in sql:
            return FakeRows([
                {
                    'fact_id': 'cand1',
                    'project_id': 'proj1',
                    'fact_type': 'document.profile',
                    'subject_kind': 'query',
                    'subject_id': 'query_123',
                    'status': FactStatus.CANDIDATE.value,
                    'value_json': '"profile summary"',
                    'method_id': 'query_derivation_v1',
                }
            ])
        if 'FROM fact_inputs' in sql:
            return FakeRows([])
        return FakeRows([])


def test_candidate_facts_are_explicitly_non_governing():
    api = FactQueryAPI(FakeDB())
    result = api.get_candidate_facts('summarize document', project_id='proj1')

    assert result['has_candidate_data'] is True
    assert result['governs_answers'] is False
    assert result['supporting_only'] is True
    assert result['provenance_class'] == AI_GENERATED_PROVENANCE
    assert result['requires_trust_promotion'] is True
    assert result['facts'][0]['governs_answers'] is False
    assert result['facts'][0]['supporting_only'] is True
    assert result['facts'][0]['provenance_class'] == AI_GENERATED_PROVENANCE
    assert 'NOT ANSWER-GOVERNING' in result['formatted_context']


def test_orchestrator_answer_path_uses_explicit_provenance_sections_without_candidate_promotion():
    source = (Path(__file__).resolve().parents[2] / 'src/application/orchestrators/agent_orchestrator.py').read_text()
    start = source.index('def answer_question(')
    end = source.index('def _derive_candidate_facts_from_evidence(')
    answer_source = source[start:end]
    assert '## Trusted Facts' in answer_source
    assert '## Extracted Evidence' in answer_source
    assert '## Linked Support' in answer_source
    assert '## AI-Generated Synthesis' in answer_source
    assert '_derive_candidate_facts_from_evidence(' not in answer_source


def test_candidate_context_is_phrase_explicitly_ai_generated():
    api = FactQueryAPI(FakeDB())
    result = api.get_candidate_facts('summarize document', project_id='proj1')
    assert result['formatted_context'].startswith('[AI-GENERATED CANDIDATE SUPPORT')
