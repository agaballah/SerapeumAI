# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import ezdxf
import logging
from src.infra.persistence.database_manager import DatabaseManager
from src.application.services.document_service import DocumentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyPhase0.2")

def setup_mock_cad_project(project_root: str):
    """Create a parent DXF that references a child DXF."""
    parent_path = os.path.join(project_root, "drawing_parent.dxf")
    child_path = os.path.join(project_root, "drawing_child.dxf")
    
    # 1. Create Child
    child_doc = ezdxf.new()
    child_doc.modelspace().add_text("I am the child drawing")
    child_doc.saveas(child_path)
    
    # 2. Create Parent with XREF to Child
    parent_doc = ezdxf.new()
    # Create an XREF block
    parent_doc.blocks.new(name="CHILD_REF", dxfattribs={"xref_path": "drawing_child.dxf"})
    parent_doc.modelspace().add_text("I am the parent drawing")
    parent_doc.saveas(parent_path)
    
    return parent_path, child_path

def verify():
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Setting up test project in {temp_dir}")
        parent_path, child_path = setup_mock_cad_project(temp_dir)
        
        db = DatabaseManager(root_dir=temp_dir, project_id="test_cad_project")
        service = DocumentService(db=db, project_root=temp_dir)
        
        logger.info("Starting ingestion of parent drawing...")
        project_id = "test_cad"
        service.ingest_document(
            abs_path=parent_path,
            project_id=project_id,
            rel_path="drawing_parent.dxf"
        )
        
        # Verify Database
        logger.info("Checking database for results...")
        
        # 1. Check if both documents exist
        docs = db.list_documents(project_id=project_id)
        file_names = {d["file_name"] for d in docs}
        logger.info(f"Ingested documents: {file_names}")
        
        if "drawing_parent.dxf" not in file_names:
            raise Exception("Parent document missing from database!")
        if "drawing_child.dxf" not in file_names:
            raise Exception("Child document (XREF) was NOT recursively ingested!")
        
        # 2. Check for link in 'links' table
        links = db._query("SELECT * FROM links WHERE link_type='CAD_XREF'")
        logger.info(f"Found {len(links)} CAD_XREF links.")
        
        if len(links) == 0:
            raise Exception("No XREF link found in the 'links' table!")
        
        link = links[0]
        logger.info(f"Link details: {link['from_id']} -> {link['to_id']} ({link['link_type']})")
        
        # 3. Test mock DGN routing (via file extension)
        dgn_path = os.path.join(temp_dir, "test.dgn")
        with open(dgn_path, "w") as f: f.write("dummy dgn content")
        
        logger.info("Testing DGN routing (expecting delegation to CADProcessor)...")
        # Since we don't have ODA converter installed, it should log a warning but be delegated correctly.
        service.ingest_document(abs_path=dgn_path, project_id=project_id)
        
        doc_dgn = db.get_document_by_hash(project_id, "test.dgn", service._calculate_file_hash(dgn_path))
        if doc_dgn:
            logger.info(f"DGN record created: {doc_dgn['doc_id']}")
        else:
            raise Exception("DGN document record not created!")

        logger.info("✅ SUCCESS: Phase 0.2 Verification Passed!")

if __name__ == "__main__":
    try:
        verify()
    except Exception as e:
        logger.error(f"❌ VERIFICATION FAILED: {e}")
        exit(1)
