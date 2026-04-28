# 08 — Risk Register

## Purpose

Track the main risks for the Total Quality Upgrade before implementation begins.

## Risk categories

| Category | Examples | Default posture |
|---|---|---|
| Architecture risk | truth weakening, source-lane mixing, schema drift | protect truth spine |
| Documentation risk | public overclaiming, outdated README, vague privacy | docs must match behavior |
| License risk | copied assets, unclear fixtures, incompatible dependency | audit before adoption |
| Packaging risk | OCR engines, WebGPU, native binaries, model runtimes | explicit approval required |
| Windows risk | paths, GPU drivers, WebView, local runtimes | terminal proof required |
| Agent risk | unsafe tools, memory leakage, uncontrolled swarms | bounded tools only |
| Data risk | confidential fixtures, project data in screenshots | synthetic/redistributable only |
| Rollback risk | schema changes, broad UI rewrites, persistent state changes | small reviewable diffs |

## Initial risks

### Public truth risk

The public repo may currently contain outdated README, roadmap, license, or feature claims. DOC-0 must address this before quality implementation begins.

### Scope explosion risk

The upgrade touches extraction, evidence, chat, tools, docs, fixtures, and labs. Packets must remain bounded.

### Dependency drift risk

OCR, IFC, PDF repair, WebGPU, and agent frameworks can introduce packaging and license risks. No dependency enters without review.

### Truth dilution risk

OCR, VLM, AI summaries, memory, retrieval, and agent outputs must not silently govern certified answers.

### Agent hype risk

Tool-using workflows are allowed; uncontrolled swarms and autonomous actions are not baseline features.

### 3D review boundary risk

Local spatial review concepts are allowed only as support. They must not become design authoring or certified BIM truth.

## Risk review rule

Every packet must update or confirm this register when it introduces new architecture, dependency, privacy, packaging, or documentation risk.
