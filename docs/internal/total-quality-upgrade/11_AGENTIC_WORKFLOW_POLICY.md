# 11 — Agentic Workflow Policy

## Purpose

Define safe agentic behavior for SerapeumAI before tool-using chat or multi-step workflows are implemented.

## Core rule

The LLM may choose tools and fill arguments. The application executes tools. The LLM narrates verified results. The LLM does not calculate, certify, write truth, or act silently.

## Allowed baseline concepts

- Tool registry.
- Tool policy gate.
- Skill registry.
- Agent run state.
- Safe trace.
- Memory separation.
- ToolBench / AgentBench.

## First internal tools

- fact query,
- evidence retrieval,
- lineage lookup,
- coverage check,
- deterministic calculator,
- unit conversion,
- metadata inspection.

## Tool requirements

Every tool must declare:

- tool id,
- input schema,
- output schema,
- authority level,
- scope,
- side effects,
- consent requirement,
- human approval requirement,
- whether it can govern truth,
- audit requirement,
- timeout and retry policy.

## Skill requirements

Every skill must declare:

- skill id,
- purpose,
- allowed tools,
- required inputs,
- required source lanes,
- refusal conditions,
- output contract,
- quality checks.

## Memory rules

- Session memory is conversation context only.
- Project memory must not govern truth unless promoted through the fact pipeline.
- User preferences must not alter truth semantics.
- Tool/runtime memory is diagnostic only.

## Forbidden baseline behavior

- No arbitrary MCP execution.
- No default web tools.
- No LLM calculations.
- No memory as certified truth.
- No autonomous file edits.
- No automatic certification.
- No uncontrolled agent swarms.
- No silent DB writes.
- No tool call without policy validation.

## Safe trace rule

A trace may show selected skill, tools called, evidence found, coverage result, calculations performed, limitations, and final answer/refusal. It must not expose private reasoning.
