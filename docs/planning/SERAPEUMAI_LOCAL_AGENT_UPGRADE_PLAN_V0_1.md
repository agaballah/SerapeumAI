# SerapeumAI Local Agent Upgrade Plan v0.1

Status: PARKED PLANNING BRANCH ONLY  
Branch: docs/local-ai-planning-v0-1  
Base authority: main at 16723b0970a81c181bb0df6801178c7032d49f21  
Implementation status: NO IMPLEMENTATION  
Source-code status: DO NOT EDIT SOURCE FOR THIS PLAN UNTIL RUNNING UPGRADE AND QUALITY UPGRADE ARE COMPLETE

---

## 1. Executive decision

The Agent Upgrade must not start as a free autonomous agent system. It must start as a deterministic, local-first, evidence-governed review system where the LLM is only an interpreter and narrator over facts, extracted evidence, and approved tool outputs.

The target is not a chatbot that can act. The target is an engineer-facing local review assistant that can:

1. read only from project-grounded evidence;
2. propose or validate only tightly controlled small facts;
3. keep deterministic extraction as the authority;
4. keep LLM synthesis non-governing unless converted into reviewable facts;
5. expose every answer with evidence lanes and trace;
6. block all write/execute behavior until a separate future gate.

This plan is parked now and must not interrupt the active upgrade sequence.

---

## 2. Mandatory upgrade sequence

The controlled sequence is fixed:

1. Finish the current Running Upgrade first.
2. Finish the Quality Upgrade second.
3. Start this Agent Upgrade third.

No Agent Upgrade implementation may begin while the Running Upgrade or Quality Upgrade is still active.

Reason: the agent layer depends on stable runtime behavior, stable extraction quality, fact governance, and human-review UX. Starting the agent layer before those foundations are stable risks building a powerful interface over unstable truth.

---

## 3. Main objective

Build a completely local AI-assisted engineering review system with zero tolerance for unsupported model claims.

The LLM must never be treated as a source of truth. It may only:

- summarize deterministic evidence;
- explain validated facts;
- compare retrieved facts;
- ask for missing evidence;
- propose candidate facts for review;
- classify low-risk facts only when deterministic anchors are complete;
- format results for engineers.

The LLM must not invent, infer beyond evidence, fill missing values, perform hidden calculations, or silently promote extracted fragments into trusted truth.

---

## 4. Current repo integration baseline

The current repository already has important foundations that this upgrade should preserve rather than replace.

### 4.1 Document Center / ingest baseline

The Documents Page currently exposes a Project Document Center, an Import Documents button, a Refresh button, and a Project Scope / Global Standards scope selector. Imports are routed through SmartImportWizard and submitted as IngestFileJob jobs, using project scope or GLOBAL scope depending on the selected context.

Planning implication: Auto-Ingest should not be a separate truth path. It should become a controlled scheduler/orchestrator over the same ingest/extract/build-facts pipeline, with visible status and no silent promotion.

### 4.2 Fact governance baseline

The facts model already separates statuses including CANDIDATE, VALIDATED, HUMAN_CERTIFIED, REJECTED, SUPERSEDED, and DRAFT. Trusted facts are currently limited to VALIDATED and HUMAN_CERTIFIED.

Planning implication: deterministic auto-validation must either map into VALIDATED only under strict rules, or introduce a distinct AUTO_VALIDATED status if the team decides VALIDATED should remain human-only. Until that decision is finalized, AUTO_VALIDATED must be treated as a planning concept, not an implemented status change.

### 4.3 Chat/orchestration baseline

The current AgentOrchestrator answer path already retrieves trusted facts, extracted evidence, linked support, and AI-generated support lanes. It also labels support-only answers separately when trusted facts are missing.

Planning implication: the Agent Upgrade should strengthen this lane model rather than bypass it. The agent must not answer directly from model memory. It must answer through the existing evidence/fact authority model.

---

## 5. Core doctrine

