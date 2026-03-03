# Documentation fix list (action-oriented, prioritized)

This is a docs-only fix list intended to reduce confusion between canonical docs and archive/spec content.

## Priority 1: Make canonical docs self-sufficient and unambiguous

1. Add a canonical documentation hub file: [`docs/INDEX.md`](docs/INDEX.md:1)
   - Link only the canonical set
   - Explicitly label [`docs/archive/`](docs/archive/DOCUMENTATION_INDEX.md:1) as historical/internal
   - Provide role-based reading order

2. Clarify the model setup story in canonical docs
   - Decide and document one truthful statement about models:
     - whether models are bundled vs manually downloaded
     - where models are expected (reference [`models/DOWNLOAD_INSTRUCTIONS.md`](models/DOWNLOAD_INSTRUCTIONS.md:1))
     - what the model selector is choosing
   - Update troubleshooting section 2 accordingly (see [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md:40))

3. Add a short, user-facing description of storage footprint and where data goes
   - Without internal module names
   - Focus on what gets cached, typical disk growth, and how to recover space
   - Place it in [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1) and/or [`docs/SYSTEM_REQUIREMENTS.md`](docs/SYSTEM_REQUIREMENTS.md:49)

## Priority 2: Reduce drift and contradictions from archive/spec documents

4. Add clear banners to the top of high-risk archive docs
   - Examples:
     - [`docs/archive/QUICK_REFERENCE.md`](docs/archive/QUICK_REFERENCE.md:1)
     - [`docs/archive/FAQ.md`](docs/archive/FAQ.md:1)
     - [`docs/archive/TECHNICAL_OVERVIEW.md`](docs/archive/TECHNICAL_OVERVIEW.md:1)
   - Banner text should state:
     - archived and may be outdated
     - canonical docs are the user contract
     - do not follow setup steps here unless you are doing development work

5. Ensure the root [`README.md`](README.md:1) links only canonical docs
   - It already does; keep it that way
   - Avoid linking archive indexes from README

## Priority 3: Decide how to reconcile the truth-engine spec with the current user manual

6. Make an explicit decision: is the Build Bible truth-engine model a shipped behavior or a roadmap?
   - If roadmap: label the journey docs as roadmap/spec and keep them out of user-facing documentation paths
   - If shipped: update [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1) to introduce:
     - facts, validation, coverage, refusal behavior
     - what the user sees in UI and how to resolve coverage gaps
   - References to reconcile:
     - [`build bible.txt`](build bible.txt:1)
     - [`full user journey  user flow.txt`](full user journey  user flow.txt:1)
     - [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:1)

## Priority 4: Light tidy-ups for trust and consistency

7. Privacy language check
   - Ensure canonical docs do not over-claim
   - Confirm statements align with red lines in [`PRODUCT_INTENT.md`](PRODUCT_INTENT.md:58)

8. Exports availability matrix
   - Replace vague text like depending on your build with a small table describing what is present in the current build
   - If unknown, explicitly say not available in this release
   - Source location: [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md:268)

