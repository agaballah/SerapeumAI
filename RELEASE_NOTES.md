# SerapeumAI Release Notes

## v0.1.0-3u published release

Status: published.

Release URL: https://github.com/agaballah/SerapeumAI/releases/tag/v0.1.0-3u

### Authority

```text
published release: v0.1.0-3u
release authority: 16723b0970a81c181bb0df6801178c7032d49f21
final packaging issue: #125 - PACKAGING PASS
final release issue: #126 - closed as completed
broader Windows validation issue: #129 - closed as completed
3U stabilization issue: #135 - closed as completed
```

### Artifact

```text
dist\SerapeumAI_Portable\SerapeumAI.exe
size: 110206723 bytes
```

Published release assets: SerapeumAI_Portable_v0.1.0-3u.zip.part001, SerapeumAI_Portable_v0.1.0-3u.zip.part002, SHA256SUMS_v0.1.0-3u.txt, README_RECOMBINE_v0.1.0-3u.txt.

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

The current published release does not enable or claim:

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

The release is published. Post-publish upgrade planning continues under issue #138.
