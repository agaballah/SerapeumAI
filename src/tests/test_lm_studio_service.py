# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch
import pytest
import requests
import json
import time
import os

# Mock llama_cpp during import of model_manager to avoid real library dependency
# We use patch.dict on sys.modules so imports of llama_cpp return a MagicMock
with patch.dict('sys.modules', {'llama_cpp': MagicMock()}):
    from src.infra.adapters.model_manager import ModelManager
    from src.infra.adapters.lm_studio_service import LMStudioService

class MockResponse:
    """Helper to mock requests.Response objects."""
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)
        self.reason = "OK" if status_code == 200 else "Error"
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")
            err.response = self
            raise err

    def iter_lines(self):
        # minimal mock for streaming tests
        return iter([])

@pytest.fixture
def mock_config():
    """Mock configuration manager with LM Studio section."""
    config = MagicMock()
    # Mock section retrieval
    config.get_section.return_value = {
        "enabled": True,
        "url": "http://127.0.0.1:1234",
        "autostart_server": False
    }
    return config

@pytest.fixture
def clean_model_manager():
    """Ensure ModelManager singleton is reset before each test."""
    ModelManager._instance = None
    mm = ModelManager()
    yield mm
    # Clean up after test
    ModelManager._instance = None

def test_model_manager_exposes_inference_lock(clean_model_manager):
    """Verify ModelManager exposes inference_lock on the active singleton path."""
    mm = clean_model_manager
    # We renamed new_inference_lock -> inference_lock in the previous step
    assert hasattr(mm, "inference_lock"), "ModelManager missing inference_lock"
    
    # Verify it is a threading.Lock
    import threading
    assert isinstance(mm.inference_lock, type(threading.Lock())), "inference_lock must be a threading.Lock instance"

