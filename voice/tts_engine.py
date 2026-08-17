"""
TTSEngine — синтез речи через pyttsx3 (офлайн, системные голоса Windows/SAPI5)
"""

import re
import threading
from typing import Optional

import pyttsx3



class TTSEngine:
    """Голосовой ответ Nevada"""

    def __init__(self, language: str = "ru", rate: int = 175):
        """
        Args:
            language: Предпочитаемый язык голоса ('ru', 'en', ...)
            rate: Скорость речи (слов в минуту)
        """
        self.language = language
        self.rate = rate
        self._lock = threading.Lock()
        self._voice_id: Optional[str] = None
        self._resolve_voice()

    def _resolve_voice(self) -> None:
        """Один раз находит подходящий системный голос под нужный язык"""
        try:
            probe = pyttsx3.init()
            try:
                for voice in probe.getProperty("voices"):
                    haystack = " ".join(
                        str(x) for x in (
                            voice.id or "",
                            voice.name or "",
                            *(getattr(voice, "languages", None) or []),
                        )
                    ).lower()
                    if self.language == "ru" and ("ru" in haystack or "russian" in haystack):
                        self._voice_id = voice.id
                        break
                    if self.language == "en" and ("en" in haystack or "english" in haystack):
                        self._voice_id = voice.id
                        break
            finally:
                probe.stop()
        except Exception as e:
            print(f"⚠️  Не удалось определить голос TTS: {e}")

    def is_available(self) -> bool:
        try:
            probe = pyttsx3.init()
            probe.stop()
            return True
        except Exception:
            return False

    def speak(self, text: str) -> None:
        """
        Блокирующий синтез речи — вызывать из фонового потока (см. voice/voice_worker.py).
        """
        text = clean_for_speech(text)
        if not text:
            return

        with self._lock:
            engine = pyttsx3.init()
            try:
                engine.setProperty("rate", self.rate)
                if self._voice_id:
                    engine.setProperty("voice", self._voice_id)
                engine.say(text)
                engine.runAndWait()
            finally:
                engine.stop()


_MARKDOWN_PATTERN = re.compile(r"[*_`#>~]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Полностью оформленные tool call'ы: <tool>...</tool> и <input>{...}</input>
_TOOL_BLOCK_PATTERN = re.compile(r"<tool\s*>.*?</tool\s*>", re.DOTALL | re.IGNORECASE)
_INPUT_BLOCK_PATTERN = re.compile(r"<input\s*>.*?</input\s*>", re.DOTALL | re.IGNORECASE)
# Одиночные/незакрытые теги, которые иначе TTS читает вслух ("слэш инпут")
_STRAY_TAG_PATTERN = re.compile(r"</?\s*(?:tool|input|think)\s*>", re.IGNORECASE)


def clean_for_speech(text: str) -> str:
    """Убирает markdown-разметку и служебные символы, чтобы TTS не читал их вслух"""
    if not text:
        return ""
    text = _MARKDOWN_PATTERN.sub("", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def prepare_response_for_speech(full_response: str) -> str:
    """
    Готовит ответ агента к озвучке: вырезает ВСЕ XML tool-call блоки
    (<tool>...</tool><input>...</input>, в том числе несколько подряд и
    вперемешку с текстом), остатки одиночных тегов и markdown-разметку.
    """
    if not full_response:
        return ""

    text = _TOOL_BLOCK_PATTERN.sub(" ", full_response)
    text = _INPUT_BLOCK_PATTERN.sub(" ", text)
    text = _STRAY_TAG_PATTERN.sub(" ", text)
    return clean_for_speech(text)
