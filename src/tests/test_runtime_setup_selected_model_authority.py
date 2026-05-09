from src.infra.services.runtime_setup_service import LocalRuntimeSetupService


class FakeConfig:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value, scope=None):
        self.values[key] = value

    def save(self, scope=None):
        self.values["saved_scope"] = scope


def _downloaded_models():
    return [
        {
            "model_key": "qwen2.5-coder-7b-instruct",
            "display_name": "Qwen2.5 Coder 7B Instruct",
            "identifier": "qwen2.5-coder-7b-instruct",
            "type": "llm",
        },
        {
            "model_key": "qwen/qwen3.5-9b",
            "display_name": "Qwen3.5 9B",
            "identifier": "qwen/qwen3.5-9b",
            "type": "llm",
        },
        {
            "model_key": "nvidia/nemotron-3-nano-4b",
            "display_name": "Nemotron 3 Nano 4B",
            "identifier": "nvidia/nemotron-3-nano-4b",
            "type": "llm",
        },
    ]


def test_selected_models_use_explicit_runtime_manager_selection_before_publish_default():
    config = FakeConfig()
    config.values["models.chat.model"] = "qwen/qwen3.5-9b"
    config.values["models.analysis.model"] = "nvidia/nemotron-3-nano-4b"

    service = LocalRuntimeSetupService(config)

    selected = service._selected_models(_downloaded_models())

    assert selected["chat"] == "qwen/qwen3.5-9b"
    assert selected["analysis"] == "nvidia/nemotron-3-nano-4b"


def test_set_selected_models_persists_user_choice_without_coercing_to_publish_default(monkeypatch):
    config = FakeConfig()
    service = LocalRuntimeSetupService(config)

    monkeypatch.setattr(
        service,
        "detect_state",
        lambda: {
            "status": "MODEL_NOT_LOADED",
            "message": "test",
            "inventory": {},
        },
    )

    service.set_selected_models(
        chat_model="qwen/qwen3.5-9b",
        analysis_model="nvidia/nemotron-3-nano-4b",
    )

    assert config.values["models.chat.model"] == "qwen/qwen3.5-9b"
    assert config.values["models.analysis.model"] == "nvidia/nemotron-3-nano-4b"
    assert config.values["saved_scope"] == "local"


def test_auto_selection_can_still_fall_back_to_publish_model_when_available():
    config = FakeConfig()
    config.values["models.chat.model"] = "auto"
    config.values["models.analysis.model"] = "auto"

    service = LocalRuntimeSetupService(config)

    selected = service._selected_models(_downloaded_models())

    assert selected["chat"] == "qwen2.5-coder-7b-instruct"
    assert selected["analysis"] == "qwen2.5-coder-7b-instruct"
