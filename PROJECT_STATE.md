# Project State

This file is for repository work continuity only.

It governs repository workers: humans, AI models, coding assistants, reviewers, scripts, and future automation working on this source repository.

It is not application runtime policy.
It is not user project memory.
It is not certified project evidence.
It is not answer authority for the application.

## Current Snapshot

- Last updated: 2026-07-12
- Branch: `openhands/iteration1-controlled`
- Baseline source commit before continuity system: `579fc7b Add Runtime Wizard read-model presenter (#157)`
- Latest local commit from operational re-entry audit: `f995f5b2e4c71eb84ca7e0fe1ea5aad7831789f0` (`Record read-only continuity validation`, 2026-07-12T10:47:03+03:00)
- Working tree: clean before controlled tiny-change validation
- Current gate: controlled tiny-change validation
- Active task: record that the read-only operational re-entry audit passed locally, with remote evidence marked PARTIAL
- Current blocker: remote evidence is PARTIAL due credential/access limitations
- Remote evidence limitation:
  - no upstream configured for `openhands/iteration1-controlled`
  - `git ls-remote` failed with `SEC_E_NO_CREDENTIALS`
  - `gh` failed with `HTTP 401`
  - public GitHub issue count contradicted connector issue search
- Next required action: manager review of this tiny-change validation

## Last Completed Work

- Summary:
  - Confirmed controlled branch has no extra commits beyond `main`.
  - Confirmed only `AGENTS.md` was untracked.
  - Confirmed `_LOCAL_APP_ARCHIVE/**` is local-only ignored archive material.
  - Confirmed active-source secret-like matches were harmless.
  - Paused external repository-worker execution until continuity files are designed.
- Files touched:
  - none committed
  - `AGENTS.md` untracked draft existed before rewrite
- Verification:
  - Git branch/status inspection
  - Archive tracking/ignore inspection
  - Active-source secret-like scan
- Result:
  - safe to create continuity files

## Current Risks

| Risk | Status | Treatment |
|---|---|---|
| Context loss across chats/tools | active | continuity files required |
| Inconsistent rules between workers | active | `AGENTS.md` required |
| Work not written down | active | `WORK_LOG.md` required |
| Local archive pollution | controlled | `_LOCAL_APP_ARCHIVE/**` forbidden as normal context |
| Secret leakage | controlled | active source scan found no key strings |
| Uncontrolled commits | controlled | commit/push require explicit approval |
| Packaging regression | controlled | packaging files require explicit approval |
| Runtime environment dependency gap | open | handle separately as runtime-environment task |

## Known Failing / Blocked Checks

| Check | Status | Cause | Next action |
|---|---|---|---|
| direct runtime launch | blocked | machine Python missing `customtkinter` | handle later as runtime-environment task |
| continuity files committed | passed | committed in repository continuity baseline | continue to read-only worker validation |

## Active Decisions

| ID | Decision | Status |
|---|---|---|
| DEC-001 | Repository continuity must live in files, not chat history | active |
| DEC-002 | Continuity system must be model/tool/person agnostic | active |
| DEC-003 | Every meaningful task must update state and log before completion | active |
| DEC-004 | Minimal necessary change doctrine governs implementation | active |
| DEC-005 | Commit/push require explicit approval | active |
| DEC-006 | Runtime/app policy is separate from repository-worker rules | active |

## Files In Progress

| File | Reason | Status |
|---|---|---|
| `AGENTS.md` | permanent repository-worker rules | written, awaiting review |
| `PROJECT_STATE.md` | live repository state | written, awaiting review |
| `WORK_LOG.md` | chronological work record | written, awaiting review |

## Handoff

The next repository worker must:

1. read `AGENTS.md`;
2. read `PROJECT_STATE.md`;
3. read latest `WORK_LOG.md` entries;
4. check Git branch and status;
5. continue only from the active task above;
6. avoid `_LOCAL_APP_ARCHIVE/**` as normal context;
7. avoid packaging files unless explicitly approved;
8. update this file and append `WORK_LOG.md` before claiming completion.
