# Repository Worker Instructions

This file is for repository work continuity only.

It governs repository workers: humans, AI models, coding assistants, reviewers, scripts, and future automation working on this source repository.

It is not application runtime policy.
It is not user project memory.
It is not certified project evidence.
It is not answer authority for the application.

## Core rule

Anyone continuing work in this repository must preserve continuity, minimize unnecessary change, report honestly, and write down meaningful work before calling a task complete.

## Mandatory start-of-task protocol

Every repository worker must:

1. Read this file.
2. Read `PROJECT_STATE.md`.
3. Read the latest relevant entries in `WORK_LOG.md`.
4. Check the current Git branch.
5. Check the current Git status.
6. Check the latest commit.
7. Classify the task.
8. Identify the affected subsystem.
9. Decide whether code is needed at all.
10. State intended touched files, risks, and verification before editing.

Repository reality is more authoritative than chat history, old summaries, or assumptions.

## Task classes

Classify every task as one of:

- `audit task`
- `source task`
- `test task`
- `repo-continuity task`
- `runtime-environment task`
- `packaging task`
- `release task`
- `workflow task`

No editing starts before task classification.

## Minimum Necessary Change Doctrine

Efficient means minimal, not careless.

The best code is code that does not need to be written.

Before writing code, stop at the first rung that solves the problem:

1. Does this need to be built at all?
2. Can existing behavior solve it?
3. Can deletion or configuration solve it?
4. Can the standard library solve it?
5. Can the native platform solve it?
6. Can an already-installed dependency solve it?
7. Can this be one local change?
8. Only then write new code.

Rules:

- No unnecessary abstraction.
- No new dependency without explicit approval.
- No unrelated refactor.
- No boilerplate nobody asked for.
- Deletion over addition.
- Boring over clever.
- Fewest files possible.
- Prefer the edge-case-correct option when two simple options are similar.
- Mark intentional simplifications with a comment that names the ceiling and upgrade path.
- Non-trivial logic must leave one runnable check behind.

Never be minimal about:

- security;
- secrets;
- data-loss prevention;
- input validation at trust boundaries;
- Windows portability;
- packaging behavior;
- release behavior;
- runtime startup;
- error handling that protects users;
- explicitly requested behavior.

## Repository boundaries

Primary editable code:

- `src/**`

Editable only when needed:

- `run.py`
- `run_tests.py`
- `README.md`
- `INSTALL.md`
- `AGENTS.md`
- `PROJECT_STATE.md`
- `WORK_LOG.md`
- `docs/**`

Sensitive files requiring explicit approval:

- `SerapeumAI_Portable.spec`
- `build_portable.ps1`
- `build_portable.bat`

Not normal context or edit targets:

- `build/**`
- `dist/**`
- `.serapeum/**`
- `models/**`
- `**/__pycache__/**`
- `_LOCAL_APP_ARCHIVE/**`

`_LOCAL_APP_ARCHIVE/**` is local-only archive material. It is not repository truth and must not be used as normal context.

## Security

Never print, store, commit, or request secrets.

Do not paste API keys into chat, source files, screenshots, logs, markdown files, or committed environment files.

Do not create repository `.env` files unless explicitly approved and confirmed ignored.

If a possible secret appears, stop and classify it before continuing.

## Verification

Every non-trivial change requires the smallest meaningful runnable check.

Acceptable checks include:

- focused test;
- import check;
- syntax check;
- source scan;
- assert-based demo;
- manual runtime proof when UI/runtime behavior is involved.

If a check cannot be run, state why and record what remains unproven.

## Honest error reporting

Failures must be reported with:

- what failed;
- command/check;
- where it failed;
- likely cause;
- source bug or environment issue;
- files changed;
- files not changed;
- what remains unproven;
- next smallest recovery step.

Do not claim success while checks are failing or skipped.

## Completion rule

A meaningful task is not complete until:

1. `PROJECT_STATE.md` is updated.
2. `WORK_LOG.md` is appended.
3. Files touched are listed.
4. Verification is listed.
5. Errors or blockers are documented.
6. Final Git status is reported.
7. Next action is stated.

## Commit and push rule

Default: no commit, no push, no pull request.

Before any commit, report:

- branch;
- git status;
- diff stat;
- files changed;
- checks run;
- risks;
- rollback method;
- proposed commit message.

Commit or push only after explicit approval.

## Reporting format

For every significant task, report:

- task class;
- files touched;
- what changed;
- why it changed;
- checks run;
- result;
- unresolved issues;
- packaging risk;
- Windows risk;
- rollback risk;
- next action.
