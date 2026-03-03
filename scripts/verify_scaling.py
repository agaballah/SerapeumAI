import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.infra.persistence.database_manager import DatabaseManager

def test_scaling_optimizations():
    # Use a temp project DB
    root = "test_scaling_project"
    os.makedirs(root, exist_ok=True)
    db = DatabaseManager(root_dir=root, project_id="test_scale")
    
    print("--- 1. Verifying Migration ---")
    rows = db._query("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    latest_version = rows[0]["version"] if rows else 0
    print(f"Latest migration version: {latest_version}")
    
    # Check vision_queue table
    try:
        db.execute("SELECT * FROM vision_queue LIMIT 1")
        print("✓ vision_queue table exists")
    except Exception as e:
        print(f"✗ vision_queue table check failed: {e}")

    # Check vision_indexed column
    try:
        db.execute("SELECT vision_indexed FROM pages LIMIT 1")
        print("✓ pages.vision_indexed column exists")
    except Exception as e:
        print(f"✗ pages.vision_indexed column check failed: {e}")

    print("\n--- 2. Testing Vision Queue Logic ---")
    db.enqueue_vision_page("doc_1", 1, priority=10)
    db.enqueue_vision_page("doc_1", 2, priority=5)
    db.enqueue_vision_page("doc_2", 1, priority=2)
    
    batch = db.pop_vision_queue_batch(limit=2)
    print(f"Popped batch (size {len(batch)}):")
    for item in batch:
        print(f"  - {item}")
    
    if len(batch) == 2 and batch[0]["doc_id"] == "doc_1" and batch[0]["page_index"] == 1:
        print("✓ Batch pop priority and order correct")
    else:
        print("✗ Batch pop logic failure")

    # Update status
    db.update_vision_queue_status(batch[0]["queue_id"], "done")
    db.update_vision_queue_status(batch[1]["queue_id"], "failed")
    
    # Check status
    rows = db._query("SELECT * FROM vision_queue")
    print("\nRemaining in queue:")
    for r in rows:
        print(f"  - {dict(r)}")

    print("\n--- 3. Done ---")

if __name__ == "__main__":
    test_scaling_optimizations()
