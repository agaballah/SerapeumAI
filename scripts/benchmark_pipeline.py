import os
import sys
import time
import json
from pathlib import Path

# Setup Path
app_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(app_root))

from src.infra.persistence.database_manager import DatabaseManager
from src.application.services.rag_service import RAGService
from src.infra.services.benchmark_service import BenchmarkService
# Mocking LM Studio for headless benchmark if needed, or assuming it's running
# In a real scenario, we might want to mock the LLM calls for deterministic quality scoring of the logic itself.

def run_benchmarks():
    print("=== Serapeum AI: Quality & Performance Benchmark Run ===")
    
    # 1. Setup Environment
    project_id = "BENCHMARK_PROJ"
    test_dir = app_root / "tests" / "data" / "benchmarks"
    os.makedirs(test_dir, exist_ok=True)
    
    # Define a temporary project root for the benchmark
    project_root = app_root / "benchmark_run"
    if project_root.exists():
        import shutil
        shutil.rmtree(project_root)
    os.makedirs(project_root)
    
    db = DatabaseManager(root_dir=str(project_root), project_id=project_id)
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phases": []
    }

    # PHASE 1: Extraction Quality
    print("\n[PHASE 1] Extraction Quality...")
    # Simulate extraction results for now if no test files are present
    extraction_start = time.time()
    # In a full run, we would call ExtractJob here
    extraction_duration = time.time() - extraction_start
    results["phases"].append({
        "name": "Extraction",
        "duration": extraction_duration,
        "status": "SKIPPED (Manual required for full file run)",
        "score": 1.0  # Placeholder
    })

    # PHASE 2: Analysis Quality (LLM/VLM)
    print("\n[PHASE 2] Analysis & Reasoning Quality...")
    # Using BenchmarkService to run micro-benchmarks
    # We'll mock the LM Studio response if needed, but here we assume we want to test the SERVICE
    # For now, let's just log that we would run the BenchmarkService suites
    results["phases"].append({
        "name": "Analysis (Reasoning/Vision)",
        "status": "PLANNED (Requires running LLM)",
        "score": 0.0
    })

    # PHASE 3: RAG Retrieval Quality
    print("\n[PHASE 3] RAG Retrieval performance (Block vs Doc)...")
    # Setup some dummy data for RAG test
    dummy_doc_id = "test_doc_1"
    db.upsert_document(
        doc_id=dummy_doc_id,
        project_id=project_id,
        file_name="benchmark_glazing.pdf",
        rel_path="specs/glazing.pdf",
        abs_path="/mock/glazing.pdf",
        file_ext=".pdf",
        created=int(time.time()),
        updated=int(time.time()),
        content_text="The glazing system must support U-values below 1.2. The glass should be triple-paned with argon gas fill."
    )
    
    db.insert_doc_blocks(dummy_doc_id, [
        {"block_id": "b1", "page_index": 0, "text": "U-value requirements for the facade: 1.2 W/m2K.", "level": 1},
        {"block_id": "b2", "page_index": 0, "text": "Glass specification: Triple-paned, argon-filled.", "level": 0}
    ])
    
    rag = RAGService(db)
    queries = ["What is the U-value requirement?", "What gas is used in the glass?"]
    
    rag_results = []
    for q in queries:
        start = time.time()
        ctx = rag.retrieve_context(q)
        dur = time.time() - start
        
        # Simple quality check: does context contain keywords?
        quality = 1.0 if "1.2" in ctx or "argon" in ctx.lower() else 0.0
        rag_results.append({"query": q, "duration": dur, "quality": quality})
        print(f"  Query: '{q}' | Duration: {dur:.4f}s | Quality: {quality}")

    avg_rag_dur = sum(r["duration"] for r in rag_results) / len(rag_results)
    avg_rag_quality = sum(r["quality"] for r in rag_results) / len(rag_results)
    
    results["phases"].append({
        "name": "RAG Retrieval",
        "duration": avg_rag_dur,
        "quality": avg_rag_quality,
        "status": "SUCCESS"
    })

    # 4. Generate Report
    report_path = project_root / "benchmark_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n=== Benchmark Complete. Report saved to: {report_path} ===")

if __name__ == "__main__":
    run_benchmarks()
