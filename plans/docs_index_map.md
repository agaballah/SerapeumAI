# Documentation index and map (canonical vs archive)

This map is based on the repository documentation structure in [`docs/`](docs/SYSTEM_REQUIREMENTS.md:1) and root-level docs.

## Status legend

- **Canonical (user-facing)**: should be kept accurate and minimal.
- **Archive (internal / historical)**: may be valuable context but is not a contract for current behavior.
- **Working notes**: planning/spec artifacts; useful for product design but not user guidance.

## Recommended reading order (by goal)

### If you just want to run and use the app

1. [`README.md`](README.md:1)
2. [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1)
3. [`docs/SYSTEM_REQUIREMENTS.md`](docs/SYSTEM_REQUIREMENTS.md:1)
4. [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md:1)

### If you want the product boundaries and doc rules

1. [`PRODUCT_INTENT.md`](PRODUCT_INTENT.md:1)
2. [`README.md`](README.md:1)
3. [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1)

### If you are doing internal product / engineering alignment

1. [`build bible.txt`](build bible.txt:1)
2. [`user journey.txt`](user journey.txt:1)
3. Selected archive references, starting at [`docs/archive/DOCUMENTATION_INDEX.md`](docs/archive/DOCUMENTATION_INDEX.md:1)

## Canonical docs (user-facing)

| Document | Audience | What it covers | Notes |
|---|---|---|---|
| [`README.md`](README.md:1) | Users, evaluators | What the app is, what it can do, what it is not, how to run | Single run path: `python run.py` |
| [`PRODUCT_INTENT.md`](PRODUCT_INTENT.md:1) | Product + engineering + docs | Intent, in-scope/out-of-scope, red lines for documentation | Explicit doc contract |
| [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1) | Users | Visible UI concepts and flows: Projects, Documents, Chat, Compliance, Graph, Settings | Avoids internal details by design |
| [`docs/SYSTEM_REQUIREMENTS.md`](docs/SYSTEM_REQUIREMENTS.md:1) | Users, IT | Windows + Python + hardware guidance | Focus on practicality |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md:1) | Users, support | Common failures and fix checklist | User-first steps |

## Root-level working notes (product/spec artifacts)

These documents describe intended flows and a stricter truth-engine model than the current canonical user manual.

| Document | Status | What it covers | How to use it |
|---|---|---|---|
| [`build bible.txt`](build bible.txt:1) | Working notes | AECO truth engine vision: evidence, facts, validation, refusal protocol | Use for roadmap and architecture alignment |
| [`user journey.txt`](user journey.txt:1) | Working notes | BPMN-style user flow mapped to UI pages and job classes | Use as internal UX spec; not user manual |
| [`end-to-end user journey.txt`](end-to-end user journey.txt:1) | Working notes | Detailed swimlane narrative, includes strict protocol | Internal reference |
| [`full user journey  user flow.txt`](full user journey  user flow.txt:1) | Working notes | Day-1 contract framing: certified facts, coverage dashboard, validation queue | Internal reference |
| [`BPMN.txt`](BPMN.txt:1) | Working notes | Similar to end-to-end user journey content | Internal reference |

## Archive docs (`docs/archive/`)

Archive contains multiple sub-families:

1. **Phase delivery and status docs** (Phase 3, etc.)
2. **Developer handoff and quick references**
3. **Technical overview and architecture notes**
4. **Audits and inventories**

Suggested entry points:

- Index: [`docs/archive/DOCUMENTATION_INDEX.md`](docs/archive/DOCUMENTATION_INDEX.md:1)
- Snapshot-of-everything: [`docs/archive/combined_docs_snapshot.md`](docs/archive/combined_docs_snapshot.md:1)
- Technical narrative: [`docs/archive/TECHNICAL_OVERVIEW.md`](docs/archive/TECHNICAL_OVERVIEW.md:1)
- Prior audit context: [`DOCS_AUDIT.md`](DOCS_AUDIT.md:1)

## Proposed structural improvement (docs-only)

Create a single top-level documentation hub such as [`docs/INDEX.md`](docs/INDEX.md:1) to:

- Point users to canonical docs
- Clearly label archive as historical
- Provide role-based reading paths

This would reduce the chance that someone reads archive quick references (CLI, installers, LM Studio, etc.) as current truth.

