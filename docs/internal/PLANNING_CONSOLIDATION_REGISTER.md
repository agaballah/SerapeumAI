# Planning Consolidation Register

## Purpose

This register captures planning decisions preserved from stale planning branches
before those branches are retired. It keeps the useful direction without merging
the old branch structures wholesale.

`main` remains the repository authority. This document is not implementation,
does not approve implementation, and does not describe shipped behavior.

## Preserved Ideas From `docs/local-ai-planning-v0-1`

- The agent layer must start read-only, deterministic, local-first, and
  evidence-governed.
- Auto-Ingest must be a controlled scheduler over the existing
  ingest/extract/build-facts pipeline, not a new truth path.
- Auto-validation must be deterministic and policy-based.
- Allowed and blocked fact classes must be explicit before any
  auto-certification policy exists.
- Evidence anchors must be replayable so a user can return to the exact source
  location and verify the value.
- Tool registry and skill registry designs must be typed, bounded, and
  safety-gated.
- Tool and skill runs need safe trace fields that show procedure without
  exposing private reasoning.
- Runtime/context concurrency should queue jobs, preflight context, and keep
  C3+ concurrency experimental until repeatedly proven.

## Preserved Ideas From `docs/total-quality-upgrade-v3-3`

- Quality work should start with a DOC-first sequence before deeper
  implementation packets.
- A quality contract and extension matrix should be an early
  implementation-quality packet.
- Domain-specific acceptance criteria are needed for PDF, OCR, drawings,
  IFC/BIM, P6/XER, Office/registers, Document Center, facts, chat, and agent
  workflows.
- Gold fixtures need a legality policy and fixture metadata requirements.
- New dependencies, copied assets, models, fixtures, binaries, and license
  obligations need an admission checklist before entering the repository.
- The release gate must block overclaimed docs, unreviewed dependencies, unsafe
  agents, packaging drift, and unproven Windows behavior.
- Lab boundaries are required for MCP/external connectors, review swarms,
  QuantBench, and local 3D review.

## Future Packet Mapping

| Packet | Source branch | Scope | Implementation status |
|---|---|---|---|
| Auto-Ingest policy | `docs/local-ai-planning-v0-1` | Define controlled Auto-Ingest modes over the existing ingest/extract/build-facts pipeline. | Not implemented here |
| Deterministic auto-validation policy | `docs/local-ai-planning-v0-1` | Define allowed and blocked fact classes plus deterministic promotion rules. | Not implemented here |
| Evidence anchor schema | `docs/local-ai-planning-v0-1` | Define replayable source anchors for candidate and validated facts. | Not implemented here |
| Safe trace schema | `docs/local-ai-planning-v0-1` | Define procedural trace fields for tool and skill runs. | Not implemented here |
| Total Quality packet sequence | `docs/total-quality-upgrade-v3-3` | Preserve the DOC-first and quality-packet ordering for future work. | Not implemented here |
| Domain acceptance criteria | `docs/total-quality-upgrade-v3-3` | Preserve quality pass criteria by domain and workflow surface. | Not implemented here |
| Gold fixture policy | `docs/total-quality-upgrade-v3-3` | Define fixture legality, metadata, and expected-output rules. | Not implemented here |
| Dependency/license checklist | `docs/total-quality-upgrade-v3-3` | Define admission review fields for dependencies, assets, fixtures, and binaries. | Not implemented here |
| Release gate policy | `docs/total-quality-upgrade-v3-3` | Define release blockers for docs, dependencies, agents, packaging, and Windows proof. | Not implemented here |
| Lab boundary policy | `docs/total-quality-upgrade-v3-3` | Define disabled-by-default boundaries for MCP, external connectors, review swarms, QuantBench, and local 3D review. | Not implemented here |

## Branch Retirement Rule

Delete `origin/docs/local-ai-planning-v0-1` only after Auto-Ingest,
auto-validation, evidence-anchor, and safe-trace ideas are captured or mapped to
issues.

Delete `origin/docs/total-quality-upgrade-v3-3` only after packet sequence,
acceptance criteria, fixture policy, dependency checklist, and release gate
ideas are captured or mapped to issues.

This file is intended to satisfy the captured-in-main requirement for
high-level planning. Individual implementation packets still need their own
issues, branches, scopes, proofs, and review.
