# 07 — Documentation Governance

## Purpose

Prevent documentation drift during the Total Quality Upgrade.

## Core rule

Public documentation describes only current proven behavior. Internal documentation may describe plans, architecture, risks, and future packets.

## Required documentation impact field

Every packet must declare one of:

- no documentation impact,
- internal docs only,
- public docs,
- changelog,
- limitations,
- system requirements,
- troubleshooting,
- privacy/security,
- license/notice.

Every packet must also declare whether it changes user-visible behavior.

## Public documentation rules

- README stays short and user-facing.
- Roadmap separates current, next, later, and research.
- Limitations must be updated when known weaknesses change.
- Privacy must state any external communication accurately.
- System requirements must reflect actual runtime needs.
- Troubleshooting must cover common user-fixable failures.
- Changelog records user-visible behavior changes.

## Internal documentation rules

Internal docs may track architecture decisions, packet sequencing, risk analysis, tool policies, fixture policy, and lab concepts.

## Forbidden public claims

Avoid language that implies:

- guaranteed compliance,
- autonomous agents,
- Revit replacement,
- design authoring,
- automatic approval or submission,
- cloud dependency where local-first is intended,
- features that are only planned or experimental.

## Documentation reconciliation

Before any release, DOC-FINAL must verify that README, roadmap, license, limitations, privacy, system requirements, troubleshooting, changelog, GitHub metadata, screenshots, and release notes match proven behavior.
