"""
VoiceManager — общий держатель голосовых движков (STT + TTS) с ленивой
инициализацией в фоновом потоке, чтобы не грузить Whisper/TTS при каждом
запуске приложения, а только когда голос реально понадобился
"""

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class _VoiceLoaderThread(QThread):
    """Инициализирует STT и TTS движки в фоне (первая загрузка Whisper — тяжёлая)"""

    ready = pyqtSignal(object, object)  # (voice_engine, tts_engine)
    error = pyqtSignal(str)

    def __init__(self, language: str):
        super().__init__()
        self.language = language

    def run(self):
        try:
            from voice.engine import VoiceEngine
            voice_engine = VoiceEngine(language=self.language)
        except Exception as e:
            self.error.emit(f"Не удалось загрузить распознавание речи: {e}")
            return

        tts_engine = None
        try:
            from voice.tts_engine import TTSEngine
            tts_engine = TTSEngine(language=self.language)
        except Exception as e:
            print(f"⚠️  Синтез речи недоступен: {e}")

        self.ready.emit(voice_engine, tts_engine)


class VoiceManager(QObject):
    """
    Общий на всё приложение менеджер голосовых движков.
    Первый вызов ensure_loaded() запускает фоновую загрузку;
    повторные — no-op, пока движок уже загружен или загружается.
    """

    ready = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, language: str = "ru", parent=None):
        super().__init__(parent)
        self.language = language
        self.stt = None
        self.tts = None
        self._loading = False
        self._loader = None

    @property
    def is_ready(self) -> bool:
        return self.stt is not None

    def ensure_loaded(self):
        """Запускает фоновую загрузку STT/TTS, если ещё не загружено и не грузится"""
        if self.is_ready or self._loading:
            return
        self._loading = True
        self._loader = _VoiceLoaderThread(self.language)
        self._loader.ready.connect(self._on_ready)
        self._loader.error.connect(self._on_error)
        self._loader.start()

    def _on_ready(self, voice_engine, tts_engine):
        self.stt = voice_engine
        self.tts = tts_engine
        self._loading = False
        self.ready.emit()

    def _on_error(self, message: str):
        self._loading = False
        self.error.emit(message)
