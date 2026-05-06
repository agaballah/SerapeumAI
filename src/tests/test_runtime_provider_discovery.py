# -*- coding: utf-8 -*-
"""
Wave 1B-1 / Upgrade 3S: read-only runtime provider discovery.

These tests prove provider discovery is local/read-only and does not install,
start, stop, download, load models, mutate config, or send project data.
"""

from urllib import error
from unittest.mock import Mock, patch

from src.infra.services.runtime_provider_discovery import (
    LMStudioDiscoveryAdapter,
    LocalReviewOnlyDiscoveryAdapter,
    OllamaDiscoveryAdapter,
    OpenAICompatibleLocalDiscoveryAdapter,
    ProviderDiscoveryResult,
    RuntimeProviderDiscoveryRegistry,
    RuntimeProviderDiscoveryService,
    PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY,
    PROVIDER_MODE_LM_STUDIO_CLI_MANAGED,
    PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT,
    PROVIDER_MODE_OLLAMA_LOCAL,
    STATUS_DISABLED,
    STATUS_REACHABLE,
    STATUS_UNREACHABLE,
    STATUS_UNSUPPORTED,
    is_loopback_endpoint,
)


class _Response:
    def __init__(self, status=200, body=b""):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Config:
    def __init__(self, sections):
        self.sections = sections

    def get_section(self, name):
        return self.sections.get(name, {})


def _assert_no_side_effects(result):
    data = result.to_dict() if isinstance(result, ProviderDiscoveryResult) else result
    assert data["side_effects"] == {
        "internet_used": False,
        "install_attempted": False,
        "start_attempted": False,
        "stop_attempted": False,
        "download_attempted": False,
        "model_load_attempted": False,
        "model_unload_attempted": False,
        "config_mutated": False,
        "project_data_sent": False,
    }


def test_loopback_endpoint_detection_is_strict():
    assert is_loopback_endpoint("http://127.0.0.1:1234")
    assert is_loopback_endpoint("http://localhost:11434")
    assert not is_loopback_endpoint("https://api.openai.com")
    assert not is_loopback_endpoint("http://192.168.1.50:1234")


def test_local_review_only_mode_is_explicit_valid_disabled_provider():
    result = LocalReviewOnlyDiscoveryAdapter().discover()

    assert result.status == STATUS_DISABLED
    assert result.reason == "local_review_only_no_ai_mode"
    assert result.provider_mode == PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY
    assert result.provider_modes_supported == [PROVIDER_MODE_DISABLED_LOCAL_REVIEW_ONLY]
    assert result.details["valid_without_ai"] is True
    assert result.available is False
    assert result.listed_models == []
    _assert_no_side_effects(result)


def test_lm_studio_disabled_returns_disabled_without_http_probe():
    urlopen = Mock()
    adapter = LMStudioDiscoveryAdapter(enabled=False)

    with patch("src.infra.services.runtime_provider_discovery.request.urlopen", urlopen):
        result = adapter.discover()

    assert result.status == STATUS_DISABLED
    assert result.reason == "disabled_in_config"
    assert result.provider_mode == PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT
    assert PROVIDER_MODE_LM_STUDIO_CLI_MANAGED in result.provider_modes_supported
    assert urlopen.call_count == 0
    _assert_no_side_effects(result)


def test_lm_studio_reachable_uses_get_v1_models_only():
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["timeout"] = timeout
        return _Response(200)

    adapter = LMStudioDiscoveryAdapter(endpoint="http://127.0.0.1:1234", timeout_s=1.25)

    with patch("src.infra.services.runtime_provider_discovery.request.urlopen", fake_urlopen):
        result = adapter.discover()

    assert result.status == STATUS_REACHABLE
    assert result.reason == "probe_ok"
    assert captured == {
        "url": "http://127.0.0.1:1234/v1/models",
        "method": "GET",
        "timeout": 1.25,
    }
    assert result.provider_mode == PROVIDER_MODE_LM_STUDIO_MANUAL_OPENAI_COMPAT
    assert "model_listing" in result.capabilities
    _assert_no_side_effects(result)


def test_lm_studio_reachable_lists_openai_compatible_models_read_only():
    body = b'{"data":[{"id":"qwen2.5-coder-7b-instruct","object":"model"}]}'

    def fake_urlopen(req, timeout):
        return _Response(200, body=body)

    adapter = LMStudioDiscoveryAdapter(endpoint="http://127.0.0.1:1234", timeout_s=1.25)

    with patch("src.infra.services.runtime_provider_discovery.request.urlopen", fake_urlopen):
        result = adapter.discover()

    assert result.status == STATUS_REACHABLE
    assert result.listed_models == [
        {
            "model_id": "qwen2.5-coder-7b-instruct",
            "display_name": "qwen2.5-coder-7b-instruct",
            "source": "lm_studio",
            "raw_type": "model",
        }
    ]
    _assert_no_side_effects(result)