### 5.1 Facts-first doctrine

1. Deterministic extraction is evidence, not automatically truth.
2. Facts are atomic review units created from evidence anchors.
3. Trusted facts govern answers.
4. Extracted evidence supports answers only when clearly labeled as support-only.
5. AI synthesis is never governing truth by itself.
6. Retrieval/vector results are support, not authority.
7. Any answer without trusted facts must say it is support-only.
8. Any answer with missing required facts must disclose the gap.

### 5.2 Local-first doctrine

1. All core review, extraction, fact validation, and chat must work against local project data.
2. No cloud model dependency is allowed for the agent core.
3. No internet access for model downloads or provider setup without explicit user consent in a later Runtime Setup Wizard.
4. Runtime capability must be reported honestly: model loaded, model not loaded, context too small, memory pressure, or unsupported role.

### 5.3 Safety doctrine

1. The default agent mode is read-only.
2. Write/execute tools are forbidden in this upgrade.
3. The agent must not delete, rename, overwrite, convert, or export files.
4. The agent must not run shell commands.
5. The agent must not alter project data except through explicitly approved future fact-review actions.
6. The agent must not certify facts on behalf of the engineer except under a deterministic auto-validation policy approved in this plan.

---

## 6. Auto-Ingest integration concept

Auto-Ingest should become the entry point for controlled project intake, not an autonomous agent.

### 6.1 Proposed user-facing behavior

Add or repurpose an Auto-Ingest toggle/button with three visible modes:

1. Off
   - No background intake beyond manual import.

2. Watch and Queue
   - Detects new files in the selected project folder.
   - Queues files for ingest.
   - Does not extract or validate without user-configured policy.

3. Watch, Extract, and Propose Facts
   - Runs deterministic extractors.
   - Builds candidate facts.
   - Runs deterministic auto-validation only for allowed fact types.
   - Sends everything else to human review.

### 6.2 Auto-Ingest pipeline

Auto-Ingest should follow this route:

1. Detect file event.
2. Register file version.
3. Compute checksum.
4. Run deterministic extractor.
5. Normalize extracted records.
6. Create evidence anchors.
7. Build candidate facts.
8. Apply deterministic auto-validation policy.
9. Update review queue.
10. Emit safe trace.
11. Refresh dashboard and Facts page.

### 6.3 Auto-Ingest forbidden behavior

Auto-Ingest must not:

- delete old files;
- overwrite source files;
- convert files destructively;
- silently certify broad engineering conclusions;
- silently treat AI summaries as facts;
- run external tools without explicit tool policy;
- run while no active project is selected;
- mix GLOBAL standards scope with project truth scope.

---

## 7. Deterministic auto-validation policy

The auto-validation policy is the core of the upgrade. It must be conservative enough for safety-critical engineering use.

### 7.1 Allowed auto-validation class

A fact may be auto-validated only if all conditions are true:

1. The fact is small and atomic.
2. The value is directly visible in deterministic evidence.
3. The extractor method is deterministic or rule-based.
4. The evidence anchor is exact enough to re-open the source location.
5. The value does not require interpretation, calculation, design judgment, legal judgment, or engineering judgment.
6. The same value is confirmed by one source with very high evidence quality, or by two independent extracted anchors if the fact is important.
7. No conflicting value exists in a newer or higher-authority source.
8. The fact type is explicitly listed in the allowed fact list.

### 7.2 Initial allowed fact list

Allowed for possible deterministic auto-validation:

- project name;
- project number;
- document number;
- document title;
- revision code;
- issue date;
- discipline;
- drawing scale when explicitly printed;
- sheet/page count;
- project owner name when printed in title block or cover sheet;
- consultant/designer name when printed in title block or cover sheet;
- contractor name when printed in title block or cover sheet;
- building name or plot number when explicitly printed;
- number of floors only when explicitly stated as text or title-block metadata;
- drawing status/stage when explicitly printed;
- file type, file size, checksum, imported date;
- schedule activity ID and name from deterministic XER parser;
- IFC entity GUID/type/name from deterministic IFC parser;
- Excel register row document number/title/status when parsed from configured register schema.

