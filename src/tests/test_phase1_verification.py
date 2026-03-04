from unittest.mock import MagicMock, patch
import os

# Mock Llama before importing model_manager because it imports it at top level if available
with patch.dict('sys.modules', {'llama_cpp': MagicMock()}):
    from src.infra.adapters.model_manager import ModelManager

def test_model_manager_singleton_and_lock():
    """Test that ModelManager is a singleton and its lock works."""
    # Reset singleton
    ModelManager._instance = None
    
    mm1 = ModelManager()
    mm2 = ModelManager()
    assert mm1 is mm2
    
    # Test locking
    assert mm1.lock("test_owner") is True
    assert mm2.get_status()["locked"] is True
    assert mm2.get_status()["locked_by"] == "test_owner"
    
    # Cant lock again by different owner
    assert mm1.lock("other") is False
    
    # Unlock
    mm1.unlock("test_owner")
    assert mm2.get_status()["locked"] is False

def test_chat_panel_init_robustness():
    """Test ChatPanel initializes even with None db."""
    import tkinter as tk
    from src.ui.chat_panel import ChatPanel
    
    if os.environ.get("SERAPEUM_ENV") == "ci":
        root = MagicMock() # Headless skip
    else:
        root = tk.Tk()
    try:
        # 1. Init with db=None
        cp = ChatPanel(root, db=None)
        assert cp._session_state is not None
        assert cp.ref_mgr is None
        
        # 2. Init with db=Mock but ReferenceManager fails (simulated by not mocking internals)
        db = MagicMock()
        db.root_dir = "."
        cp2 = ChatPanel(root, db=db)
        assert cp2.role_mgr is not None # RoleManager mocked or real?
        # Check ref_mgr
        # If ReferenceManager import works, it might be instantiated. 
        # If it fails, cp2.ref_mgr should be None (due to our try/except block)
    finally:
        root.destroy()

if __name__ == "__main__":
    # Manual run if pytest not available
    try:
        test_model_manager_init_no_crash()
        print("ModelManager test passed")
        test_chat_panel_init_robustness()
        print("ChatPanel test passed")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
