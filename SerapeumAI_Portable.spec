# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SerapeumAI portable Windows build.

Packet 9 packaging entrypoint.

Rules:
- Build from run.py.
- Do not include local runtime state (.serapeum), models, build, or dist.
- Include runtime data needed by the app: migrations, prompt templates, README/docs.
- Keep packaging Windows-first and one-folder for easier inspection/debugging.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

ROOT = Path(SPECPATH).resolve()


def _add_tree(datas, source_dir: Path, dest_dir: str, allowed_suffixes=None):
    if not source_dir.exists():
        return
    allowed = {s.lower() for s in allowed_suffixes} if allowed_suffixes else None
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = set(part.lower() for part in path.relative_to(ROOT).parts)
        if any(part in rel_parts for part in {".serapeum", "build", "dist", "models", "__pycache__"}):
            continue
        if allowed is not None and path.suffix.lower() not in allowed:
            continue
        rel_parent = path.parent.relative_to(source_dir)
        dest = str(Path(dest_dir) / rel_parent)
        datas.append((str(path), dest))


def _add_file(datas, source_file: Path, dest_dir: str):
    if source_file.exists() and source_file.is_file():
        datas.append((str(source_file), dest_dir))


datas = []

# Runtime data used through filesystem paths.
_add_tree(
    datas,
    ROOT / "src" / "infra" / "persistence" / "migrations",
    "src/infra/persistence/migrations",
    allowed_suffixes={".sql"},
)
_add_tree(
    datas,
    ROOT / "src" / "domain" / "templates",
    "src/domain/templates",
    allowed_suffixes={".yaml", ".yml", ".json", ".txt", ".md"},
)
_add_tree(
    datas,
    ROOT / "src" / "compliance",
    "src/compliance",
    allowed_suffixes={".yaml", ".yml", ".json", ".txt", ".md", ".csv"},
)
_add_tree(
    datas,
    ROOT / "docs",
    "docs",
    allowed_suffixes={".md", ".txt", ".json", ".yaml", ".yml"},
)
_add_file(datas, ROOT / "README.md", ".")

# Some UI/runtime packages carry data files; collect when installed.
for package_name in ("customtkinter",):
    try:
        datas += collect_data_files(package_name)
    except Exception:
        pass

hiddenimports = []
try:
    hiddenimports += collect_submodules("src")
except Exception:
    pass


a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "setuptools.tests",
        "pip._vendor.pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SerapeumAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SerapeumAI_Portable",
)
