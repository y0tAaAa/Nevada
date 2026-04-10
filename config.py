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
    model: str = os.getenv("NEVADA_MODEL", "gemma2-9b-it")
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
    
    # Цвета (тёмная тема)
    BG_WINDOW = "#0d0f14"
    BG_INPUT = "#1a1d26"
    BG_MSG_USER = "#2563eb"
    BG_MSG_NEV = "#1a1d26"
    TEXT_PRIMARY = "#e8eaf0"
    ACCENT = "#3b82f6"
    BORDER = "#1f2335"
    
    def validate(self) -> bool:
        """Проверяет обязательные настройки"""
        if not self.groq_api_key:
            print("⚠️  GROQ_API_KEY не установлен в .env")
            return False
        return True
