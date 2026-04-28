# 06 — Test and Proof Strategy

## Purpose

Define how Total Quality Upgrade packets will be verified. Review of source text is not enough for runtime behavior; each packet must include appropriate tests, evidence, and documentation-impact review.

## Proof layers

1. Contract checks for schemas, matrices, and documentation structure.
2. Unit tests for isolated logic.
3. Fixture tests for extraction and evidence output.
4. Integration tests for pipeline, facts, and chat behavior.
5. Windows runtime proof where behavior depends on the desktop app or local runtime.
6. Documentation reconciliation for user-visible behavior.

## Required packet proof

Each packet should report:

- commands or checks used,
- fixtures or inputs used,
- expected result,
- actual result,
- changed files,
- documentation impact,
- risk impact,
- rollback notes.

## Test areas

### Quality contract

- extension matrix loads,
- required extensions exist,
- required fields exist,
- unsupported behavior is explicit.

### Extraction quality

- native PDF, scanned PDF, mixed PDF, and drawing PDF fixtures,
- Office/register fixtures,
- IFC fixture,
- XER fixture,
- image/drawing fixture.

### Document Center

- four-tab structure,
- separation between deterministic extraction and AI/VLM support,
- metadata visibility,
- honest empty states.

### Chat quality

- positive trusted-fact answer,
- refusal when trusted facts are missing,
- candidate fact exclusion,
- active project scope,
- no cross-project leakage.

### Tool and agentic workflow

- schema validation,
- unauthorized tool rejection,
- deterministic calculator behavior,
- audit record creation,
- safe procedural trace,
- timeout and stop behavior.

### Documentation

- public docs avoid future features as shipped claims,
- roadmap status categories are clear,
- limitations are current,
- privacy language is accurate,
- changelog records user-visible changes.

## Exit rule

A packet is blocked if required proof is missing, fixtures are unavailable, behavior is only visually assumed, or documentation impact remains unresolved.
