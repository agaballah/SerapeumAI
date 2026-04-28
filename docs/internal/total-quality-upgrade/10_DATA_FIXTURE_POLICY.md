# 10 — Data Fixture Policy

## Purpose

Define what test fixtures are allowed for the Total Quality Upgrade.

## Fixture principles

Gold fixtures must be:

- non-confidential,
- redistributable,
- small enough for repository use,
- documented,
- deterministic,
- legally safe,
- linked to expected outputs.

## Forbidden fixture sources

- client project documents,
- tender files from real projects,
- confidential drawings,
- proprietary standards,
- copyrighted documents without permission,
- personal data,
- screenshots containing private project data,
- model files with unclear license.

## Preferred fixture sources

- synthetic documents created for testing,
- owner-created dummy files,
- public-domain or permissively licensed samples,
- tiny hand-made files designed for one test purpose.

## Required fixture metadata

Each fixture should declare:

- fixture name,
- file type,
- purpose,
- source/author,
- license or ownership,
- expected output file,
- quality dimensions tested,
- limitations.

## Minimum fixture families

- native PDF,
- scanned PDF,
- vector drawing PDF,
- mixed PDF,
- Excel register,
- DOCX specification,
- PPTX deck,
- IFC model,
- XER schedule,
- image/drawing,
- optional local spatial scene JSON with dummy data only.

## Review rule

Fixtures are part of the product proof surface. They must not create legal, privacy, or confidentiality risk.