def test_lm_studio_unreachable_returns_structured_status():
    adapter = LMStudioDiscoveryAdapter(endpoint="http://127.0.0.1:1234")

    with patch(
        "src.infra.services.runtime_provider_discovery.request.urlopen",
        side_effect=error.URLError("offline"),
    ):
        result = adapter.discover()

    assert result.status == STATUS_UNREACHABLE
    assert result.reason.startswith("unreachable:")
    _assert_no_side_effects(result)


def test_ollama_reachable_uses_get_api_tags_only():
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["timeout"] = timeout
        return _Response(200)

    adapter = OllamaDiscoveryAdapter(endpoint="http://127.0.0.1:11434", timeout_s=1.0)

    with patch("src.infra.services.runtime_provider_discovery.request.urlopen", fake_urlopen):
        result = adapter.discover()

    assert result.status == STATUS_REACHABLE
    assert captured == {
        "url": "http://127.0.0.1:11434/api/tags",
        "method": "GET",
        "timeout": 1.0,
    }
    assert result.provider_mode == PROVIDER_MODE_OLLAMA_LOCAL
    assert "ollama" in result.capabilities
    _assert_no_side_effects(result)


def test_ollama_reachable_lists_local_models_read_only():
    body = b'{"models":[{"name":"llama3.1:8b","size":123,"modified_at":"2026-01-01T00:00:00Z"}]}'

    def fake_urlopen(req, timeout):
        return _Response(200, body=body)

    adapter = OllamaDiscoveryAdapter(endpoint="http://127.0.0.1:11434", timeout_s=1.0)

    with patch("src.infra.services.runtime_provider_discovery.request.urlopen", fake_urlopen):
        result = adapter.discover()

    assert result.status == STATUS_REACHABLE
    assert result.listed_models == [
        {
            "model_id": "llama3.1:8b",
            "display_name": "llama3.1:8b",
            "source": "ollama",
            "size": 123,
            "modified_at": "2026-01-01T00:00:00Z",
        }
    ]
    _assert_no_side_effects(result)


def test_non_local_openai_compatible_endpoint_is_blocked_without_probe():
    urlopen = Mock()
    adapter = OpenAICompatibleLocalDiscoveryAdapter(
        endpoint="https://api.openai.com",
        enabled=True,
    )

    with patch("src.infra.services.runtime_provider_discovery.request.urlopen", urlopen):
        result = adapter.discover()

    assert result.status == STATUS_UNSUPPORTED
    assert result.reason == "non_local_endpoint_blocked"
    assert urlopen.call_count == 0
    _assert_no_side_effects(result)


def test_registry_discovers_in_deterministic_order():
    registry = RuntimeProviderDiscoveryRegistry(
        [
            OllamaDiscoveryAdapter(enabled=False),
            LMStudioDiscoveryAdapter(enabled=False),
        ]
    )

    results = registry.discover()

    assert [item.provider_name for item in results] == ["lm_studio", "ollama"]


def test_from_config_includes_local_review_lm_studio_ollama_and_configured_openai_local():
    config = _Config(
        {
            "lm_studio": {"enabled": False, "url": "http://127.0.0.1:1234"},
            "ollama": {"enabled": False, "url": "http://127.0.0.1:11434"},
            "openai_compatible": {
                "enabled": True,
                "url": "http://127.0.0.1:8000",
                "name": "local_openai_server",
            },
        }
    )

    registry = RuntimeProviderDiscoveryRegistry.from_config(config)
    names = [adapter.name for adapter in registry.adapters]

    assert names == ["local_review_only", "lm_studio", "ollama", "local_openai_server"]


def test_service_returns_dicts_with_required_status_fields():
    config = _Config(
        {
            "lm_studio": {"enabled": False, "url": "http://127.0.0.1:1234"},
            "ollama": {"enabled": False, "url": "http://127.0.0.1:11434"},
        }
    )

    service = RuntimeProviderDiscoveryService(config)
    rows = service.discover_providers()

    assert rows
    for row in rows:
        assert set(
            [
                "provider_name",
                "provider_type",
                "endpoint",
                "status",
                "reason",
                "capabilities",
                "side_effects",
                "details",
                "available",
                "provider_mode",
                "provider_modes_supported",
                "listed_models",
            ]
        ).issubset(row.keys())
        _assert_no_side_effects(row)
