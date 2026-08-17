"""
Общая настройка путей для тестов.

Тесты должны работать в двух ситуациях:
1. Зависимости установлены обычно (pip install -r requirements.txt) — ничего
   настраивать не нужно.
2. Зависимости лежат в отдельной папке (изолированная установка) — путь берётся
   из переменной окружения NEVADA_TEST_DEPS.

Импортируйте это первым делом:  from tests.conftest_paths import setup_paths
                               setup_paths()
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def setup_paths(offscreen: bool = False) -> None:
    """
    Готовит sys.path и, при необходимости, папку с изолированными зависимостями.

    Args:
        offscreen: включить QT_QPA_PLATFORM=offscreen для UI-тестов без экрана
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    deps = os.environ.get("NEVADA_TEST_DEPS")
    if deps:
        deps_path = Path(deps)
        if deps_path.exists():
            _add_deps(deps_path)

    if offscreen:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _add_deps(deps_path: Path) -> None:
    """Подключает изолированную папку зависимостей, включая pywin32"""
    for candidate in (deps_path, deps_path / "win32", deps_path / "win32" / "lib",
                      deps_path / "win32com"):
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))

    # Python 3.8+ на Windows не берёт DLL из PATH — нужен add_dll_directory
    system32 = deps_path / "pywin32_system32"
    if system32.exists() and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(system32))
        except OSError:
            pass


class Checker:
    """Простой сборщик результатов проверок, общий для всех тестов"""

    def __init__(self):
        self.failures = []

    def __call__(self, name: str, condition, detail: str = "") -> bool:
        ok = bool(condition)
        suffix = f" — {detail}" if detail and not ok else ""
        print(f"[{'OK ' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            self.failures.append(name)
        return ok

    def finish(self) -> int:
        """Печатает итог, возвращает код выхода"""
        print()
        if self.failures:
            print(f"ИТОГ: провалено {len(self.failures)}: {self.failures}")
            return 1
        print("ИТОГ: все проверки пройдены")
        return 0
