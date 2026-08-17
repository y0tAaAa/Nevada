"""
Конфигурация Nevada — загружает параметры из .env
"""

from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os


@dataclass
class Config:
    """Настройки приложения Nevada"""
    
    # Загружаем .env файл
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    # API Groq
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = os.getenv("NEVADA_MODEL", "llama-3.3-70b-versatile")
    api_base: str = "https://api.groq.com/openai/v1"
    
    # Приложение
    system_name: str = "Nevada"
    language: str = os.getenv("NEVADA_LANGUAGE", "ru")
    
    # Горячие клавиши
    hotkey: str = os.getenv("NEVADA_HOTKEY", "ctrl+shift+space")
    
    # Автозапуск
    autostart: bool = os.getenv("NEVADA_AUTOSTART", "true").lower() == "true"
    
    # База данных
    db_path: Path = Path(__file__).parent / "nevada.db"
    
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
            print("⚠️  GROQ_API_KEY не установлен в .env")
            return False
        return True