### 7.3 Blocked fact list

Always blocked from auto-validation:

- code compliance;
- fire/life-safety compliance;
- structural adequacy;
- MEP design adequacy;
- constructability conclusions;
- quantities requiring geometric interpretation;
- BOQ pricing conclusions;
- schedule delay responsibility;
- critical path judgment unless deterministic CPM/float authority is explicitly proven;
- contractual entitlement;
- legal interpretation;
- safety approval;
- design approval;
- clash severity judgment;
- DGN/CAD semantic interpretation unless converted and parsed through a verified deterministic extractor;
- OCR-only ambiguous values;
- low-confidence table extraction;
- any fact extracted only from AI summary;
- any fact requiring cross-document inference unless an explicit deterministic reconciliation rule exists.

### 7.4 Auto-validation output states

Recommended states:

- CANDIDATE: extracted but not trusted.
- AUTO_VALIDATION_ELIGIBLE: passes deterministic checks but not yet promoted.
- AUTO_VALIDATED: promoted by deterministic policy, if the team approves adding this status.
- HUMAN_CERTIFIED: explicitly certified by engineer.
- REJECTED: rejected by engineer or deterministic conflict rule.
- SUPERSEDED: replaced by newer source/revision.

If no new status is added, AUTO_VALIDATED should be represented as VALIDATED with method_id and audit metadata proving deterministic promotion. This decision must be made during implementation design, not now.

---

## 8. Evidence anchor schema

Every candidate or auto-validated fact must carry a replayable evidence anchor.

Minimum anchor fields:

- project_id;
- file_version_id;
- source_path;
- file_sha256;
- extractor_id;
- extractor_version;
- method_id;
- record_type;
- page_index or sheet_name/row/column or entity_guid;
- raw_text_excerpt or raw_value;
- normalized_value;
- bbox or cell/range/entity reference when available;
- confidence score;
- confidence reason;
- status;
- created_at;
- validated_at;
- validated_by_method;
- conflict_group_id when applicable;
- supersedes_fact_id when applicable.

Anchor rule: if the user cannot open the source and verify the exact evidence location, the fact must not be auto-validated.

---

## 9. Tool registry plan

The tool registry must be deterministic, typed, local, and safety-gated.

### 9.1 Registry fields

Each tool must define:

- tool_id;
- display_name;
- category;
- input_schema;
- output_schema;
- read_only flag;
- writes_project_data flag;
- writes_files flag;
- external_process flag;
- requires_user_approval flag;
- deterministic flag;
- evidence_anchor_output flag;
- timeout_seconds;
- allowed_file_types;
- allowed_project_scope;
- safety_notes;
- tests_required.

### 9.2 Initial read-only tools

Initial allowed tools should be read-only only:

- file inventory tool;
- checksum tool;
- PDF metadata/text/vector extraction tool;
- OCR extraction tool with low-confidence labeling;
- DXF entity inventory tool;
- IFC entity inventory/query tool where dependency exists;
- XER parser/query tool;
- Excel register parser/query tool;
- facts query tool;
- evidence anchor viewer;
- deterministic calculator/unit converter.

### 9.3 Blocked tools in this upgrade

Blocked until future write/execute gate:

- shell command execution;
- file deletion/rename/move;
- source file conversion;
- document authoring/export;
- email sending;
- external upload;
- issue/PR creation from inside the app;
- automated approvals;
- autonomous loops that run tools repeatedly without bounded plan and user visibility.

---

## 10. Skill registry plan

A skill is a bounded workflow built from tools, prompts, and validation rules.

### 10.1 Skill registry fields

Each skill must define:

