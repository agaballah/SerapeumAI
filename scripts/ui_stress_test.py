import os
import sqlite3
import uuid
import time
import random
import argparse

def create_stress_data(db_path, num_docs=1000, num_facts=5000):
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get active project ID if any, or use a default
    project_id = "STRESS_TEST_PROJ"
    
    print(f"Generating {num_docs} mock documents...")
    # Add mock file_versions
    # Schema: file_id, project_id, path, file_type, created_at (guessed from documents_page.py)
    # Actually documents_page.py uses: source_path, file_id FROM file_versions
    
    # Let's ensure tables exist (minimal schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_versions (
            file_version_id TEXT PRIMARY KEY,
            file_id TEXT,
            source_path TEXT,
            imported_at INTEGER,
            created_at INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            fact_id TEXT PRIMARY KEY,
            fact_type TEXT,
            subject_id TEXT,
            value_text TEXT,
            value_num REAL,
            value_json TEXT,
            status TEXT,
            created_at INTEGER
        )
    """)

    # Batch insert docs
    doc_rows = []
    now = int(time.time())
    for i in range(num_docs):
        fv_id = str(uuid.uuid4())
        f_id = f"FILE_{i}"
        path = f"C:\\Projects\\StressTest\\Drawing_{i:04d}.pdf"
        doc_rows.append((fv_id, f_id, path, now - i*60, now - i*60))
    
    cursor.executemany("INSERT INTO file_versions (file_version_id, file_id, source_path, imported_at, created_at) VALUES (?,?,?,?,?)", doc_rows)

    print(f"Generating {num_facts} mock facts...")
    fact_types = ["schedule.critical_path_membership", "bim.element_inventory_count_by_type", "procurement.delivery_date", "workflow.rfi_status"]
    statuses = ["VALIDATED", "CANDIDATE", "REJECTED"]
    
    fact_rows = []
    for i in range(num_facts):
        f_id = str(uuid.uuid4())
        f_type = random.choice(fact_types)
        subj = f"ELEMENT_{random.randint(1, 10000)}"
        status = random.choice(statuses)
        val_text = f"Mock Value for fact {i}"
        val_num = random.random() * 100
        fact_rows.append((f_id, f_type, subj, val_text, val_num, None, status, now - i*10))

    cursor.executemany("INSERT INTO facts (fact_id, fact_type, subject_id, value_text, value_num, value_json, status, created_at) VALUES (?,?,?,?,?,?,?,?)", fact_rows)

    conn.commit()
    conn.close()
    print("Done! Data generated successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serapeum UI Stress Test Data Generator")
    parser.add_argument("--db", type=str, required=True, help="Path to the .serapeum SQLite database")
    parser.add_argument("--docs", type=int, default=1000, help="Number of documents to generate")
    parser.add_argument("--facts", type=int, default=5000, help="Number of facts to generate")
    
    args = parser.parse_args()
    
    if not os.path.exists(os.path.dirname(args.db)) and os.path.dirname(args.db) != "":
        os.makedirs(os.path.dirname(args.db), exist_ok=True)
        
    create_stress_data(args.db, args.docs, args.facts)
