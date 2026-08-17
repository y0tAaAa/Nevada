"""
VoiceEngine — распознавание речи через faster-whisper
"""

import re

import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional
from pathlib import Path


# Whisper обучался на субтитрах и на тишине/шуме галлюцинирует титрами
# ("Редактор субтитров ...", "ДИНАМИЧНАЯ МУЗЫКА", "Продолжение следует...").
# Такие фразы нельзя отдавать агенту — они засоряют память диалога.
_HALLUCINATION_PATTERNS = [
    r"редактор\s+субтитр",
    r"корректор\b",
    r"субтитры\s+(?:сделал|создан|подготов)",
    r"продолжение\s+следует",
    r"динамичная\s+музыка",
    r"^\s*музыка\s*$",
    r"^\s*аплодисменты\s*$",
    r"^\s*спасибо\s+за\s+просмотр",
    r"^\s*подписывайтесь",
    r"amara\.org",
    r"subtitles?\s+by",
    r"thanks\s+for\s+watching",
]

# Минимальная громкость (RMS), ниже которой считаем, что речи не было
MIN_SPEECH_RMS = 0.006
# Минимальная длительность речи в секундах
MIN_SPEECH_SECONDS = 0.35


def is_hallucination(text: str) -> bool:
    """Проверяет, похож ли распознанный текст на типичную галлюцинацию Whisper"""
    if not text:
        return True

    normalized = text.strip().lower()

    # Одни лишь знаки препинания / очень короткий мусор
    if len(re.sub(r"[^\w]", "", normalized)) < 2:
        return True

    for pattern in _HALLUCINATION_PATTERNS:
        if re.search(pattern, normalized):
            return True

    return False


class VoiceEngine:
    """Голосовой ввод с использованием Whisper"""

    def __init__(self, language: str = "ru", model_name: str = "tiny"):
        """
        Args:
            language: Язык распознавания ('ru', 'en', и т.д.)
            model_name: Размер модели Whisper ('tiny', 'base', 'small')
        """
        self.language = language
        self.model_name = model_name
        self.sample_rate = 16000
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Загружает модель Whisper в памяти"""
        try:
            print(f"🎤 Загрузка модели Whisper ({self.model_name})...")
            self.model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8"  # Оптимизированный формат для CPU
            )
            print("✅ Модель загружена")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Проверяет наличие микрофона и модели"""
        if not self.model:
            return False
        
        try:
            # Пытаемся получить список микрофонов
            devices = sd.query_devices()
            return len(devices) > 0
        except Exception:
            return False
    
    def listen(self, seconds: float = 5, device: Optional[int] = None) -> Optional[str]:
        """
        Записывает аудио и распознаёт речь.
        
        Args:
            seconds: Время записи в секундах
            device: ID микрофона (None = стандартный)
        
        Returns:
            Распознанный текст или None при ошибке
        """
        if not self.is_available():
            return None
        
        try:
            print(f"🎤 Записываю... ({seconds}s)")
            
            # Записываем аудио
            audio = sd.rec(
                int(self.sample_rate * seconds),
                samplerate=self.sample_rate,
                channels=1,
                device=device,
                dtype=np.float32
            )
            sd.wait()
            
            # Нормализуем
            audio = np.squeeze(audio)

            # Распознаём через Whisper (с защитой от галлюцинаций)
            text = self._transcribe(audio)
            if text:
                return text

            print("⚠️  Не удалось распознать речь")
            return None
        
        except Exception as e:
            print(f"❌ Ошибка при записи: {str(e)}")
            return None
    
    def listen_until_silence(
        self,
        max_duration: float = 10,
        silence_threshold: float = 0.01,
        on_level: Optional[callable] = None,
    ) -> Optional[str]:
        """
        Записывает речь до наступления тишины.

        Args:
            max_duration: Максимальная длительность записи
            silence_threshold: Порог тишины (norm значение)
            on_level: Коллбек(rms: float), вызывается на каждый аудио-блок —
                      используется для реактивной визуализации уровня звука (HUD)

        Returns:
            Распознанный текст
        """
        if not self.is_available():
            return None

        try:
            print("🎤 Слушаю... (говорите, потом беру паузу)")

            # Записываем весь аудиопоток блоками по 100мс
            block_size = self.sample_rate // 10
            frames = []
            silence_frames = 0
            max_blocks = int(max_duration * 10)  # max_duration в блоках по 100мс
            max_silence_frames = 5  # 5 блоков по 100мс = 0.5s тишины

            def audio_callback(indata, frames_count, time_info, status):
                nonlocal silence_frames

                # Вычисляем RMS уровень
                rms = np.sqrt(np.mean(indata**2))

                frames.append(indata.copy())

                if on_level:
                    on_level(float(rms))

                if rms < silence_threshold:
                    silence_frames += 1
                else:
                    silence_frames = 0
            
            # Начинаем потоковую запись
            with sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                callback=audio_callback,
                blocksize=block_size
            ) as stream:
                while len(frames) < max_blocks and silence_frames < max_silence_frames:
                    sd.sleep(50)
            
            # Объединяем фреймы
            if frames:
                audio = np.squeeze(np.vstack(frames))
                text = self._transcribe(audio)
                if text:
                    return text

            print("⚠️  Не удалось распознать речь")
            return None
        
        except Exception as e:
            print(f"❌ Ошибка голосового ввода: {str(e)}")
            return None

    def _transcribe(self, audio: np.ndarray) -> Optional[str]:
        """
        Распознаёт готовый аудиомассив с защитой от галлюцинаций Whisper:
        отсекает слишком тихие/короткие записи, включает VAD и фильтрует
        типичные "субтитровые" галлюцинации.
        """
        # Гейт по громкости — на тишине Whisper выдумывает титры
        rms = float(np.sqrt(np.mean(audio ** 2)))
        duration = len(audio) / self.sample_rate
        if rms < MIN_SPEECH_RMS or duration < MIN_SPEECH_SECONDS:
            print(f"⚠️  Тишина (RMS={rms:.4f}, {duration:.2f}s) — пропускаем распознавание")
            return None

        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,                 # отсекаем участки без речи
            condition_on_previous_text=False,  # не даём модели "разгоняться" на своих же выдумках
            no_speech_threshold=0.6,
        )

        text = "".join(segment.text for segment in segments).strip()

        if is_hallucination(text):
            print(f"⚠️  Отброшена галлюцинация Whisper: {text!r}")
            return None

        print(f"✅ Распознано: {text}")
        return text
