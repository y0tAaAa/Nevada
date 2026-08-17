"""Живой прогон против настоящего Groq API: тот же вопрос «какая видеокарта»."""
import os
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)

from memory.manager import MemoryManager
from tools.registry import ToolRegistry
from tools.shell import ShellTool
from tools.file_tool import FileTool
from tools.system_tool import SystemTool
from agent.loop import AgentLoop
from config import Config

cfg = Config()
registry = ToolRegistry()
for name, tool in (("shell", ShellTool()), ("file", FileTool()), ("system", SystemTool())):
    registry.register(name, tool, tool.description)

import tempfile
from pathlib import Path
tmp_db = Path(tempfile.mkdtemp()) / "probe.db"   # чистая память, не трогаем рабочую
memory = MemoryManager(tmp_db)

agent = AgentLoop(memory, tool_registry=registry)

question = sys.argv[1] if len(sys.argv) > 1 else "какая у меня видеокарта?"
print(f"ВОПРОС: {question}")
print("=" * 70)
answer = "".join(agent.stream(question))
print(answer)
print("=" * 70)

# Реальное имя видеокарты для сверки
import subprocess
real = subprocess.run(
    "wmic path win32_VideoController get name",
    shell=True, capture_output=True, text=True
).stdout
print("ФАКТИЧЕСКАЯ ВИДЕОКАРТА ПО СИСТЕМЕ:")
print(real.strip())
memory.close()
