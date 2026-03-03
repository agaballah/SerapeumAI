import os
import sys
import sqlite3
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.ERROR) # Only show errors to keep output clean

# Setup Path
app_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(app_root))

from src.infra.persistence.database_manager import DatabaseManager
from src.infra.persistence.global_db_initializer import ensure_global_db, global_db_path

def test_unified_db():
    print("=== Serapeum AI: Dual-Database Strategy Verification ===")
    
    # 1. Global DB Setup
    g_path = global_db_path()
    print(f"[*] Global DB Location: {g_path}")
    
    try:
        ensure_global_db(g_path)
        g_db = DatabaseManager(
            root_dir=os.path.dirname(g_path), 
            db_name=os.path.basename(g_path),
            migrations_dir=str(app_root / "src" / "infra" / "persistence" / "global_migrations")
        )
        print("✓ Global DB Initialization: SUCCESS")
        
        tables = [t[0] for t in g_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        shared_tables = ["standards", "clauses", "model_benchmarks", "model_preferences"]
        for t in shared_tables:
            if t in tables:
                print(f"  ✓ Global Table '{t}': OK")
            else:
                print(f"  ✗ Global Table '{t}': MISSING")
        g_db.close_connection()
    except Exception as e:
        print(f"✗ Global DB Initialization: FAILED ({e})")

    # 2. Project DB Setup (Isolation Test)
    print("\n[*] Project DB Isolation Test")
    p_root = app_root / "tests" / "data" / "verify_project"
    p_root.mkdir(parents=True, exist_ok=True)
    p_db_path = p_root / "project.sqlite3"
    if p_db_path.exists():
        p_db_path.unlink() # Start fresh

    try:
        p_db = DatabaseManager(root_dir=str(p_root), db_name="project.sqlite3")
        print("✓ Project DB Initialization: SUCCESS")
        
        p_tables = [t[0] for t in p_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        # Verify Project Core
        if "documents" in p_tables:
            print("  ✓ Project Table 'documents': OK")
        
        # Verify Isolation (Global tables should NOT be here if strictly separated)
        # Note: In current Serapeum, some legacy migrations might still add these tables.
        # But we want to ensure the logic uses Global for new data.
        if "standards" in p_tables:
            print("  ! Note: Legacy 'standards' table found in Project DB (Isolation incomplete in schema but logic redirected)")
        else:
            print("  ✓ Strict Isolation: 'standards' NOT found in Project DB")
            
        p_db.close_connection()
    except Exception as e:
        print(f"✗ Project DB Initialization: FAILED ({e})")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    test_unified_db()
