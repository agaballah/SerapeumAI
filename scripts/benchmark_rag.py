import time
import sys
import os
from pathlib import Path

# Setup Path
app_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(app_root))

from src.infra.persistence.database_manager import DatabaseManager
from src.application.services.rag_service import RAGService

def benchmark_retrieval(project_id, db_path, queries):
    db = DatabaseManager(os.path.dirname(db_path), project_id=project_id)
    rag = RAGService(db)
    
    print(f"--- RAG Benchmarks for {project_id} ---")
    print(f"Context: {db.execute('SELECT COUNT(*) FROM doc_blocks').fetchone()[0]} blocks, {db.execute('SELECT COUNT(*) FROM facts').fetchone()[0]} facts")
    
    results = []
    for q in queries:
        start = time.time()
        context = rag.retrieve_context(q)
        duration = time.time() - start
        
        if isinstance(context, dict):
            block_count = len(context.get("text_blocks", []))
            fact_count = len(context.get("facts", []))
        else:
            block_count = 0
            fact_count = 0
            print(f"Warning: Unexpected response type for query '{q[:20]}...': {type(context)}")
        
        print(f"Query: '{q[:40]}...' | Time: {duration:.3f}s | Blocks: {block_count} | Facts: {fact_count}")
        results.append(duration)
    
    avg = sum(results) / len(results)
    print(f"--- Average Retrieval Time: {avg:.3f}s ---")

if __name__ == "__main__":
    queries = [
        "What are the total number of activities in the schedule?",
        "Summarize the glazing requirements for the project.",
        "What is the total price for ITEM No. 1.0?",
        "Uptime Tier requirements for Riyadh HQ",
        "HVAC design parameters"
    ]
    benchmark_retrieval("MCCC_Riyadh HQ", r"D:\AAC\Misc\MCCC_Riyadh HQ\.serapeum\serapeum_MCCC_Riyadh_HQ.sqlite3", queries)
