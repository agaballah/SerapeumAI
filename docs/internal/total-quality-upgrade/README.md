# Total Quality Upgrade Planning Dossier

Status: planned / not active  
Audience: maintainers and release planning  
Scope: documentation-governed quality program for a future SerapeumAI major upgrade

This folder is an internal planning dossier for the future **Total Quality Upgrade v3.3**. It is not user documentation and must not be treated as a claim that the described behavior is already shipped.

## Control rule

Public documentation describes only current proven behavior. Internal planning documents may describe future work, architecture, risks, and packet sequencing.

## Documents

1. `00_PROGRAM_CHARTER.md` — upgrade purpose, principles, and success definition.
2. `01_CURRENT_REPO_TRUTH.md` — repo-truth freeze template to complete before implementation.
3. `02_SCOPE_AND_NON_SCOPE.md` — what is in and out of scope.
4. `03_BACKLOG.md` — full DOC/TQ packet backlog.
5. `04_PACKET_SEQUENCE.md` — execution order and packet contract.
6. `05_ACCEPTANCE_CRITERIA.md` — pass criteria by quality area.
7. `06_TEST_AND_PROOF_STRATEGY.md` — how packets are proven.
8. `07_DOCUMENTATION_GOVERNANCE.md` — how docs stay aligned during the upgrade.
9. `08_RISK_REGISTER.md` — risk categories and initial risks.
10. `09_DEPENDENCY_AND_LICENSE_REVIEW.md` — dependency and license admission rules.
11. `10_DATA_FIXTURE_POLICY.md` — gold fixture legality and quality rules.
12. `11_AGENTIC_WORKFLOW_POLICY.md` — safe tool/skill/agentic workflow policy.
13. `12_LOCAL_3D_REVIEW_LAB_POLICY.md` — local-only spatial review lab boundaries.
14. `13_RELEASE_GATE.md` — final release barrier.
15. `14_GITHUB_ROLLOUT_PLAN.md` — GitHub milestone, issue, and public messaging plan.

## Current execution status

The upgrade is **planned, not active**. The first future executable packet is `DOC-01 Documentation Inventory and Truth Audit`. The first quality implementation packet is `TQ-01 Quality Contract + Extension Matrix`.

## Non-negotiables

- No packaging changes without explicit approval.
- No dependency upgrades without explicit approval.
- No public claims beyond proven behavior.
- No uncontrolled autonomous agents.
- No arbitrary MCP execution in the baseline.
- No LLM calculations.
- No memory as certified truth.
- No AI/VLM output as deterministic evidence.
- No design authoring or Revit replacement language.
