"""
AppTool — управление программами на компьютере: запуск, переключение окон,
ввод текста и горячие клавиши, поиск в браузере.

Безопасность: любой ввод текста и любые горячие клавиши требуют явного
подтверждения пользователя (повторный вызов с "confirm": true), потому что
ошибка модели здесь уходит прямо в чужое приложение.
"""

import os
import shutil
import subprocess
import time
import urllib.parse
import webbrowser
from typing import Dict, List, Optional

try:
    import win32api
    import win32clipboard
    import win32con
    import win32gui
    import win32process
    _WIN32_AVAILABLE = True
except ImportError:  # pragma: no cover — не Windows или нет pywin32
    _WIN32_AVAILABLE = False

try:
    import keyboard as keyboard_lib
    _KEYBOARD_AVAILABLE = True
except ImportError:  # pragma: no cover
    _KEYBOARD_AVAILABLE = False


# Белый список программ: имя для агента -> команда запуска.
# Дополняется через add_program() / файл apps.json рядом с конфигом.
DEFAULT_PROGRAMS: Dict[str, str] = {
    "блокнот": "notepad.exe",
    "калькулятор": "calc.exe",
    "проводник": "explorer.exe",
    "браузер": "",            # открывается через webbrowser (браузер по умолчанию)
    "paint": "mspaint.exe",
    "терминал": "wt.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "диспетчер задач": "taskmgr.exe",
    "параметры": "ms-settings:",
    "claude": "claude",       # ищется в PATH / по стандартным путям установки
    "vs code": "code",
    "word": "winword.exe",
    "excel": "excel.exe",
}

SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={}",
    "yandex": "https://yandex.ru/search/?text={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
}

# Окна, в которые Nevada не станет печатать даже с подтверждением
BLOCKED_WINDOW_PATTERNS = ("диспетчер задач", "task manager", "regedit", "редактор реестра")