- skill_id;
- objective;
- allowed_tools;
- required_fact_types;
- required_evidence_types;
- blocked_fact_types;
- max_steps;
- max_runtime_seconds;
- model_role_required;
- deterministic_prechecks;
- output_schema;
- failure_modes;
- user-visible trace requirement;
- acceptance tests.

### 10.2 Initial skills

Initial read-only skills:

1. Project Profile Builder
   - Builds candidate small facts such as owner, consultant, project name, document stage.

2. Drawing Register Auditor
   - Checks document numbers, titles, revisions, duplicates, missing pairs, latest/superseded logic.

3. Evidence-Based Q&A
   - Answers from trusted facts first and support-only extracted evidence second.

4. Fact Gap Finder
   - Reports missing trusted facts required to answer a question.

5. Conflict Detector
   - Identifies conflicting values for the same fact type and subject.

6. Source Trace Explainer
   - Explains where a fact came from and why it is trusted, candidate, rejected, or blocked.

7. Auto-Ingest Review Queue Builder
   - Converts newly ingested deterministic evidence into candidate/review queues.

---

## 11. Safe trace design

Every agent action must produce a safe trace that is visible to the engineer and persisted if approved by the implementation phase.

Trace fields:

- run_id;
- project_id;
- active_project_id_at_start;
- user_request;
- selected_skill;
- selected_tools;
- input_files;
- evidence_records_read;
- facts_read;
- facts_created_as_candidate;
- facts_auto_validated;
- facts_blocked;
- conflicts_detected;
- model_used;
- context_length;
- token budget estimate;
- safety gate result;
- final answer authority;
- elapsed time;
- errors;
- cancellation state.

Safe trace must not expose secrets, private keys, passwords, or full confidential payloads beyond evidence snippets already in the project workspace.

---

## 12. LLM role in analysis tasks

The analysis model should not be allowed to create truth. Its safe roles are:

- classify user intent;
- map a question to required fact types;
- explain deterministic facts in plain engineering language;
- summarize extracted evidence with citations;
- identify ambiguity and missing evidence;
- propose candidate facts, never trusted facts, unless deterministic auto-validation rules independently pass;
- produce a user-facing answer with visible authority labels.

The analysis model must not:

- use its training knowledge as project evidence;
- generate missing project values;
- calculate quantities without deterministic tools;
- override deterministic parser output;
- hide uncertainty;
- cite non-existent facts;
- infer approvals or compliance.

---

## 13. Context and concurrency lessons from local benchmark

The local Qwen3.5-9B work showed the model can produce valid JSON under controlled load when context length is correctly loaded at 8192, and that concurrency depends heavily on context budget and prompt size.

Planning implications:

1. Agent prompts must be small and schema-bounded.
2. The app must preflight context length before submitting multi-agent jobs.
3. The app must queue jobs by role instead of assuming unlimited parallelism.
4. Reviewer/final-report jobs should be queued or isolated from operational jobs.
5. C3 concurrency is not safe until prompt budget, final report policy validation, and local context preflight are deterministic.
6. A local model should be treated as a constrained runtime component, not as a cloud-scale agent backend.

Recommended initial runtime policy:

- default: single active analysis job;
- safe mode: max 2 concurrent lightweight jobs only after context preflight;
- reviewer/final-report lane: queue, not parallel flood;
- C3+ concurrency: experimental only, blocked until strict policy/context gate passes repeatedly.

---

## 14. Acceptance gates

### Gate 0: Prerequisite sequence gate

Pass criteria:

- Running Upgrade is finished and merged/parked as appropriate.
- Quality Upgrade is finished and merged/parked as appropriate.
- This plan is reconciled against current main before implementation.

### Gate 1: Repo truth gate

Pass criteria:

- Confirm current ingest pipeline.
- Confirm current extractor registry.
- Confirm current fact schema and statuses.
- Confirm current chat answer lane model.
- Confirm current runtime manager behavior.
- Confirm no hidden write/execute agent loop exists.

