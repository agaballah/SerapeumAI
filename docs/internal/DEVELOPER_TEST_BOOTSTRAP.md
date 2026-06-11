# Developer Test Bootstrap Guidance

Task class: documentation task / test hygiene task.

R2-A defines test reporting lanes only. It does not add dependencies, edit packaging, or implement runtime features.

Test lanes:

1. Dependency-light direct checks: standard Python checks that avoid importing the full app stack.
2. Focused pytest checks: targeted pytest commands when pytest and required packages are available.
3. Wider pytest checks: full src/tests only when broader local dependencies are available.
4. GUI/extractor/integration checks: tests that may require UI packages, PDF/OCR packages, Tesseract, Poppler, runtime providers, or fixtures.

Future PRs must report task class, touched files, packaging risk, Windows risk, rollback risk, test lane used, exact command, exact result, and whether wider tests passed, were skipped, or were blocked by missing local dependencies.

Never commit .venv, logs, __pycache__, build, dist, models, .serapeum runtime state, local cleanup scripts, or local cleanup CSV files.

Do not add or upgrade dependency files without a separate bounded task, packaging risk review, and Windows validation plan.
