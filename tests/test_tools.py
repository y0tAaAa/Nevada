"""Проверка tools/*, agent/parser.py — только stdlib, без установки зависимостей."""
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import tempfile
import shutil
from pathlib import Path

from tools.registry import ToolRegistry
from tools.shell import ShellTool
from tools.file_tool import FileTool
from agent.parser import parse_tool_call

failures = []

def check(name, cond):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        failures.append(name)

# --- parser.py ---
tc = parse_tool_call('<tool>shell</tool><input>{"command": "dir"}</input>')
check("parser: базовый tool call парсится", tc == ("shell", {"command": "dir"}))
check("parser: нет tool call -> None", parse_tool_call("просто текст") is None)

# --- ShellTool: деструктивная команда требует confirm ---
shell = ShellTool()
r1 = shell.execute("del C:\\temp\\file.txt")
check("shell: деструктивная команда без confirm блокируется", "подтвержд" in r1 and "temp" not in r1.split("подтвержд")[0])
r2 = shell.execute("echo hello")
check("shell: обычная команда выполняется сразу", "hello" in r2)

# --- ShellTool: confirm=True реально выполняет ---
tmp_dir = Path(tempfile.mkdtemp(prefix="nevada_test_"))
victim_dir = tmp_dir / "sub"
victim_dir.mkdir()
r3 = shell.execute(f'rmdir /s /q "{victim_dir}"', confirm=True)
check("shell: confirm=True реально удаляет через rmdir", not victim_dir.exists())

# --- FileTool: delete без confirm не удаляет ---
ft = FileTool()
victim_file = tmp_dir / "victim.txt"
victim_file.write_text("secret")
r4 = ft.execute("delete", str(victim_file))
check("file: delete без confirm НЕ удаляет файл", victim_file.exists() and "подтвержд" in r4)

# --- FileTool: delete с confirm=True реально удаляет ---
r5 = ft.execute("delete", str(victim_file), confirm=True)
check("file: delete с confirm=True реально удаляет файл", not victim_file.exists() and "Удалено" in r5)

# --- FileTool: delete директории с confirm=True ---
victim_dir2 = tmp_dir / "sub2"
victim_dir2.mkdir()
(victim_dir2 / "inner.txt").write_text("x")
r6 = ft.execute("delete", str(victim_dir2), confirm=True)
check("file: delete директории с confirm=True удаляет рекурсивно", not victim_dir2.exists())

# --- ToolRegistry передаёт confirm как kwarg ---
registry = ToolRegistry()
registry.register("file", ft, ft.description)
victim_file2 = tmp_dir / "victim2.txt"
victim_file2.write_text("secret2")
result = registry.execute("file", {"action": "delete", "path": str(victim_file2), "confirm": True})
check("registry: confirm корректно прокидывается через execute()", not victim_file2.exists())

shutil.rmtree(tmp_dir, ignore_errors=True)

print()
if failures:
    print(f"ИТОГ: {len(failures)} провалено: {failures}")
    sys.exit(1)
else:
    print("ИТОГ: все проверки пройдены")
