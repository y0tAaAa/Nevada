"""Проверка трёх фиксов: очистка речи от tool-тегов, фильтр галлюцинаций Whisper,
и что ошибки API больше не попадают в память."""
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import types
import re

failures = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# --- заглушки только для железа ---
sd_mod = types.ModuleType("sounddevice")
sd_mod.query_devices = lambda: [{"name": "mic"}]
sys.modules["sounddevice"] = sd_mod

fw_mod = types.ModuleType("faster_whisper")
class _FakeWhisperModel:
    def __init__(self, *a, **k): pass
sys.modules["faster_whisper"] = fw_mod
fw_mod.WhisperModel = _FakeWhisperModel

pyttsx3_mod = types.ModuleType("pyttsx3")
class _FakeImpl:
    def getProperty(self, n): return [] if n == "voices" else None
    def setProperty(self, n, v): pass
    def say(self, t): pass
    def runAndWait(self): pass
    def stop(self): pass
pyttsx3_mod.init = lambda: _FakeImpl()
sys.modules["pyttsx3"] = pyttsx3_mod

from voice.tts_engine import prepare_response_for_speech
from voice.engine import is_hallucination, MIN_SPEECH_RMS

print("=== 1. Очистка ответа от tool-тегов (случай со скриншота) ===")

# Ровно тот текст, что был на экране у пользователя
screen_text = (
    'Если вы хотите добавить еще текст, отправьте команду в формате '
    '"<tool>редактор субтитров</tool><input>{...}</input>" и я буду готов помочь вам.\n\n'
    'Например, команду "<tool>редактор</tool><input>{text: X}</input>" чтобы добавить.\n\n'
    'Можете отправить "<tool>редактор</tool><input>{action: save, confirm: true}</input>".'
)
spoken = prepare_response_for_speech(screen_text)
check("нет '<tool>' в озвучиваемом тексте", "<tool>" not in spoken, f"got={spoken!r}")
check("нет '</input>' в озвучиваемом тексте", "</input>" not in spoken, f"got={spoken!r}")
check("нет '<input>' в озвучиваемом тексте", "<input>" not in spoken, f"got={spoken!r}")
check("нет '</tool>' в озвучиваемом тексте", "</tool>" not in spoken, f"got={spoken!r}")
check("осмысленный текст сохранён", "Например" in spoken and "помочь вам" in spoken)
print(f"    → озвучится: {spoken[:110]}...")

print("\n=== 2. Одиночные/незакрытые теги ===")
check("незакрытый <tool> вырезан", "<tool>" not in prepare_response_for_speech("Текст <tool> хвост"))
check("одиночный </input> вырезан", "input" not in prepare_response_for_speech("Текст </input> хвост").lower())
check("<think> вырезан", "think" not in prepare_response_for_speech("<think>размышляю</think> Ответ").lower())

print("\n=== 3. Фильтр галлюцинаций Whisper (реальные из лога) ===")
real_hallucinations = [
    "Редактор субтитров А.Кулакова",
    "Редактор субтитров А.Синецкая Корректор А.Егорова",
    "ДИНАМИЧНАЯ МУЗЫКА",
    "Продолжение следует...",
    "Субтитры сделал DimaTorzok",
    "Спасибо за просмотр!",
    "Thanks for watching!",
    "Subtitles by the Amara.org community",
    ".",
    "",
]
for h in real_hallucinations:
    check(f"отброшено: {h[:42]!r}", is_hallucination(h))

print("\n=== 4. Нормальная речь НЕ отбрасывается ===")
real_speech = [
    "Привет, это тест",
    "Открой калькулятор",
    "Покажи файлы в папке загрузки",
    "Какая сейчас загрузка процессора",
    "Да",
]
for s in real_speech:
    check(f"пропущено: {s[:42]!r}", not is_hallucination(s))

print("\n=== 5. Ошибки API больше не сохраняются в память ===")
import inspect
from agent import loop as loop_mod
src = inspect.getsource(loop_mod.AgentLoop.stream)
check("есть флаг failed", "failed = True" in src)
check("save вызывается только если не failed", "if not failed" in src)
check("есть общий except Exception", "except Exception" in src)

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
