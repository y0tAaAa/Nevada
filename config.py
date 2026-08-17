"""
Конфигурация Nevada — загружает параметры из .env
"""

from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os
import sys


def _base_dir() -> Path:
    """
    Папка, где лежат .env и база данных.

    В обычном запуске — корень проекта. В собранном .exe модули лежат внутри
    _internal, поэтому пути нужно считать от самого исполняемого файла,
    иначе приложение не найдёт .env, который пользователь положил рядом с exe.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


BASE_DIR = _base_dir()


# Известные OpenAI-совместимые провайдеры: адрес и модель по умолчанию.
# Свой вариант задаётся через NEVADA_API_BASE и NEVADA_MODEL.
PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
}

PROVIDER_DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "nvidia": "meta/llama-3.3-70b-instruct",
}


@dataclass
class Config:
    """Настройки приложения Nevada"""
    
    # Загружаем .env файл
    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Провайдер модели. Любой OpenAI-совместимый API: Groq, NVIDIA NIM и т.п.
    # Переключение — только через .env, код менять не нужно.
    provider: str = os.getenv("NEVADA_PROVIDER", "groq").strip().lower()

    # Ключ: сначала смотрим общий NEVADA_API_KEY, потом ключ конкретного провайдера
    groq_api_key: str = (
        os.getenv("NEVADA_API_KEY", "")
        or os.getenv("NVIDIA_API_KEY", "")
        or os.getenv("GROQ_API_KEY", "")
    )

    model: str = os.getenv("NEVADA_MODEL", "") or PROVIDER_DEFAULT_MODELS.get(
        os.getenv("NEVADA_PROVIDER", "groq").strip().lower(), "llama-3.3-70b-versatile"
    )

    api_base: str = os.getenv("NEVADA_API_BASE", "") or PROVIDER_BASE_URLS.get(
        os.getenv("NEVADA_PROVIDER", "groq").strip().lower(),
        "https://api.groq.com/openai/v1",
    )
    
    # Приложение
    system_name: str = "Nevada"
    language: str = os.getenv("NEVADA_LANGUAGE", "ru")
    
    # Горячие клавиши
    hotkey: str = os.getenv("NEVADA_HOTKEY", "ctrl+shift+space")
    
    # Автозапуск
    autostart: bool = os.getenv("NEVADA_AUTOSTART", "true").lower() == "true"
    
    # База данных
    db_path: Path = BASE_DIR / "nevada.db"
    
    # Цвета — тёмная индиго-тема: компоновка с градиентным «hero»,
    # крупным приветствием и мягкими карточками
    BG_WINDOW = "#0f111a"    # основной фон окна
    BG_ALT = "#141726"       # боковая панель
    CARD = "#181c2e"         # поверхность карточек/панелей
    BG_INPUT = "#1e2338"     # поля ввода
    BG_MSG_USER = "#4f5bd5"  # индиго-пузырь пользователя
    BG_MSG_NEV = "#1e2338"   # пузырь ассистента
    TEXT_PRIMARY = "#e6e9f5"
    TEXT_MUTED = "#8b92b0"
    INK = "#f5f6fd"          # заголовки
    ACCENT = "#7c8cf8"       # индиго-акцент
    ACCENT_DARK = "#5b6ae0"
    ACCENT_2 = "#c4b5fd"     # сиреневый вторичный
    BORDER = "#2a3050"
    DANGER = "#f87171"
    CODE_BG = "#0c0e18"      # фон блоков вывода инструментов

    # Градиент «hero» как на референсе (индиго → сиренево-розовый)
    HERO_FROM = "#3b4b9e"
    HERO_MID = "#5566c4"
    HERO_TO = "#8b7bc4"

    # Типографика
    FONT_FAMILY = "Segoe UI Variable, Bahnschrift, Segoe UI, sans-serif"
    
    def validate(self) -> bool:
        """Проверяет обязательные настройки"""
        if not self.groq_api_key:
            expected = {
                "groq": "GROQ_API_KEY",
                "nvidia": "NVIDIA_API_KEY",
            }.get(self.provider, "NEVADA_API_KEY")
            print(f"⚠️  Ключ API не установлен в .env (ожидается {expected} или NEVADA_API_KEY)")
            return False

        # У NVIDIA идентификаторы моделей с namespace (meta/llama-3.3-70b-instruct),
        # у Groq — без. Частая ошибка при переключении провайдера: забыть сменить модель.
        if self.provider == "nvidia" and "/" not in self.model:
            print(
                f"⚠️  Провайдер nvidia, но модель «{self.model}» похожа на имя Groq. "
                "У NVIDIA идентификаторы вида meta/llama-3.3-70b-instruct — "
                "поправьте NEVADA_MODEL в .env"
            )
        elif self.provider == "groq" and "/" in self.model and not self.model.startswith("openai/"):
            print(
                f"⚠️  Провайдер groq, но модель «{self.model}» похожа на имя NVIDIA. "
                "Проверьте NEVADA_MODEL в .env"
            )

        return True
