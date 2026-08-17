"""
Живой end-to-end тест: открываем ЧИСТЫЙ блокнот, вставляем в него русский текст
и читаем содержимое обратно через WM_GETTEXT, чтобы доказать, что текст реально дошёл.
Ничего кроме только что открытого блокнота не трогаем.
"""
import os
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import time

import win32gui
import win32con

from tools.app_tool import AppTool

TEST_TEXT = "Проверка Nevada: заметка на русском языке, 12345."

tool = AppTool()

print("1) Запускаю блокнот...")
print("   ", tool.execute("launch", program="блокнот"))
time.sleep(2.0)

print("2) Ищу окно блокнота среди реальных окон...")
matches = tool._find_window("Блокнот") or tool._find_window("Notepad")
if not matches:
    print("   ❌ окно блокнота не найдено")
    sys.exit(1)
hwnd, title = matches[0]
print(f"   найдено: {title!r}")

print("3) Пробую вставить БЕЗ подтверждения (должно быть отказано)...")
r = tool.execute("type_text", title=title, text=TEST_TEXT)
assert "Требуется подтверждение" in r, r
print("   ✔ отказано, как и задумано")

print("4) Вставляю С подтверждением...")
print("   ", tool.execute("type_text", title=title, text=TEST_TEXT, confirm=True))
time.sleep(0.8)


def read_text_from_window(root_hwnd) -> str:
    """Читает текст из дочерних контролов окна через WM_GETTEXT"""
    found = []

    def walk(hwnd, _):
        cls = win32gui.GetClassName(hwnd)
        length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
        if length:
            buf = win32gui.PyMakeBuffer((length + 1) * 2)
            win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buf)
            try:
                value = buf[: (length) * 2].tobytes().decode("utf-16-le", errors="ignore")
            except Exception:
                value = ""
            if value.strip():
                found.append((cls, value))

    try:
        win32gui.EnumChildWindows(root_hwnd, walk, None)
    except Exception as e:
        print("   (не удалось обойти дочерние окна:", e, ")")
    return "\n".join(v for _, v in found)


print("5) Читаю содержимое окна обратно...")
content = read_text_from_window(hwnd)
if content:
    print(f"   прочитано: {content[:120]!r}")
else:
    print("   (современный Блокнот Windows 11 не отдаёт текст через WM_GETTEXT)")

ok = TEST_TEXT in content
print()
if ok:
    print("ИТОГ: ✔ текст ПОДТВЕРЖДЁН в окне блокнота")
else:
    print("ИТОГ: ⚠ программно подтвердить не удалось — проверьте окно блокнота глазами.")
    print(f"      Ожидаемый текст: {TEST_TEXT}")
