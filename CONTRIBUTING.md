# Contributing to SerapeumAI

First, thank you for considering contributing to SerapeumAI! This project is built by and for the construction engineering community.

---

## 🛠️ Development Setup

1. **Install Dev Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest ruff
   ```

2. **Code Style**:
   - We use **Ruff** for linting.
   - Please include **Google Style** docstrings for all new functions.
   - Favor **logging** over `print()` for any output that isn't purely UI-driven.

3. **Running Tests**:
   ```bash
   pytest src/tests/
   ```

---

## 📂 Where to Contribute

### 1. New Extractors
If you want to add support for a new file type (e.g., Revit, Synchro, Procore exports), create a class in `src/engine/extractors/`.

### 2. Fact Builders
Help us extract more "Truth" from existing data by adding logic to `src/engine/builders/`.

### 3. UI/UX
Enhance the desktop experience in `src/ui/`. We use **CustomTkinter** for a modern, dark-themed look.

---

## 🚀 Pull Request Process

1. Fork the repository and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Update the documentation if you've changed functionality.
5. Issue a Pull Request with a clear description of the change.

---

## ⚖️ License
By contributing, you agree that your contributions will be licensed under the **Apache 2.0 License**.
