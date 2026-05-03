# Third-Party Notices

This file summarizes third-party runtime and development components relevant to SerapeumAI publication hygiene.

It is not a full legal dependency audit. Before a broad public release or commercial redistribution, run a complete dependency-license review against the exact locked environment and packaged artifact.

## Runtime and platform posture

SerapeumAI is a Windows-first, local-first desktop application. The current release-candidate path expects local runtime components to be installed and operated by the user where applicable.

## Important component families

The application may interact with or depend on components in these families, depending on the local environment and packaging state:

- Python and Python packages used by the application.
- Tk / desktop UI runtime components.
- SQLite and local persistence components.
- PDF/document processing libraries.
- OCR/PDF rendering tools where installed, such as Tesseract and Poppler.
- Local LM Studio-compatible model runtime.
- Local embedding/runtime support libraries.

## Local model/runtime note

Local language models are not distributed by this notice unless explicitly bundled in a release artifact. Users are responsible for ensuring that any local model they install or load is used under its own license and terms.

## No compliance warranty

Third-party notices do not change SerapeumAI's product boundary. SerapeumAI provides review assistance and does not provide guaranteed legal, contractual, regulatory, or compliance approval.
