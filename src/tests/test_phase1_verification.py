from unittest.mock import MagicMock, patch

# Mock Llama before importing model_manager because it imports it at top level if available
with patch.dict('sys.modules', {'llama_cpp': MagicMock()}):
    from src.infra.adapters.model_manager import ModelManager

def test_model_manager_init_no_crash():
    """Test that ModelManager initializes without crashing (double thread start fix)."""
    # Reset singleton
    ModelManager._instance = None
    ModelManager._monitor_thread = None
    
    with patch('src.infra.adapters.model_manager._HAS_LLAMA_CPP', True):
        mm = ModelManager()
        # Verify monitor thread started exactly once
        assert mm._monitor_thread is not None
        assert mm._monitor_thread.is_alive()
        
        # Verify unloading doesn't crash
        mm._current_model = MagicMock()
        mm._current_task_type = "universal"
        mm._unload_current_model()
        # Should not raise RuntimeError

def test_chat_panel_init_robustness():
    """Test ChatPanel initializes even with None db."""
    import tkinter as tk
    from src.ui.chat_panel import ChatPanel
    
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
