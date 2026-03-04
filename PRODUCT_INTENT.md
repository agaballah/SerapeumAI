# PRODUCT_INTENT — SerapeumAI (Intent + Red Lines)

This file defines what SerapeumAI is meant to be **and what it must not become**.

It is **not** a user manual. It exists so product, engineering, and documentation stay aligned.

---

## Product intent (north star)
SerapeumAI helps AEC teams **review project documents faster** by:
- Ingesting and organizing mixed project files.
- Answering questions with document-grounded evidence.
- **Truth Certification**: Providing a structured "Truth Spine" where facts can be human-verified.
- **Human-in-the-loop**: Designing for expert review rather than black-box automation.
- Running a structured compliance-style review to surface potential issues.

The product is designed to be **local-first** and **privacy-first**.

---

## Target users
- Architects
- Engineers (structural, MEP, civil)
- PM/PMC teams
- QA/QC reviewers

---

## In scope (must be true)
- **Desktop-first** workflow (Windows is the baseline)
- **Local processing** as the default posture
- **Evidence-based output** (citations back to project documents)
- A workflow that supports:
  - Projects → Documents → Processing → Chat/Compliance → Export

---

## Out of scope (explicitly not the product)
- No “design authoring” (no CAD/BIM editing).
- No cloud collaboration features as a requirement for core use.
- No automatic submission/approval actions on behalf of the user.
- No “agent” behavior that runs actions without a clear user trigger.

---

## Red lines (non-negotiable)
1) **Docs must match behavior, not ambition.**  
   If a feature is not in the shipped UI, it does not belong in user documentation.

2) **User docs are not engineering docs.**  
   No internal architecture, file paths, module names, stack diagrams, or code blocks in user-facing docs.

3) **One clear run path.**  
   For user-facing docs: one run method — `python run.py`.  
   (If packaging changes later, the docs change then.)

4) **No hidden “service language” in README.**  
   README stays user-facing and minimal. Deep setup stays in System Requirements / Troubleshooting.

5) **Privacy-first language must be accurate.**  
   If anything ever leaves the machine, it must be explicitly stated. No vague claims.

6) **No “guaranteed compliance.”**  
   Output must be framed as review assistance with evidence, not a legal/compliance certification.

---

## Documentation contract (what the docs must do)
- README: short, honest, single run path.
- User manual: describe the visible UI and flows.
- System requirements: realistic Windows + hardware guidance.
- Troubleshooting: user-first fixes for common failures.

---

## Quality bar
- Fast to start, stable to run
- Predictable UI with clear states (processing vs ready)
- Every “finding” points to evidence
- Failure modes are recoverable (clear errors, retriable actions)
