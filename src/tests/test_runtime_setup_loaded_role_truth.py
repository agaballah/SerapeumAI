from src.infra.services.runtime_setup_service import LocalRuntimeSetupService


class FakeConfig:
    def get(self, key, default=None):
        return default


def test_loaded_roles_reject_stale_role_identifier_for_different_model():
    service = LocalRuntimeSetupService(FakeConfig())

    selected = {
        "analysis": "qwen/qwen3.5-9b",
        "chat": "qwen/qwen3.5-9b",
    }
    loaded = [
        {
            "identifier": "serapeum-analysis",
            "model_key": "qwen2.5-coder-7b-instruct",
        }
    ]

    roles = service._loaded_roles(selected, loaded)

    assert roles["analysis"] is False
    assert roles["chat"] is False


def test_loaded_selected_model_can_satisfy_both_roles_when_roles_share_model():
    service = LocalRuntimeSetupService(FakeConfig())

    selected = {
        "analysis": "qwen/qwen3.5-9b",
        "chat": "qwen/qwen3.5-9b",
    }
    loaded = [
        {
            "identifier": "serapeum-analysis",
            "model_key": "qwen/qwen3.5-9b",
        }
    ]

    roles = service._loaded_roles(selected, loaded)

    assert roles["analysis"] is True
    assert roles["chat"] is True


def test_loaded_role_identifier_satisfies_role_when_it_points_to_selected_model():
    service = LocalRuntimeSetupService(FakeConfig())

    selected = {
        "analysis": "nvidia/nemotron-3-nano-4b",
        "chat": "qwen/qwen3.5-9b",
    }
    loaded = [
        {
            "identifier": "serapeum-analysis",
            "model_key": "nvidia/nemotron-3-nano-4b",
        },
        {
            "identifier": "serapeum-chat",
            "model_key": "qwen/qwen3.5-9b",
        },
    ]

    roles = service._loaded_roles(selected, loaded)

    assert roles["analysis"] is True
    assert roles["chat"] is True


def test_unload_session_models_attempts_canonical_role_identifiers(monkeypatch):
    service = LocalRuntimeSetupService(FakeConfig())
    called = []

    def fake_unload(role, on_status=None):
        called.append(role)
        return {}

    monkeypatch.setattr(service, "unload_role_model", fake_unload)
    monkeypatch.setattr(
        service,
        "detect_state",
        lambda: {
            "status": "MODEL_NOT_LOADED",
            "message": "test",
            "inventory": {},
        },
    )
    monkeypatch.setattr(service, "_emit", lambda callback, status, message, **extra: {"status": status, "message": message, **extra})

    out = service.unload_session_models()

    assert called == ["analysis", "chat"]
    assert out["phase"] == "session_models_unloaded"
