from src.infra.adapters.model_router import ModelRouter


class FakeConfig:
    def __init__(self, values):
        self.values = dict(values)

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeLMS:
    def __init__(self):
        self.models = [
            {"id": "qwen2.5-coder-7b-instruct"},
            {"id": "qwen/qwen3.5-9b"},
            {"id": "nvidia/nemotron-3-nano-4b"},
        ]

    def list_models(self):
        return list(self.models)

    def get_status(self):
        return {"loaded": True, "model": "qwen/qwen3.5-9b"}


class FakeDB:
    def execute(self, *args, **kwargs):
        class Cursor:
            def fetchall(self):
                return []

            def fetchone(self):
                return None

        return Cursor()

    def commit(self):
        pass


def _router(values):
    return ModelRouter(FakeDB(), FakeLMS(), config=FakeConfig(values))


def test_analysis_runtime_manager_selection_wins_before_publish_default():
    router = _router({"models.analysis.model": "qwen/qwen3.5-9b"})

    chosen = router.get_best_model("analysis")

    assert chosen == "qwen/qwen3.5-9b"


def test_chat_runtime_manager_selection_wins_for_chat_family():
    router = _router({"models.chat.model": "nvidia/nemotron-3-nano-4b"})

    chosen = router.get_best_model("chat")

    assert chosen == "nvidia/nemotron-3-nano-4b"


def test_explicit_config_wins_even_when_cache_contains_old_publish_default():
    router = _router({"models.analysis.model": "qwen/qwen3.5-9b"})
    router.cache["analysis"] = ("qwen2.5-coder-7b-instruct", 9999999999)

    chosen = router.get_best_model("analysis")

    assert chosen == "qwen/qwen3.5-9b"


def test_auto_can_still_fall_back_to_publish_default_when_available():
    router = _router({"models.analysis.model": "auto"})

    chosen = router.get_best_model("analysis")

    assert chosen == "qwen2.5-coder-7b-instruct"
