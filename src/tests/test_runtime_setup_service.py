from unittest.mock import patch

from src.infra.services.runtime_setup_service import (
    LocalRuntimeSetupService,
    STATUS_CHAT_MODEL_MISSING,
    STATUS_CLI_NOT_AVAILABLE,
    STATUS_EMBEDDING_RUNTIME_NOT_READY,
    STATUS_LMSTUDIO_NOT_INSTALLED,
    STATUS_MODEL_NOT_LOADED,
    STATUS_READY,
    STATUS_SERVER_NOT_RUNNING,
)


class DummyConfig:
    def __init__(self, values=None):
        self.values = values or {}
        self.saved_scopes = []

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value, scope="local"):
        self.values[key] = value

    def save(self, scope="local"):
        self.saved_scopes.append(scope)
        return "dummy-config.yaml"


class DummyLMReady:
    def verify_chat_runtime(self, target_model=None, require_stateful=False):
        return {"connected": True, "resolved_model": target_model}


def _downloaded_model(model_key, display_name=None):
    return {
        "model_key": model_key,
        "display_name": display_name or model_key,
        "identifier": model_key,
        "type": "llm",
        "path": model_key,
    }


def _loaded_model(model_key, identifier=None):
    return {
        "model_key": model_key,
        "display_name": model_key,
        "identifier": identifier or model_key,
        "type": "llm",
        "status": "idle",
    }


def test_detect_state_reports_not_installed_when_no_app_or_cli():
    svc = LocalRuntimeSetupService(DummyConfig())
    with patch.object(svc, '_find_lmstudio_app', return_value=None), patch.object(svc, '_find_lms_cli', return_value=None):
        state = svc.detect_state()
    assert state['status'] == STATUS_LMSTUDIO_NOT_INSTALLED


def test_detect_state_reports_cli_missing_when_app_exists():
    svc = LocalRuntimeSetupService(DummyConfig())
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), patch.object(svc, '_find_lms_cli', return_value=None):
        state = svc.detect_state()
    assert state['status'] == STATUS_CLI_NOT_AVAILABLE
    assert 'bootstrap the CLI' in state['message']


def test_detect_state_reports_server_not_running_before_model_checks():
    svc = LocalRuntimeSetupService(DummyConfig())
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), \
         patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, '_list_local_models', return_value=[]), \
         patch.object(svc, '_list_loaded_models', return_value=[]), \
         patch.object(svc, '_server_running', return_value=False):
        state = svc.detect_state()
    assert state['status'] == STATUS_SERVER_NOT_RUNNING


def test_detect_state_reports_chat_model_missing_when_no_downloaded_models():
    svc = LocalRuntimeSetupService(DummyConfig())
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), \
         patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, '_server_running', return_value=True), \
         patch.object(svc, '_list_local_models', return_value=[]), \
         patch.object(svc, '_list_loaded_models', return_value=[]):
        state = svc.detect_state()
    assert state['status'] == STATUS_CHAT_MODEL_MISSING
    assert 'publish generative model' in state['message']


def test_detect_state_reports_embedding_runtime_not_ready_when_local_embedding_missing():
    cfg = DummyConfig({
        'models.chat.model': 'qwen/qwen3.5-4b',
        'models.analysis.model': 'qwen/qwen2.5-coder-7b-instruct',
    })
    svc = LocalRuntimeSetupService(cfg)
    downloaded = [
        _downloaded_model('qwen/qwen2.5-coder-7b-instruct'),
    ]
    loaded = [
        _loaded_model('qwen/qwen2.5-coder-7b-instruct', 'serapeum-analysis'),
    ]
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), \
         patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, '_server_running', return_value=True), \
         patch.object(svc, '_list_local_models', return_value=downloaded), \
         patch.object(svc, '_list_loaded_models', return_value=loaded), \
         patch.object(svc, '_embedding_model_available', return_value=False):
        state = svc.detect_state()
    assert state['status'] == STATUS_EMBEDDING_RUNTIME_NOT_READY


def test_detect_state_reports_model_not_loaded_when_selected_models_are_not_active():
    cfg = DummyConfig({
        'models.chat.model': 'qwen/qwen3.5-4b',
        'models.analysis.model': 'qwen/qwen2.5-coder-7b-instruct',
    })
    svc = LocalRuntimeSetupService(cfg)
    downloaded = [
        _downloaded_model('qwen/qwen2.5-coder-7b-instruct'),
    ]
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), \
         patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, '_server_running', return_value=True), \
         patch.object(svc, '_list_local_models', return_value=downloaded), \
         patch.object(svc, '_list_loaded_models', return_value=[]), \
         patch.object(svc, '_embedding_model_available', return_value=True):
        state = svc.detect_state()
    assert state['status'] == STATUS_MODEL_NOT_LOADED


