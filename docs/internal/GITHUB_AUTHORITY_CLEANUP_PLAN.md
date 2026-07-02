# GitHub Authority Cleanup Plan

Task class: documentation task / repository authority cleanup plan.

Status: planning note only. This document does not edit source code, close issues, delete branches, merge branches, or approve implementation.

## Purpose

Consolidate the current branch and issue situation before more post-publish implementation continues.

The goal is to restore a simple working structure:

- `main` is authority.
- One issue defines one bounded packet.
- One branch implements one issue.
- One PR reviews one branch.
- Branches are deleted after merge.
- Stale planning branches are mined for useful decisions, not merged wholesale.

## Current Branch Inventory

| Branch | Classification | Current interpretation | Recommended action |
|---|---|---|---|
| `main` | active authority | Long-lived repo authority. Remote `origin/main` remains the shared baseline. | Keep as the only durable authority branch. |
| `repair-r2-baseline-audit-note` | cleanup PR | Documentation-only cleanup branch for the malformed/truncated R2 baseline audit note. | Review, merge if accepted, then delete branch. |
| `r3b-runtime-wizard-read-model-presenter` | empty/stale branch | Remote branch currently appears identical to `origin/main`; intended name maps to issue #151. | Keep only if #151 work starts there; otherwise delete after confirming no unique work exists. |
| `docs/local-ai-planning-v0-1` | stale planning branch | Planning branch for local AI/runtime direction. | Mine useful decisions into authoritative docs or issues; do not merge wholesale. |
| `docs/total-quality-upgrade-v3-3` | stale planning branch | Broad quality/upgrade planning branch. | Mine useful decisions into authoritative docs or issues; do not merge wholesale. |
| `runtime-provider-tooling-audit` | local candidate implementation branch | Local branch containing a candidate runtime/provider discovery baseline slice. | Treat as an R1-A candidate under #136 only after issue scope is confirmed; do not use for #151. |

## Open Issue Mapping

| Issue | Classification | Working interpretation | Recommended action |
|---|---|---|---|
| #138 Post-publish Master Plan - Runtime, Quality, Agentic Upgrade Sequence | master plan | Planning authority for upgrade sequencing and branch cleanup. | Keep as the source issue until the plan is fully captured in `main`; close or supersede stale planning references afterward. |
| #136 Future Upgrade - Runtime Setup Wizard hardware benchmark and model recommendation | implementation umbrella | Natural home for runtime/provider/model recommendation packets. | Split into small packets; treat `runtime-provider-tooling-audit` as an R1-A candidate only if the owner approves that packet boundary. |
| #151 R3-B - Runtime Wizard read-model presenter | narrow implementation packet | Should remain focused on read-model/presenter behavior for the Runtime Wizard. | Keep separate and narrow; do not mix provider registry, model catalog, or recommendation engine work into this branch. |
| #24 Master backlog: post-publish upgrades and loose ends register | old master backlog | Broad backlog issue predating the current post-publish plan. | Close or supersede after useful content is captured into #138 or newer packet issues. |

## Recommended Cleanup Actions

1. Merge or close `repair-r2-baseline-audit-note`.

   If the documentation fix is accepted, merge the PR and delete the branch. If it is superseded, close it explicitly so it no longer looks like active runtime work.

2. Mine stale planning branches, but do not merge them wholesale.

   Use `docs/local-ai-planning-v0-1` and `docs/total-quality-upgrade-v3-3` as source material only. Pull forward specific decisions into `main` or into bounded packet issues.

3. Close or supersede stale issues after content is captured.

   #24 should not remain a competing authority once #138 and the post-publish plan have captured the future direction.

4. Treat `runtime-provider-tooling-audit` as an R1-A candidate under #136.

   The branch is too broad for #151. It should become a first runtime/provider baseline packet only if #136 is explicitly split into a bounded issue such as:

   ```text
   R1-A - Runtime provider discovery baseline
   ```

5. Keep #151 separate and narrow.

   #151 should focus on Runtime Wizard read-model presenter behavior and should not absorb provider registry, model role manifest, recommendation engine, or embedded GGUF implementation work.

## Moving-Forward Rule

Future post-publish implementation should follow this rule:

```text
main is authority.
One issue per packet.
One branch per issue.
One PR per branch.
Delete branch after merge.
No stale planning branch merges.
```

## Branch-to-Issue Direction

| Branch | Issue direction |
|---|---|
| `repair-r2-baseline-audit-note` | Cleanup documentation PR, not a runtime issue. |
| `r3b-runtime-wizard-read-model-presenter` | #151 only. |
| `runtime-provider-tooling-audit` | Candidate #136 R1-A packet only. |
| `docs/local-ai-planning-v0-1` | Mine into #138/#136, then retire. |
| `docs/total-quality-upgrade-v3-3` | Mine into #138, then retire. |

## Stop Conditions Before More Runtime Implementation

Do not continue runtime/provider implementation until:

- the owner confirms whether `runtime-provider-tooling-audit` should become #136 R1-A;
- #151 is protected as a separate narrow presenter branch;
- stale planning branches are no longer treated as merge candidates;
- stale backlog issues are either closed, superseded, or explicitly mapped to new packet issues;
- local Python test availability is resolved or PR language clearly states that Python validation is locally blocked.
