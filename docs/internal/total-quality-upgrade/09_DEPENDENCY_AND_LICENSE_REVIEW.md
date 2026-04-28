# 09 — Dependency and License Review

## Purpose

Control dependency, license, and asset risk during the Total Quality Upgrade.

## Admission rule

No new dependency, copied code, model, fixture, image, font, binary, or asset may enter the repository until it has a documented review.

## Required review fields

- name,
- purpose,
- source URL,
- license,
- commercial/distribution implications,
- Windows support,
- offline/local behavior,
- packaging impact,
- security posture,
- expected footprint,
- rollback plan,
- owner approval status.

## High-risk areas

- OCR engines and preprocessing tools,
- PDF repair/parsing libraries,
- IFC/BIM libraries,
- CAD/DGN conversion tools,
- model runtimes,
- agent frameworks,
- MCP/external connectors,
- WebGPU/WebView/3D viewer stacks,
- bundled fixtures or screenshots.

## License rules

- Do not change the project license without explicit owner approval.
- Do not add GPL/AGPL/copyleft-sensitive components without review.
- Do not include third-party files without license trace.
- Add notices only when required and proven.
- Keep public license language consistent with the repository license.

## Packaging rules

- Packaging files are sensitive and must not be touched unless explicitly approved.
- Native binaries and external runtimes require separate packaging risk review.
- Optional/lab dependencies must remain outside the baseline until approved.

## Local-first rule

Any dependency that requires internet, cloud services, hosted APIs, or external accounts must be treated as optional/lab only unless the owner explicitly changes the product posture.
