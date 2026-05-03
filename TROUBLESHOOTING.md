# Troubleshooting

This guide covers common local runtime and release-candidate observations.

## Runtime is not ready

If model-backed analysis or chat is unavailable:

- confirm the local runtime is open;
- confirm the expected local endpoint is reachable;
- confirm the expected model is loaded;
- use **Re-check Runtime** inside the app.

The app should report runtime state honestly rather than presenting unavailable model paths as ready.

## GPU, VRAM, or thermal warnings

On constrained laptops, especially around 8 GB VRAM, you may see:

- GPU temperature warnings;
- VRAM-limited model routing downgrade;
- embedding model loading on CPU;
- analysis model downgraded to chat model.

These are performance/runtime caveats. They do not automatically invalidate deterministic extraction or stored facts.

## Page-level model output parse retries

Some pages may produce model-output parse retries during AI-assisted analysis.

Interpretation:

- deterministic extraction can still succeed;
- Facts and File Inspector evidence lanes may still be valid;
- AI Output Only remains non-governing unless promoted through review/certification;
- retry or inspect the affected page when analysis quality matters.

## Missing OCR/PDF tools

Some document-processing paths may require tools such as Tesseract OCR or Poppler/PDF utilities. If they are missing, PDF/OCR processing may be limited.

## Shutdown observations

The current packaged smoke proof showed clean shutdown with no Tk post-destroy noise in the supplied tail. If you see shutdown noise, record:

- exact steps;
- terminal/log tail;
- whether background jobs were running;
- whether a project was open.
