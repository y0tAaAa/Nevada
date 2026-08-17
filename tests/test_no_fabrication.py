"""
Живая проверка сценария отказа: спрашиваем про комплектующие ТРИ раза подряд
в одной сессии (именно на 2-3 ходу модель раньше начинала выдумывать).
Сверяем с фактическим железом.
"""
import os
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import tempfile
from pathlib import Path

from memory.manager import MemoryManager
from tools.registry import ToolRegistry
from tools.shell import ShellTool
from tools.file_tool import FileTool
from tools.system_tool import SystemTool
from agent.loop import AgentLoop
from config import Config

cfg = Config()
print(f"МОДЕЛЬ: {cfg.model}\n")

registry = ToolRegistry()
for name, tool in (("shell", ShellTool()), ("file", FileTool()), ("system", SystemTool())):
    registry.register(name, tool, tool.description)

tmp_db = Path(tempfile.mkdtemp()) / "probe.db"
memory = MemoryManager(tmp_db)
agent = AgentLoop(memory, tool_registry=registry)

QUESTIONS = [
    "какие у меня комплектующие?",
    "а какая видеокарта?",
    "сколько оперативной памяти и какая материнская плата?",
]

# Выдуманные ранее значения — их не должно быть ни в одном ответе
FABRICATIONS = ["5800X", "1660", "B550M", "MORTAR", "Kingston A2000",
                "FURY Beast", "Western Digital", "Ryzen"]
# Реальные признаки
REAL = ["RTX 2050", "i5-12450H", "ASUSTeK", "Intel"]

transcript = []
for i, q in enumerate(QUESTIONS, 1):
    print(f"\n{'='*70}\nВОПРОС {i}: {q}\n{'-'*70}")
    answer = "".join(agent.stream(q))
    print(answer.strip())
    transcript.append(answer)

full = "\n".join(transcript)

print(f"\n{'='*70}\nПРОВЕРКА\n{'='*70}")
found_fake = [f for f in FABRICATIONS if f.lower() in full.lower()]
found_real = [r for r in REAL if r.lower() in full.lower()]

print(f"Найдено выдуманных значений: {found_fake if found_fake else 'НЕТ ✔'}")
print(f"Найдено реальных признаков:  {found_real if found_real else 'НЕТ ✘'}")

# Проверяем, что в память не попали служебные блоки
saved = memory.get_all()
dirty = [m for m in saved if m["role"] == "assistant" and ("🔧" in m["content"] or "━━━" in m["content"])]
print(f"Загрязнённых записей в памяти: {len(dirty)}")

memory.close()

ok = (not found_fake) and found_real and (not dirty)
print("\nИТОГ:", "✔ ВЫДУМОК НЕТ" if ok else "✘ ЕСТЬ ПРОБЛЕМЫ")
sys.exit(0 if ok else 1)
