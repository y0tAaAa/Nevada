"""
Переключение провайдера модели через .env: Groq / NVIDIA NIM / свой endpoint.
Проверяется на временных .env-файлах, не трогая рабочий.
"""
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT, Checker
setup_paths()
import os
os.chdir(PROJECT_ROOT)

import shutil
import tempfile

check = Checker()

ENV_PATH = PROJECT_ROOT / ".env"
BACKUP = None


def load_config_with_env(content: str):
    """Подменяет .env на время проверки и возвращает свежий Config"""
    ENV_PATH.write_text(content, encoding="utf-8")
    # Config читает .env при определении класса — нужен повторный импорт
    for name in [m for m in sys.modules if m == "config"]:
        del sys.modules[name]
    # Чистим переменные, чтобы не мешали
    for var in ("NEVADA_PROVIDER", "NEVADA_API_BASE", "NEVADA_MODEL",
                "NEVADA_API_KEY", "NVIDIA_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(var, None)
    from config import Config
    return Config()


try:
    if ENV_PATH.exists():
        BACKUP = ENV_PATH.read_text(encoding="utf-8")

    print("=== 1. Groq по умолчанию ===")
    cfg = load_config_with_env("GROQ_API_KEY=gsk_dummy\n")
    check("провайдер groq", cfg.provider == "groq", f"got={cfg.provider}")
    check("адрес Groq", cfg.api_base == "https://api.groq.com/openai/v1", f"got={cfg.api_base}")
    check("модель Groq по умолчанию", cfg.model == "llama-3.3-70b-versatile", f"got={cfg.model}")
    check("ключ подхвачен", cfg.groq_api_key == "gsk_dummy")

    print("\n=== 2. Переключение на NVIDIA одной строкой ===")
    cfg = load_config_with_env("NEVADA_PROVIDER=nvidia\nNVIDIA_API_KEY=nvapi-dummy\n")
    check("провайдер nvidia", cfg.provider == "nvidia", f"got={cfg.provider}")
    check("адрес NVIDIA NIM", cfg.api_base == "https://integrate.api.nvidia.com/v1",
          f"got={cfg.api_base}")
    check("модель NVIDIA по умолчанию", cfg.model == "meta/llama-3.3-70b-instruct",
          f"got={cfg.model}")
    check("ключ NVIDIA подхвачен", cfg.groq_api_key == "nvapi-dummy")

    print("\n=== 3. Свой OpenAI-совместимый endpoint (например, локальная Ollama) ===")
    cfg = load_config_with_env(
        "NEVADA_API_BASE=http://localhost:11434/v1\n"
        "NEVADA_MODEL=qwen2.5:7b\n"
        "NEVADA_API_KEY=local\n"
    )
    check("свой адрес применён", cfg.api_base == "http://localhost:11434/v1", f"got={cfg.api_base}")
    check("своя модель применена", cfg.model == "qwen2.5:7b", f"got={cfg.model}")

    print("\n=== 4. Общий NEVADA_API_KEY работает для любого провайдера ===")
    cfg = load_config_with_env("NEVADA_PROVIDER=nvidia\nNEVADA_API_KEY=universal\n")
    check("общий ключ подхвачен", cfg.groq_api_key == "universal", f"got={cfg.groq_api_key}")

    print("\n=== 5. Валидация ===")
    cfg = load_config_with_env("NEVADA_PROVIDER=nvidia\n")
    check("без ключа validate() = False", cfg.validate() is False)

    cfg = load_config_with_env("NEVADA_PROVIDER=nvidia\nNVIDIA_API_KEY=k\n")
    check("с ключом validate() = True", cfg.validate() is True)

    # Модель от другого провайдера — предупреждение, но не отказ
    cfg = load_config_with_env(
        "NEVADA_PROVIDER=nvidia\nNVIDIA_API_KEY=k\nNEVADA_MODEL=llama-3.3-70b-versatile\n")
    check("несовпадение модели не блокирует запуск", cfg.validate() is True)

    print("\n=== 6. Клиент агента получает нужный адрес ===")
    import types
    fake_openai = types.ModuleType("openai")
    captured = {}

    class _Client:
        def __init__(self, api_key=None, base_url=None, **kw):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = None

    fake_openai.OpenAI = _Client
    fake_openai.AuthenticationError = type("AuthenticationError", (Exception,), {})
    fake_openai.APIError = type("APIError", (Exception,), {})
    sys.modules["openai"] = fake_openai

    load_config_with_env("NEVADA_PROVIDER=nvidia\nNVIDIA_API_KEY=nvapi-xyz\n")
    for name in [m for m in list(sys.modules) if m.startswith("agent")]:
        del sys.modules[name]
    from agent.loop import AgentLoop

    class _Mem:
        def get_recent(self, n=10): return []
        def save(self, u, a): pass

    AgentLoop(_Mem(), tool_registry=None)
    check("AgentLoop использует адрес NVIDIA",
          captured.get("base_url") == "https://integrate.api.nvidia.com/v1",
          f"got={captured.get('base_url')}")
    check("AgentLoop использует ключ NVIDIA", captured.get("api_key") == "nvapi-xyz",
          f"got={captured.get('api_key')}")

finally:
    # Возвращаем рабочий .env на место
    if BACKUP is not None:
        ENV_PATH.write_text(BACKUP, encoding="utf-8")
    elif ENV_PATH.exists():
        ENV_PATH.unlink()

sys.exit(check.finish())
