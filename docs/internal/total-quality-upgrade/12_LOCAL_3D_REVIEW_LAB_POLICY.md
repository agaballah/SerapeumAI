# 12 — Local 3D Review Lab Policy

## Purpose

Define the boundary for any future local 3D/spatial review concept inspired by browser-based building editors.

## Decision

Do not adopt Pascal Editor or any hosted browser editor as a core dependency. Adopt only local-safe concepts if they prove useful.

## Allowed concepts

- Local browser-style 3D review.
- Level, zone, wall, slab, and opening hierarchy.
- Spatial scene JSON.
- Local autosave concept.
- Undo/redo concept.
- Optional local viewer research.
- Dummy-data-only prototypes.
- Candidate evidence mapping.

## Forbidden behavior

- No public hosted demo with project files.
- No internet-required runtime.
- No cloud-hosted editor.
- No packaging dependency without approval.
- No certified facts from scene edits.
- No design-authoring claim.
- No Revit replacement language.
- No automatic model write-back.

## Product boundary

3D review may become visual support, review annotation, candidate evidence, or spatial context. It must not become certified BIM truth, official design authoring, or automatic project model authority.

## Candidate future packets

- TQ-20 Local 3D Review Concepts Lab.
- TQ-21 SerapeumAI-Owned Spatial Scene Schema.
- TQ-22 Optional Local Viewer Decision.

## Acceptance for any future continuation

Proceed only if the approach is 100 percent local for project data, Windows-safe, packaging-safe, optional, disableable, and truth-safe.
