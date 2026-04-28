# 13 — Release Gate

## Purpose

Define the final barrier before any Total Quality Upgrade release is considered.

## Release rule

Release is binary: PASS or FAIL. There is no release-grade partial acceptance.

## Required gates

### Code and behavior

- All active upgrade packets have PASS verdicts.
- No approved requirement remains deferred while being claimed as shipped.
- No truth-governance rule is weakened.
- No unsupported answer path is introduced.
- No cross-project leakage is present.
- No uncontrolled agentic behavior is present.
- No candidate facts, AI support, memory, or retrieval-only output silently govern certified answers.

### Tests and proof

- Required tests pass.
- Gold fixture checks pass where implemented.
- Chat positive/refusal checks pass where implemented.
- Tool and skill checks pass where implemented.
- Windows runtime proof is captured for runtime-sensitive behavior.
- Any packaging-sensitive behavior is proven separately before release.

### Documentation

- README matches current mounted/proven behavior.
- Roadmap separates current, planned, later, and research-only work.
- Limitations are current.
- Privacy language is accurate.
- System requirements match actual runtime needs.
- Troubleshooting covers known common failures.
- Changelog captures user-visible changes.
- Release notes are generated from proven behavior, not ambition.
- Screenshots are current or removed.

### License and dependencies

- License posture is clear and owner-approved.
- New dependencies are reviewed and approved.
- Third-party notices are present when required.
- Fixtures and assets are redistributable.
- Optional/lab dependencies are not presented as baseline requirements.

### Packaging

- Packaging files are untouched unless explicitly approved.
- If packaging is affected, packaged runtime parity must be proven.
- Windows portability remains intact.

## Failure conditions

The release gate fails if:

- docs overclaim,
- license is unclear,
- privacy language is vague,
- roadmap makes research look shipped,
- tests are missing for release-critical behavior,
- AI/VLM output can govern truth silently,
- memory can become hidden truth,
- tool calls bypass policy,
- packaging drift is unapproved,
- Windows runtime behavior is unproven.

## Exit condition

The upgrade may move to release only after DOC-FINAL and RELEASE-GATE both pass with evidence.
