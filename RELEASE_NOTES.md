# SerapeumAI Release Notes

## Release candidate after final packaging proof

Status: release candidate available; owner publish decision pending in #126.

### Authority

```text
main includes PR #123
commit: 51bc3280e1adf9e3cc53859cb2f99bc0b8847548
final packaging issue: #125 — PACKAGING PASS
publication hygiene issue: #127 — active before final publish decision
```

### Artifact

```text
dist\SerapeumAI_Portable\SerapeumAI.exe
size: 110206723 bytes
```

No GitHub Release/tag is created by this file.

---

## Passed gates

- Release-relevant source regression: 115 passed in 1.81s.
- Manual source workflow smoke: passed with caveats.
- Documentation honesty checkpoint: passed.
- Existing packaging script: passed with exit code 0.
- Packaged executable: produced, fresh, and non-empty.
- Packaged app smoke: passed on Windows.
- Packaged File Inspector lanes: passed.
- Packaged Facts page and lineage/evidence popup: passed.
- Packaged Expert Chat evidence-labeled answer: passed.
- Shutdown tail: no Tk post-destroy / bgerror / invalid command noise observed.

---

## Known caveats

- Constrained 8 GB VRAM laptops may show runtime, VRAM, or GPU-temperature warnings.
- Model routing may downgrade analysis to chat when VRAM is limited.
- Embeddings may load on CPU when VRAM is reserved or insufficient.
- Page-level LLM JSON parse retries/errors can occur during analysis.
- These are runtime/performance/analysis-quality caveats, not current packaging blockers.

---

## Explicit non-enabled behavior

The current release candidate does not enable or claim:

- autonomous chat tool execution;
- MCP integration;
- autonomous agent loops;
- runtime provider provisioning or model download control;
- Revit bridge;
- Schedule Truth Workspace implementation;
- CPM engine;
- PDF VLM routing;
- IFC fallback parser when `ifcopenshell` is missing;
- typed Office/CAD persistence;
- generic Excel workbook semantic persistence;
- guaranteed legal, contractual, regulatory, or compliance approval.

---

## Release decision status

The final publish decision is intentionally separate from packaging proof.

Allowed decisions in #126:

- publish now / create GitHub Release;
- hold artifact privately;
- require broader-machine validation first;
- prepare announcement only, no release yet.
