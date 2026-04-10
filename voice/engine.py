"""
VoiceEngine — распознавание речи через faster-whisper
"""

import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional
from pathlib import Path


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
            
            # Распознаём через Whisper
            segments, _ = self.model.transcribe(
                audio,
                language=self.language,
                beam_size=5
            )
            
            # Собираем результат
            text = "".join([segment.text for segment in segments]).strip()
            
            if text:
                print(f"✅ Распознано: {text}")
                return text
            else:
                print("⚠️  Не удалось распознать речь")
                return None
        
        except Exception as e:
            print(f"❌ Ошибка при записи: {str(e)}")
            return None
    
    def listen_until_silence(self, max_duration: float = 10, silence_threshold: float = 0.01) -> Optional[str]:
        """
        Записывает речь до наступления тишины.
        
        Args:
            max_duration: Максимальная длительность записи
            silence_threshold: Порог тишины (norm значение)
        
        Returns:
            Распознанный текст
        """
        if not self.is_available():
            return None
        
        try:
            print("🎤 Слушаю... (говорите, потом беру паузу)")
            
            # Записываем весь аудиопоток
            frames = []
            silence_frames = 0
            max_silence_frames = int(0.5 * self.sample_rate)  # 0.5s тишины
            
            def audio_callback(indata, frames_count, time_info, status):
                nonlocal silence_frames
                
                # Вычисляем RMS уровень
                rms = np.sqrt(np.mean(indata**2))
                
                frames.append(indata.copy())
                
                if rms < silence_threshold:
                    silence_frames += 1
                else:
                    silence_frames = 0
            
            # Начинаем потоковую запись
            with sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                callback=audio_callback,
                blocksize=self.sample_rate // 10  # 100ms блоки
            ) as stream:
                while len(frames) < max_duration * self.sample_rate and silence_frames < max_silence_frames:
                    sd.sleep(50)
            
            # Объединяем фреймы
            if frames:
                audio = np.vstack(frames)
                
                # Распознаём
                segments, _ = self.model.transcribe(
                    np.squeeze(audio),
                    language=self.language,
                    beam_size=5
                )
                
                text = "".join([segment.text for segment in segments]).strip()
                
                if text:
                    print(f"✅ Распознано: {text}")
                    return text
            
            print("⚠️  Не удалось распознать речь")
            return None
        
        except Exception as e:
            print(f"❌ Ошибка голосового ввода: {str(e)}")
            return None
