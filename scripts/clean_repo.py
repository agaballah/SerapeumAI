import os
import shutil
import glob
from pathlib import Path

def clean_repo(root_dir="."):
    root = Path(root_dir).resolve()
    print(f"--- Cleaning Repository: {root} ---")

    # 1. Remove all SQLite databases (except perhaps standards if needed, but clean run usually recreates)
    dbs = glob.glob(str(root / "**/*.sqlite3"), recursive=True)
    for db in dbs:
        try:
            os.remove(db)
            print(f"Removed: {db}")
        except Exception as e:
            print(f"Error removing {db}: {e}")

    # 2. Remove all __pycache__ folders
    pycaches = glob.glob(str(root / "**/__pycache__"), recursive=True)
    for pc in pycaches:
        try:
            shutil.rmtree(pc)
            print(f"Removed: {pc}")
        except Exception as e:
            print(f"Error removing {pc}: {e}")

    # 3. Remove .serapeum metadata and vector folders
    metadata_folders = [".serapeum", ".serapeum_vectors", ".pytest_cache"]
    for folder in metadata_folders:
        for p in root.rglob(folder):
            if p.is_dir():
                try:
                    shutil.rmtree(p)
                    print(f"Removed: {p}")
                except Exception as e:
                    print(f"Error removing {p}: {e}")

    # 4. Remove logs and tmp files
    temp_patterns = ["*.log", "test_out*.txt", "test_error*.txt", "benchmark_report*.md"]
    for pattern in temp_patterns:
        files = glob.glob(str(root / f"**/{pattern}"), recursive=True)
        for f in files:
            try:
                os.remove(f)
                print(f"Removed: {f}")
            except Exception as e:
                print(f"Error removing {f}: {e}")

    # 5. Specific project temp dirs if any
    test_projects = ["test_scaling_project", "MCCC_Riyadh HQ"]
    for tp in test_projects:
        tp_path = root / tp
        if tp_path.exists() and tp_path.is_dir():
            print(f"Found test project dir: {tp_path}. Suggesting manual check if it contains source documents.")
            # We don't delete source documents automatically unless explicitly requested, 
            # but we clear its .serapeum etc above.

    print("--- Cleanup Complete ---")

if __name__ == "__main__":
    clean_repo()