### Gate 2: Doctrine tests gate

Pass criteria:

- Candidate facts do not govern answers.
- Trusted facts govern answers.
- Support-only answers are visibly labeled.
- AI output is non-governing.
- Missing facts produce gap disclosure.
- Rejected facts are excluded.
- Project isolation holds.

### Gate 3: Auto-validation tests gate

Pass criteria:

- Allowed small fact is auto-validation eligible only with exact evidence anchor.
- Blocked fact is never auto-validated.
- OCR ambiguity blocks auto-validation.
- Conflicting values block auto-validation.
- Newer revision supersedes older fact by deterministic rule only.
- Auto-validation trace is visible and replayable.

### Gate 4: Tool registry tests gate

Pass criteria:

- Every tool has schema, safety class, timeout, and read/write flag.
- Write tools are unavailable in this upgrade.
- Tool output has evidence anchors where applicable.
- Tool failures are visible and do not produce facts.

### Gate 5: Skill registry tests gate

Pass criteria:

- Every skill is bounded by max steps and allowed tools.
- No skill can call blocked tools.
- No skill can promote facts outside policy.
- Every skill returns a safe trace.

### Gate 6: Runtime/concurrency gate

Pass criteria:

- Context preflight prevents LM Studio HTTP context overflow.
- C1 and C2 pass strict JSON and policy gates.
- C3 is blocked or experimental unless repeated clean runs pass.
- Final Report policy validator blocks write/execute language in visible output.

### Gate 7: UX gate

Pass criteria:

- Engineer sees answer first.
- Evidence is behind Show Evidence.
- Auto-validated facts are visibly separate from human-certified facts unless final policy says otherwise.
- Review queue is human-readable.
- User can inspect why a fact was allowed, blocked, or rejected.

---

## 15. Forbidden behavior

The Agent Upgrade must not introduce:

- autonomous write/execute agents;
- shell command execution;
- hidden file operations;
- hidden model memory answers;
- cloud dependency for local review;
- automatic design/compliance approval;
- unbounded loops;
- prompt-only validation;
- LLM arithmetic as authority;
- broad fact auto-certification;
- silent fact promotion;
- cross-project evidence leakage;
- support-only answers presented as trusted truth;
- AI summaries stored as trusted facts;
- C3/C4 concurrency without context and policy gates.

---

## 16. Implementation waves when this plan is later activated

### Wave A: Inspection and contracts only

- Re-inspect current repo after Running Upgrade and Quality Upgrade.
- Lock doctrine tests.
- Lock allowed/blocked fact lists.
- Lock evidence anchor schema.
- No UI feature implementation yet.

### Wave B: Auto-Ingest controller planning-to-code

- Wire Auto-Ingest as a controller over existing ingest pipeline.
- Add visible modes.
- Add queue status.
- No auto-validation yet unless Gate 3 tests exist.

### Wave C: Deterministic auto-validation engine

- Implement allowed fact policy.
- Implement blocked fact policy.
- Implement evidence anchor replay checks.
- Add conflict/superseded handling.

### Wave D: Tool registry

- Register read-only tools only.
- Add schemas and safety classes.
- Add safe execution harness with timeout and cancellation.

### Wave E: Skill registry

- Add bounded skills.
- Add safe trace.
- Add UI presentation and review queue integration.

### Wave F: Local runtime gate

- Add context preflight.
- Add queue policy.
- Add role-based concurrency limits.
- Block C3+ unless proven safe.

### Wave G: Release hardening

- Full source tests.
- Packaged smoke.
- Second-machine validation.
- No release claim until all gates pass.

---

## 17. Parked status

This branch is intentionally parked. It exists to preserve the planning doctrine and prevent the Agent Upgrade from contaminating the active Running Upgrade or Quality Upgrade.

The next action is not implementation. The next action is to finish the current Running Upgrade, then finish the Quality Upgrade, then return to this branch and reconcile the plan against the final main branch state.
