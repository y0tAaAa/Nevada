"""Живой прогон через настоящего агента: просим его поработать с программами."""
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
from tools.app_tool import AppTool
from tools.skill_tool import SkillTool
from tools.research_tool import ResearchTool
from agent.loop import AgentLoop

registry = ToolRegistry()
for name, tool in (("shell", ShellTool()), ("file", FileTool()),
                   ("system", SystemTool()), ("app", AppTool()), ("skill", SkillTool()), ("research", ResearchTool())):
    registry.register(name, tool, tool.description)

memory = MemoryManager(Path(tempfile.mkdtemp()) / "apps.db")
agent = AgentLoop(memory, tool_registry=registry)

question = sys.argv[1] if len(sys.argv) > 1 else "какие программы у меня сейчас открыты?"
print(f"ВОПРОС: {question}\n{'='*70}")
print("".join(agent.stream(question)))
memory.close()