def test_detect_state_reports_ready_when_selected_models_are_downloaded_and_loaded():
    cfg = DummyConfig({
        'models.chat.model': 'qwen/qwen3.5-4b',
        'models.analysis.model': 'qwen/qwen2.5-coder-7b-instruct',
    })
    svc = LocalRuntimeSetupService(cfg)
    downloaded = [
        _downloaded_model('qwen/qwen2.5-coder-7b-instruct'),
    ]
    loaded = [
        _loaded_model('qwen/qwen2.5-coder-7b-instruct', 'serapeum-analysis'),
    ]
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), \
         patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, '_server_running', return_value=True), \
         patch.object(svc, '_list_local_models', return_value=downloaded), \
         patch.object(svc, '_list_loaded_models', return_value=loaded), \
         patch.object(svc, '_embedding_model_available', return_value=True):
        state = svc.detect_state()
    assert state['status'] == STATUS_READY
    assert state['inventory']['selected_models']['analysis'] == 'qwen/qwen2.5-coder-7b-instruct'


def test_set_selected_models_persists_local_selection():
    cfg = DummyConfig()
    svc = LocalRuntimeSetupService(cfg)
    with patch.object(svc, 'detect_state', return_value={'status': STATUS_CHAT_MODEL_MISSING, 'message': 'Select models', 'inventory': {}}):
        result = svc.set_selected_models(chat_model='qwen/qwen3.5-4b', analysis_model='qwen/qwen2.5-coder-7b-instruct')
    assert cfg.values['models.chat.model'] == 'qwen2.5-coder-7b-instruct'
    assert cfg.values['models.analysis.model'] == 'qwen2.5-coder-7b-instruct'
    assert cfg.saved_scopes == ['local']
    assert result['status'] == STATUS_CHAT_MODEL_MISSING


def test_get_required_models_publish_lock_uses_single_generative_model():
    svc = LocalRuntimeSetupService(DummyConfig({'models.chat.model': 'qwen/qwen3.5-4b'}))
    required = svc.get_required_models()
    assert required['chat'] == 'qwen2.5-coder-7b-instruct'
    assert required['analysis'] == 'qwen2.5-coder-7b-instruct'


def test_detect_state_reports_ready_when_single_publish_model_satisfies_both_roles():
    svc = LocalRuntimeSetupService(DummyConfig())
    downloaded = [_downloaded_model('qwen/qwen2.5-coder-7b-instruct')]
    loaded = [_loaded_model('qwen/qwen2.5-coder-7b-instruct', 'serapeum-analysis')]
    with patch.object(svc, '_find_lmstudio_app', return_value='C:/LM Studio/LM Studio.exe'), \
         patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, '_server_running', return_value=True), \
         patch.object(svc, '_list_local_models', return_value=downloaded), \
         patch.object(svc, '_list_loaded_models', return_value=loaded), \
         patch.object(svc, '_embedding_model_available', return_value=True):
        state = svc.detect_state()
    assert state['status'] == STATUS_READY
    assert state['inventory']['selected_models']['chat'] == 'qwen/qwen2.5-coder-7b-instruct'
    assert state['inventory']['selected_models']['analysis'] == 'qwen/qwen2.5-coder-7b-instruct'
    assert state['inventory']['loaded_roles']['chat'] is True
    assert state['inventory']['loaded_roles']['analysis'] is True


def test_load_model_for_role_uses_cli_identifier_and_marks_session_loaded():
    cfg = DummyConfig({'models.analysis.model': 'qwen/qwen2.5-coder-7b-instruct'})
    svc = LocalRuntimeSetupService(cfg)
    downloaded = [_downloaded_model('qwen/qwen2.5-coder-7b-instruct')]
    with patch.object(svc, 'get_runtime_inventory', return_value={'server_running': True, 'selected_models': {'analysis': 'qwen/qwen2.5-coder-7b-instruct'}, 'loaded_roles': {'analysis': False, 'chat': False}}), \
         patch.object(svc, '_list_local_models', return_value=downloaded), \
         patch.object(svc, '_run_cli') as run_cli, \
         patch.object(svc, 'detect_state', return_value={'status': STATUS_MODEL_NOT_LOADED, 'message': 'Load the selected session model(s).', 'inventory': {'server_running': True}}):
        run_cli.return_value = type('R', (), {'returncode': 0, 'stdout': 'ok', 'stderr': ''})()
        svc.load_model_for_role('analysis')
    run_cli.assert_called_once()
    called_args = run_cli.call_args[0][0]
    assert called_args[:2] == ['load', 'qwen/qwen2.5-coder-7b-instruct']
    assert '--identifier' in called_args
    assert 'serapeum-analysis' in called_args


def test_cleanup_unloads_app_loaded_models_and_stops_only_app_started_server():
    svc = LocalRuntimeSetupService(DummyConfig())
    svc._role_to_loaded_identifier = {'analysis': 'serapeum-analysis', 'chat': 'serapeum-chat'}
    svc._loaded_models_by_app = {'serapeum-analysis', 'serapeum-chat'}
    svc._server_started_by_app = True
    with patch.object(svc, '_find_lms_cli', return_value='C:/LM Studio/lms.exe'), \
         patch.object(svc, 'unload_role_model', return_value={'status': STATUS_MODEL_NOT_LOADED, 'message': 'done'}) as unload_role, \
         patch.object(svc, '_run_cli') as run_cli:
        run_cli.return_value = type('R', (), {'returncode': 0, 'stdout': 'ok', 'stderr': ''})()
        svc.cleanup_provisioned_runtime()
    assert unload_role.call_count == 2
    run_cli.assert_called_once_with(['server', 'stop'], timeout_s=120)
