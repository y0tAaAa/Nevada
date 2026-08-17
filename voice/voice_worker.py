"""
QThread-воркеры для голосового ввода/вывода — чтобы запись, распознавание
и синтез речи не блокировали UI
"""

from PyQt6.QtCore import QThread, pyqtSignal


class ListenWorker(QThread):
    """Записывает речь до тишины и распознаёт её через VoiceEngine"""

    text_ready = pyqtSignal(str)
    no_speech = pyqtSignal()
    error = pyqtSignal(str)
    level_changed = pyqtSignal(float)  # RMS-уровень микрофона, для визуализации

    def __init__(self, voice_engine, max_duration: float = 10):
        super().__init__()
        self.voice_engine = voice_engine
        self.max_duration = max_duration

    def run(self):
        try:
            text = self.voice_engine.listen_until_silence(
                max_duration=self.max_duration,
                on_level=lambda level: self.level_changed.emit(level),
            )
            if text:
                self.text_ready.emit(text)
            else:
                self.no_speech.emit()
        except Exception as e:
            self.error.emit(str(e))


class SpeakWorker(QThread):
    """Озвучивает текст через TTSEngine"""

    finished_speaking = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, tts_engine, text: str):
        super().__init__()
        self.tts_engine = tts_engine
        self.text = text

    def run(self):
        try:
            self.tts_engine.speak(self.text)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished_speaking.emit()
