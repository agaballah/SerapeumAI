# 00 — Program Charter

## Program name

**Total Quality Upgrade v3.3 — Documentation-Governed Quality Program**

## Status

Planned / not active.

This document is an internal planning artifact. It does not describe shipped behavior unless explicitly stated.

## Purpose

The Total Quality Upgrade exists to improve the quality of everything the user receives from SerapeumAI:

- extension support clarity,
- extraction quality,
- evidence quality,
- metadata quality,
- OCR and drawing review quality,
- IFC/BIM and P6/XER truth quality,
- analysis quality,
- fact quality,
- chat quality,
- safe tool-using workflow quality,
- test fixture and regression quality,
- documentation truth.

## Product boundary

SerapeumAI remains a desktop-first, Windows-baseline, local-first AECO review workspace with an evidence and truth spine. It is not a generic chatbot, not a cloud-required platform, not a design-authoring product, and not an autonomous action system.

## Primary principle

Improve usefulness without weakening truth, and never let documentation claim more than the app can prove.

## Operating principle

Native and deterministic extraction is the baseline. OCR is a support lane. VLM and AI output are interpretation/support lanes. Certified facts govern answers. Retrieval supports answers but does not silently become truth. Memory is context, not evidence. Calculations are deterministic tools, not LLM guesses. Agentic workflows are bounded, audited, and policy-controlled.

## Success definition

The upgrade succeeds only when:

1. every supported extension has a declared quality contract,
2. every output has a source lane,
3. every finding can point to evidence,
4. every fact has lineage and state semantics,
5. chat answers from trusted scope or refuses honestly,
6. deterministic tools handle calculations,
7. agentic actions are controlled by registry and policy gates,
8. public docs match mounted and proven behavior,
9. gold fixtures prevent quality regression,
10. final release gates pass without overclaiming.

## Program owner model

- Application owner makes final product and release decisions.
- Architecture/release copilot scopes work, protects doctrine, and defines packets.
- Execution agents perform bounded implementation only.
- Terminal proof and reviewable diffs remain mandatory.

## First future executable packet

`DOC-01 Documentation Inventory and Truth Audit`

## First future quality implementation packet

`TQ-01 Quality Contract + Extension Matrix`