def test_lm_studio_non_stream_falls_back_after_404(mock_config):
    """Verify LM Studio non-stream path falls back to OpenAI endpoint if /api/v1/chat fails."""
    
    with patch("requests.get") as mock_get, patch("requests.request") as mock_req:
        # 1. Mock _is_server_reachable (called during init)
        mock_get.return_value = MockResponse({}, status_code=200)

        svc = LMStudioService(mock_config)

        # 2. Mock payload for OpenAI compatibility fallback
        mock_openai_payload = {
            "choices": [{
                "message": {"role": "assistant", "content": "Fallback Content"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 15}
        }

        # 3. Define side effect to simulate 404 on native and 200 on fallback
        def mock_side_effect(method, url, **kwargs):
            if "/api/v1/chat" in url:
                # Native endpoint fails with 404
                resp = MockResponse({"error": "not found"}, status_code=404)
                resp.raise_for_status() # Trigger the catch block in chat()
            elif "/v1/chat/completions" in url:
                # OpenAI fallback succeeds
                return MockResponse(mock_openai_payload, status_code=200)
            return MockResponse({}, status_code=200)

        mock_req.side_effect = mock_side_effect

        msg = [{"role": "user", "content": "test"}]
        result = svc.chat(msg, stream=False)

        # Assert correct content was returned from fallback
        assert result["content"] == "Fallback Content"
        
        # Verify call order: native then fallback
        calls = [c.args[1] if (c.args and len(c.args) > 1) else c.kwargs.get("url") for c in mock_req.call_args_list]
        assert any(u and "/api/v1/chat" in u for u in calls)
        assert any(u and "/v1/chat/completions" in u for u in calls)

def test_normalization_prefers_message_content(mock_config):
    """Verify normalization logic prioritizes message.content."""
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse({}, status_code=200)
        svc = LMStudioService(mock_config)

    payload = {
        "choices": [{
            "message": {
                "content": "Primary Text",
                "reasoning_content": "Hidden Reasoning"
            }
        }]
    }
    # Test internal private normalization helper
    result = svc._openai_chat_to_normalized(payload, model="test-model")
    assert result["content"] == "Primary Text"

def test_normalization_uses_reasoning_content_when_content_empty(mock_config):
    """Verify normalization uses reasoning_content if content is empty or None."""
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse({}, status_code=200)
        svc = LMStudioService(mock_config)

    # Scen 1: Empty string content
    payload1 = {
        "choices": [{
            "message": {
                "content": "",
                "reasoning_content": "The reasoning is the answer"
            }
        }]
    }
    result1 = svc._openai_chat_to_normalized(payload1, model="test-model")
    assert result1["content"] == "The reasoning is the answer"
    assert "reasoning_content" in result1

    # Scen 2: Missing content field
    payload2 = {
        "choices": [{
            "message": {
                "reasoning_content": "Missing content fallback"
            }
        }]
    }
    result2 = svc._openai_chat_to_normalized(payload2, model="test-model")
    assert result2["content"] == "Missing content fallback"

def test_normalization_handles_blank_payload_safely(mock_config):
    """Verify normalization handles empty choices or blank payload without crashing."""
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse({}, status_code=200)
        svc = LMStudioService(mock_config)

    # Scen 1: Empty choices list
    payload1 = {"choices": []}
    result1 = svc._openai_chat_to_normalized(payload1, model="test-model")
    assert "content" not in result1 or result1["content"] == ""

    # Scen 2: Empty dict
    result2 = svc._openai_chat_to_normalized({}, model="test")
    assert result2["model"] == "test"
    assert "usage" in result2


def test_openai_only_mode_skips_native_chat(mock_config):
    """If only /v1/models is available, LM Studio chat should not hit /api/v1/chat first."""
    with patch("requests.get") as mock_get, patch("requests.request") as mock_req:
        def get_side_effect(url, **kwargs):
            if url.endswith("/api/v1/models"):
                return MockResponse({"error": "not found"}, status_code=404)
            if url.endswith("/v1/models"):
                return MockResponse({"data": [{"id": "qwen3.5-4b"}]}, status_code=200)
            return MockResponse({}, status_code=200)

        def req_side_effect(method, url, **kwargs):
            if url.endswith("/api/v1/chat") or url.endswith("/api/v1/models/load"):
                return MockResponse({"error": "not found"}, status_code=404)
            if url.endswith("/v1/models"):
                return MockResponse({"data": [{"id": "qwen3.5-4b"}]}, status_code=200)
            if url.endswith("/v1/chat/completions"):
                return MockResponse({
                    "choices": [{"message": {"role": "assistant", "content": "OpenAI-only OK"}}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
                }, status_code=200)
            raise AssertionError(f"Unexpected request URL: {url}")

        mock_get.side_effect = get_side_effect
        mock_req.side_effect = req_side_effect

        svc = LMStudioService(mock_config)
        result = svc.chat([{"role": "user", "content": "test"}], stream=False)

        assert result["content"] == "OpenAI-only OK"
        request_urls = [c.kwargs.get("url") for c in mock_req.call_args_list]
        assert any(url.endswith("/v1/chat/completions") for url in request_urls)
        native_chat_posts = [
            c for c in mock_req.call_args_list
            if c.kwargs.get("url", "").endswith("/api/v1/chat") and c.args and c.args[0] == "POST"
        ]
        native_load_posts = [
            c for c in mock_req.call_args_list
            if c.kwargs.get("url", "").endswith("/api/v1/models/load") and c.args and c.args[0] == "POST"
        ]
        assert not native_chat_posts
        assert not native_load_posts


def test_load_model_fails_fast_in_openai_only_mode(mock_config):
    """Model auto-load must fail early with a clear runtime-contract error in OpenAI-only mode."""
    with patch("requests.get") as mock_get:
        def get_side_effect(url, **kwargs):
            if url.endswith("/api/v1/models"):
                return MockResponse({"error": "not found"}, status_code=404)
            if url.endswith("/v1/models"):
                return MockResponse({"data": [{"id": "qwen3.5-4b"}]}, status_code=200)
            return MockResponse({}, status_code=200)

        mock_get.side_effect = get_side_effect
        svc = LMStudioService(mock_config)

        with pytest.raises(Exception) as exc:
            svc.load_model("qwen3.5-4b")

        assert "does not expose native model load/unload endpoints" in str(exc.value)


def test_native_chat_without_model_load_never_calls_models_load(mock_config):
    """If native chat exists but /api/v1/models/load is absent, SerapeumAI must skip auto-load and chat directly."""
    with patch("requests.get") as mock_get, patch("requests.request") as mock_req:
        def get_side_effect(url, **kwargs):
            if url.endswith("/api/v1/models"):
                return MockResponse({"data": [{"id": "qwen3.5-4b"}]}, status_code=200)
            if url.endswith("/v1/models"):
                return MockResponse({"error": "not found"}, status_code=404)
            return MockResponse({}, status_code=200)

        def req_side_effect(method, url, **kwargs):
            if url.endswith("/api/v1/chat") and method == "GET":
                return MockResponse({"error": "method not allowed"}, status_code=405)
            if url.endswith("/api/v1/models/load"):
                return MockResponse({"error": "not found"}, status_code=404)
            if url.endswith("/api/v1/chat"):
                return MockResponse({
                    "response_id": "resp_1",
                    "output": [{"type": "message", "content": "Native chat OK"}],
                    "stats": {"input_tokens": 4, "total_output_tokens": 3},
                }, status_code=200)
            raise AssertionError(f"Unexpected request URL: {url}")

        mock_get.side_effect = get_side_effect
        mock_req.side_effect = req_side_effect

        svc = LMStudioService(mock_config)
        result = svc.chat([{"role": "user", "content": "test"}], stream=False, model="qwen3.5-4b")

        assert result["content"] == "Native chat OK"
        request_urls = [c.kwargs.get("url") for c in mock_req.call_args_list]
        assert any(url.endswith("/api/v1/chat") for url in request_urls)
        runtime_calls = [c for c in mock_req.call_args_list if c.kwargs.get("url", "").endswith("/api/v1/models/load") and c.kwargs.get("json")]
        assert not runtime_calls


def test_resolve_openai_model_name_maps_publish_alias_to_exposed_model_id(mock_config):
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse({}, status_code=200)
        svc = LMStudioService(mock_config)

    svc._runtime_contract = {
        "connected": True,
        "native_rest": True,
        "native_chat": True,
        "native_model_management": False,
        "openai_compat": True,
        "mode": "native_chat_only",
        "message": "ok",
        "native_models": ["qwen2.5-coder-7b-instruct"],
        "openai_models": ["qwen/qwen2.5-coder-7b-instruct"],
    }

    assert svc._resolve_openai_model_name("qwen2.5-coder-7b-instruct") == "qwen/qwen2.5-coder-7b-instruct"


def test_openai_chat_400_retries_with_normalized_payload(mock_config):
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse({}, status_code=200)
        svc = LMStudioService(mock_config)

    svc._runtime_contract = {
        "connected": True,
        "native_rest": False,
        "native_chat": False,
        "native_model_management": False,
        "openai_compat": True,
        "mode": "openai_compat_only",
        "message": "ok",
        "native_models": [],
        "openai_models": ["qwen/qwen2.5-coder-7b-instruct"],
    }

    first = {"count": 0}

    def request_side_effect(method, path, **kwargs):
        assert method == "POST"
        assert path == "/v1/chat/completions"
        payload = kwargs.get("json_body") or {}
        first["count"] += 1
        if first["count"] == 1:
            err_resp = MockResponse({"error": "bad request"}, status_code=400)
            err = requests.exceptions.HTTPError("HTTP Error: 400")
            err.response = err_resp
            raise err
        assert payload["model"] == "qwen/qwen2.5-coder-7b-instruct"
        assert isinstance(payload["messages"][0]["content"], str)
        return MockResponse({
            "choices": [{"message": {"role": "assistant", "content": "Normalized OK"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        }, status_code=200)

    with patch.object(svc, "_request", side_effect=request_side_effect):
        result = svc.chat([
            {"role": "user", "content": [{"type": "text", "text": "Provide project scope summary"}]}
        ], stream=False, model="qwen2.5-coder-7b-instruct")

    assert result["content"] == "Normalized OK"
    assert first["count"] == 2
