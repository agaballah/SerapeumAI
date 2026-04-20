#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path('/mnt/data/fullrepo')

checks = []


def check(name, ok, detail=''):
    checks.append((name, ok, detail))

models = (ROOT / 'src/domain/facts/models.py').read_text()
fact_api = (ROOT / 'src/application/api/fact_api.py').read_text()
coverage_gate = (ROOT / 'src/application/services/coverage_gate.py').read_text()
orchestrator = (ROOT / 'src/application/orchestrators/agent_orchestrator.py').read_text()
authority = (ROOT / 'src/domain/facts/authority_service.py').read_text()

# Packet A/B guardrails
check('trusted_states_include_validated', "FactStatus.VALIDATED.value" in models)
check('trusted_states_include_human_certified', "FactStatus.HUMAN_CERTIFIED.value" in models)
check('candidate_not_in_trusted_tuple', 'NON_GOVERNING_FACT_STATUSES = (FactStatus.CANDIDATE.value,)' in models)
check('ai_generated_provenance_defined', 'AI_GENERATED_PROVENANCE' in models and 'FactProvenanceClass.AI_GENERATED.value' in models)

# Packet B enforcement
check('fact_api_uses_trusted_status_constant', 'CERTIFIED_STATUSES = TRUSTED_FACT_STATUSES' in fact_api)
check('coverage_gate_uses_trusted_status_sql', 'TRUSTED_FACT_STATUSES_SQL' in coverage_gate)
check('authority_service_restricts_certification_to_trusted', 'if cert_type not in TRUSTED_FACT_STATUSES' in authority)
check('orchestrator_refuses_without_trusted_support', 'NO_TRUSTED_FACT_SUPPORT' in orchestrator)

# Packet C rejection lane
check('canonical_rejected_status_defined', 'CANONICAL_REJECTED_STATUS' in models)
check('legacy_refused_mapped_to_rejected', 'REFUSED' in models and 'return CANONICAL_REJECTED_STATUS if str(status).upper() == "REFUSED" else str(status)' in models)
check('fact_api_normalizes_rejection_status', 'normalize_rejection_status' in fact_api)

# Packet D candidate containment
check('candidate_support_labeled_ai_generated', 'AI-GENERATED CANDIDATE SUPPORT - visible for review; NOT ANSWER-GOVERNING' in fact_api)
check('candidate_support_marked_non_governing', '"governs_answers": False' in fact_api and '"supporting_only": True' in fact_api)
# Ensure main answer path itself doesn't invoke candidate derivation
try:
    start = orchestrator.index('def answer_question(')
    end = orchestrator.index('def _derive_candidate_facts_from_evidence(')
    answer_body = orchestrator[start:end]
    check('main_answer_path_no_candidate_fallback', '_derive_candidate_facts_from_evidence' not in answer_body)
except ValueError:
    check('main_answer_path_no_candidate_fallback', False, 'could not locate answer_question or candidate helper')

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"{name}: {'PASS' if ok else 'FAIL'}" + (f" - {detail}" if detail else ''))

if failed:
    print(f"\n{len(failed)} truth-spine contract check(s) failed.")
    sys.exit(1)

print('\nAll truth-spine contract checks passed.')
