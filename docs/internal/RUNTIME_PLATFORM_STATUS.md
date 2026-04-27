# Runtime Platform Status

## Purpose

This document records the current implemented status of Runtime Platform Wave 1B.

It is an internal status checkpoint. It must not be read as a user manual, installer guide, or provisioning promise.

## Current status

Runtime Platform Wave 1B provides a read-only foundation for local runtime awareness.

The current implementation can:

- discover supported local runtime providers using read-only checks;
- present runtime/provider status honestly;
- aggregate provider status, hardware-based recommendations, and consent requirements into a read model;
- expose read-only runtime status in the desktop sidebar;
- define consent requirements for future runtime actions;
- define provisioning action contracts for future implementation;
- define consent prompt copy for future user approval flows;
- present runtime action eligibility as blocked/non-executing by design.

## Supported read-only provider discovery

The read-only discovery layer supports provider checks for:

- LM Studio via local OpenAI-compatible model listing;
- Ollama via local model listing;
- configured local OpenAI-compatible endpoints.

Provider discovery must not:

- install a runtime;
- start a runtime;
- stop a runtime;
- load a model;
- unload a model;
- download a model;
- mutate configuration;
- send project data to a provider.

Reachable means endpoint reachable only. It does not mean the runtime is approved, configured, loaded, or safe for a project workload.

## Hardware and model recommendation posture

The runtime platform includes a source-defined model catalog and hardware-aware recommendation skeleton.

The recommendation layer may classify machine posture and recommend a model posture, such as a balanced 7B quantized posture for suitable 8 GB VRAM / 16 GB RAM class machines.

This recommendation is advisory only. It does not download, load, install, or execute a model.

## Consent and provisioning posture

The current implementation defines consent requirements and provisioning contracts for future work.

The following actions are modeled as consent-controlled concepts:

- internet use;
- model download;
- provider start;
- provider stop;
- model load;
- model unload;
- non-local endpoint use;
- runtime install.

Consent is denied by default.

Current consent state is not a shipped persistent approval system for real provisioning execution.

## Runtime action eligibility posture

The eligibility presenter may produce action rows showing whether a future action is eligible or blocked.

Current runtime action output is deliberately non-executing.

In the current Wave 1B state:

- `executes` remains false;
- `can_execute` remains false;
- action rows are presentation/contract outputs only;
- no real runtime mutation is performed.

## Explicit non-goals in current implementation

The current implementation does not:

- install runtimes;
- download models;
- start providers;
- stop providers;
- load models;
- unload models;
- use cloud/non-local endpoints as an active runtime path;
- persist consent approvals as a complete user-facing approval system;
- execute provisioning plans;
- provide active runtime action buttons;
- silently mutate user machine state;
- silently send project data outside the machine.

## Product doctrine boundary

Runtime Platform work must remain aligned with SerapeumAI doctrine:

- Windows-first;
- local-first;
- privacy-first;
- evidence-backed;
- human-in-the-loop;
- no hidden internet use;
- no hidden provider mutation;
- no hidden model download/load/install;
- no silent runtime actions.

Future runtime provisioning requires a separate owner-approved implementation phase.

## Current safe next steps

The safe continuation path after this checkpoint is:

1. keep Wave 1B documentation aligned with implemented behavior;
2. avoid wiring real runtime actions directly;
3. design any future provisioning implementation as a separate approved phase;
4. add UI/consent dry-run layers before any real install/download/start/load behavior;
5. require explicit owner approval before any real provisioning action implementation.

## Release note

This checkpoint documents existing runtime-platform behavior only.

It does not change source behavior, user-facing runtime actions, packaging, dependencies, or distribution behavior.
