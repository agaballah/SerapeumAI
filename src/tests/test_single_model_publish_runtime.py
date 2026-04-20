from types import SimpleNamespace

from src.infra.adapters.model_router import ModelRouter
from src.infra.adapters.llm_service import LLMService


def _cfg():
    values = {
        'models.auto_select.cache_ttl_s': 3600,
        'models.auto_select.enabled': False,
        'models.auto_select.min_quality': 0.5,
        'models.universal.model': 'auto',
    }
    return SimpleNamespace(get=lambda key, default=None: values.get(key, default))


class DummyDB:
    def execute(self, *args, **kwargs):
        raise RuntimeError("db access not expected in publish-lock tests")


class DummyLMS:
    def __init__(self, installed=None):
        self.installed = installed or []

    def list_models(self):
        return [{"id": model_id} for model_id in self.installed]

    def get_status(self):
        return {"model": self.installed[0] if self.installed else None}


def test_model_router_uses_single_publish_model_for_completion_tasks():
    lms = DummyLMS(installed=['qwen/qwen2.5-coder-7b-instruct'])
    router = ModelRouter(DummyDB(), lms, config=_cfg())

    analysis = router.get_best_model('analysis')
    universal = router.get_best_model('universal')
    reasoning = router.get_best_model('reasoning')

    assert analysis == 'qwen/qwen2.5-coder-7b-instruct'
    assert universal == 'qwen/qwen2.5-coder-7b-instruct'
    assert reasoning == 'qwen/qwen2.5-coder-7b-instruct'


def test_model_router_keeps_vision_tasks_outside_publish_completion_lock():
    lms = DummyLMS(installed=['qwen/qwen2.5-coder-7b-instruct', 'qwen2-vl-7b-instruct'])
    router = ModelRouter(DummyDB(), lms, config=_cfg())

    assert router._publish_locked_model('vision') is None


class DummyRouter:
    def get_best_model(self, task_type):
        return 'qwen2.5-coder-7b-instruct'

    def record_usage(self, **kwargs):
        return None


class DummyLMStudio:
    def verify_chat_runtime(self, target_model=None, require_stateful=False):
        return {'resolved_model': target_model}

    def get_status(self):
        return {'loaded': True, 'model': 'qwen/qwen2.5-coder-7b-instruct'}

    def chat(self, **kwargs):
        return {'choices': [{'message': {'content': 'ok'}}], 'used_model': kwargs.get('model')}


def test_llm_service_accepts_active_model_alias_for_single_publish_model():
    llm = LLMService.__new__(LLMService)
    llm.use_lm_studio = True
    llm.router = DummyRouter()
    llm.lm_studio = DummyLMStudio()

    response = llm._chat_lm_studio(
        messages=[{'role': 'user', 'content': 'scope?'}],
        task_type='universal',
        temperature=0.1,
        top_p=0.9,
        max_tokens=128,
        stream=False,
    )

    assert response['used_model'] == 'qwen2.5-coder-7b-instruct'