class AppTool:
    """Работа с программами и окнами Windows"""

    def __init__(self, extra_programs: Optional[Dict[str, str]] = None):
        self.programs = dict(DEFAULT_PROGRAMS)
        if extra_programs:
            self.programs.update(extra_programs)

        self.description = (
            "Управление программами на компьютере. Параметр action — ТОЛЬКО одно из:\n"
            "      • list_programs — какие программы разрешено запускать\n"
            "      • list_windows — список СЕЙЧАС открытых окон (заголовки)\n"
            "      • launch — запустить программу: {\"action\":\"launch\",\"program\":\"блокнот\"}\n"
            "      • focus — переключиться на окно: {\"action\":\"focus\",\"title\":\"Блокнот\"}\n"
            "      • type_text — напечатать текст в окно (title ОБЯЗАТЕЛЕН, ТРЕБУЕТ подтверждения):\n"
            "        {\"action\":\"type_text\",\"title\":\"Блокнот\",\"text\":\"...\",\"confirm\":true}\n"
            "      • hotkey — нажать сочетание клавиш (ТРЕБУЕТ подтверждения, title желателен):\n"
            "        {\"action\":\"hotkey\",\"title\":\"Блокнот\",\"keys\":\"ctrl+s\",\"confirm\":true}\n"
            "      • search — поиск в браузере: {\"action\":\"search\",\"query\":\"погода\"}\n"
            "        (необязательно engine: google/yandex/duckduckgo/youtube)\n"
            "      Перед вводом текста сначала узнай реальные окна через list_windows —\n"
            "      не угадывай заголовки."
        )

    # ------------------------------------------------------------------ API

    def execute(
        self,
        action: str,
        program: str = None,
        title: str = None,
        text: str = None,
        keys: str = None,
        query: str = None,
        engine: str = "google",
        confirm: bool = False,
    ) -> str:
        try:
            if action == "list_programs":
                return self._list_programs()
            if action == "list_windows":
                return self._list_windows()
            if action == "launch":
                return self._launch(program)
            if action == "focus":
                return self._focus(title)
            if action == "type_text":
                return self._type_text(text, title, confirm)
            if action == "hotkey":
                return self._hotkey(keys, confirm, title)
            if action == "search":
                return self._search(query, engine)
            return (
                f"❌ Неизвестное действие: {action}. "
                "Доступны: list_programs, list_windows, launch, focus, type_text, hotkey, search"
            )
        except Exception as e:
            return f"❌ Ошибка управления программами: {e}"

    def add_program(self, name: str, command: str) -> None:
        """Добавляет программу в белый список"""
        self.programs[name.strip().lower()] = command

    # -------------------------------------------------------------- Actions

    def _list_programs(self) -> str:
        names = sorted(self.programs)
        return "Разрешённые программы:\n" + "\n".join(f"  • {n}" for n in names)

    def _list_windows(self) -> str:
        if not _WIN32_AVAILABLE:
            return "❌ Управление окнами недоступно: не установлен pywin32"

        windows: List[str] = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                windows.append(title)

        win32gui.EnumWindows(callback, None)

        if not windows:
            return "Открытых окон не найдено"

        # Убираем дубликаты, сохраняя порядок
        unique = list(dict.fromkeys(windows))
        return "Сейчас открыты окна:\n" + "\n".join(f"  • {w}" for w in unique)

    def _launch(self, program: Optional[str]) -> str:
        if not program:
            return "❌ Не указано, какую программу запускать (параметр program)"

        key = program.strip().lower()
        if key not in self.programs:
            available = ", ".join(sorted(self.programs))
            return (
                f"❌ Программа '{program}' не в белом списке. "
                f"Разрешены: {available}. "
                "Добавить новую может только пользователь в настройках."
            )

        command = self.programs[key]

        # «Браузер» открываем через webbrowser — там браузер по умолчанию
        if key == "браузер" or not command:
            webbrowser.open("about:blank")
            return "✅ Открыт браузер"

        # ms-settings: и подобные URI запускаем через startfile
        if command.endswith(":"):
            os.startfile(command)
            return f"✅ Запущено: {program}"

        resolved = shutil.which(command)
        if resolved is None and not os.path.isabs(command):
            return (
                f"❌ Не удалось найти '{command}' в системе. "
                f"Возможно, программа '{program}' не установлена."
            )

        subprocess.Popen(resolved or command, shell=False)
        return f"✅ Запущено: {program}"

    def _find_window(self, title: str):
        """Ищет видимое окно по подстроке заголовка (без учёта регистра)"""
        needle = title.strip().lower()
        matches = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            window_title = win32gui.GetWindowText(hwnd).strip()
            if window_title and needle in window_title.lower():
                matches.append((hwnd, window_title))

        win32gui.EnumWindows(callback, None)
        return matches

    def _bring_to_foreground(self, hwnd) -> bool:
        """
        Пытается вывести окно на передний план и ПРОВЕРЯЕТ результат.
        Windows запрещает фоновому процессу «красть» фокус, поэтому
        одного SetForegroundWindow недостаточно — обязательна проверка.
        """
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
        except Exception:
            pass

        # Попытка 1: как есть
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.25)
        if win32gui.GetForegroundWindow() == hwnd:
            return True

        # Попытка 2: присоединяемся к потоку активного окна — так система
        # разрешает смену фокуса
        try:
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            current_thread = win32api.GetCurrentThreadId()
            foreground = win32gui.GetForegroundWindow()
            foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground) if foreground else (0, 0)

            for thread in {target_thread, foreground_thread}:
                if thread and thread != current_thread:
                    win32process.AttachThreadInput(current_thread, thread, True)
            try:
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            finally:
                for thread in {target_thread, foreground_thread}:
                    if thread and thread != current_thread:
                        win32process.AttachThreadInput(current_thread, thread, False)
        except Exception:
            pass

        time.sleep(0.25)
        return win32gui.GetForegroundWindow() == hwnd

    def _focus(self, title: Optional[str]) -> str:
        if not title:
            return "❌ Не указан заголовок окна (параметр title)"
        if not _WIN32_AVAILABLE:
            return "❌ Управление окнами недоступно: не установлен pywin32"

        matches = self._find_window(title)
        if not matches:
            return f"❌ Окно с заголовком, содержащим '{title}', не найдено. Проверь list_windows"

        hwnd, found_title = matches[0]
        if self._bring_to_foreground(hwnd):
            return f"✅ Активно окно: {found_title}"

        return (
            f"❌ Не удалось переключиться на «{found_title}» — Windows не отдала фокус. "
            "Попроси пользователя открыть это окно вручную."
        )

    def _set_clipboard(self, text: str) -> None:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

    def _type_text(self, text: Optional[str], title: Optional[str], confirm: bool) -> str:
        # Сначала проверки параметров и политики безопасности — они не зависят
        # от платформы и дают понятную ошибку даже без pywin32
        if not text:
            return "❌ Не указан текст для ввода (параметр text)"

        target = title or "активное окно"

        if title:
            for pattern in BLOCKED_WINDOW_PATTERNS:
                if pattern in title.lower():
                    return f"❌ В окно '{title}' ввод запрещён из соображений безопасности"

        if not confirm:
            preview = text if len(text) <= 200 else text[:200] + "…"
            return (
                f"⚠️ Требуется подтверждение пользователя. Собираюсь вставить в «{target}» текст:\n"
                f"---\n{preview}\n---\n"
                "Спроси пользователя явно и, если он согласен, вызови этот же инструмент "
                "повторно с \"confirm\": true."
            )

        if not _WIN32_AVAILABLE or not _KEYBOARD_AVAILABLE:
            return "❌ Ввод текста недоступен: нужны pywin32 и keyboard"

        # Печатать «вслепую» в неизвестно какое окно запрещено: нажатия уйдут
        # в то приложение, которое сейчас активно, и это может быть что угодно
        if not title:
            return (
                "❌ Нужно явно указать окно (параметр title). "
                "Сначала посмотри list_windows и выбери реальный заголовок."
            )

        matches = self._find_window(title)
        if not matches:
            return f"❌ Окно с заголовком, содержащим '{title}', не найдено. Проверь list_windows"

        hwnd, found_title = matches[0]
        if not self._bring_to_foreground(hwnd):
            return (
                f"❌ Текст НЕ вставлен: не удалось активировать окно «{found_title}» "
                "(Windows не отдала фокус фоновому процессу). Нажатия не отправлены, "
                "чтобы не попасть в чужое приложение. Попроси пользователя открыть окно вручную."
            )

        # Вставка через буфер обмена: имитация нажатий ненадёжна для кириллицы
        # (зависит от активной раскладки клавиатуры)
        self._set_clipboard(text)
        time.sleep(0.15)
        keyboard_lib.send("ctrl+v")
        time.sleep(0.2)

        # Проверяем, что фокус не увели в момент вставки
        if win32gui.GetForegroundWindow() != hwnd:
            return (
                f"⚠️ Во время вставки фокус ушёл из «{found_title}». "
                "Проверьте, куда попал текст."
            )

        return f"✅ Текст вставлен в «{found_title}» ({len(text)} симв.)"

    def _hotkey(self, keys: Optional[str], confirm: bool, title: Optional[str] = None) -> str:
        if not keys:
            return "❌ Не указано сочетание клавиш (параметр keys)"

        target = title or "активное окно"
        if not confirm:
            return (
                f"⚠️ Требуется подтверждение пользователя: собираюсь нажать «{keys}» "
                f"в «{target}». Спроси пользователя и вызови повторно с \"confirm\": true."
            )

        if not _KEYBOARD_AVAILABLE:
            return "❌ Горячие клавиши недоступны: не установлен keyboard"

        # Если окно указано — убеждаемся, что нажатия уйдут именно туда
        if title:
            if not _WIN32_AVAILABLE:
                return "❌ Проверка окна недоступна: не установлен pywin32"
            matches = self._find_window(title)
            if not matches:
                return f"❌ Окно '{title}' не найдено. Проверь list_windows"
            hwnd, found_title = matches[0]
            if not self._bring_to_foreground(hwnd):
                return (
                    f"❌ Клавиши НЕ отправлены: не удалось активировать «{found_title}». "
                    "Попроси пользователя открыть окно вручную."
                )
            target = found_title

        keyboard_lib.send(keys)
        return f"✅ Нажато «{keys}» в «{target}»"

    def _search(self, query: Optional[str], engine: str) -> str:
        if not query:
            return "❌ Не указан поисковый запрос (параметр query)"

        engine_key = (engine or "google").strip().lower()
        template = SEARCH_ENGINES.get(engine_key)
        if not template:
            return (
                f"❌ Неизвестная поисковая система '{engine}'. "
                f"Доступны: {', '.join(SEARCH_ENGINES)}"
            )

        url = template.format(urllib.parse.quote_plus(query))
        webbrowser.open(url)
        return f"✅ Открыт поиск в браузере ({engine_key}): {query}"
