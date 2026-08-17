"""
Запуск тестов Nevada.

    python tests/run_tests.py            # только офлайн-тесты (по умолчанию)
    python tests/run_tests.py --live     # ещё и живые (сеть, токены Groq, окна)
    python tests/run_tests.py --all      # всё
    python tests/run_tests.py test_skills.py test_tools.py   # выборочно

Если зависимости лежат в отдельной папке, укажите её:
    set NEVADA_TEST_DEPS=C:\\путь\\к\\deps
"""

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent

# Не требуют сети, токенов и не трогают окна — можно гонять всегда
OFFLINE_TESTS = [
    "test_tools.py",         # инструменты shell/file и подтверждение через confirm
    "test_agent_loop.py",    # агентный цикл, фильтр тегов, чистота памяти
    "test_fact_guard.py",    # страж выдумок
    "test_confirm_gate.py",  # гейт подтверждения (модель не обойдёт)
    "test_skills.py",        # навыки: парсинг, триггеры, перезагрузка
    "test_app_tool.py",      # белый список, окна, запрет слепого ввода
    "test_fixes.py",         # очистка речи от тегов, фильтр галлюцинаций Whisper
    "test_worker_dedup.py",  # воркер не выполняет инструменты сам
    "test_wiring.py",        # сборка UI (ловит ошибки проводки)
    "test_ui_layout.py",     # раскладка сообщений, прокрутка, cooldown HUD
]

# Требуют сети, квоты Groq или взаимодействия с рабочим столом
LIVE_TESTS = {
    "test_research.py": "сеть: Wikipedia (токены Groq не тратит)",
    "test_agent_apps.py": "тратит токены Groq",
    "test_no_fabrication.py": "тратит токены Groq",
    "test_real_gpu.py": "тратит токены Groq",
    "test_voice_hud.py": "загружает модель Whisper (~75 МБ при первом запуске)",
    "test_notepad_live.py": "откроет Блокнот и напечатает в него текст",
}


# Каждый тест обязан напечатать эту строку. Без неё «успех» недостоверен:
# пустой или обрезанный файл тоже выходит с кодом 0.
RESULT_MARKER = "ИТОГ:"


def run_one(name: str) -> bool:
    path = TESTS_DIR / name
    if not path.exists():
        print(f"[SKIP] {name}: файла нет")
        return False

    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(PROJECT_ROOT),
        env={**_env(), "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (result.stdout or "") + (result.stderr or "")
    print(output.rstrip())

    if result.returncode != 0:
        return False

    # Защита от ложного «зелёного»: тест не напечатал итог — значит,
    # он не выполнился до конца (обрезан, упал молча, ничего не проверил)
    if RESULT_MARKER not in output:
        print(f"[FAIL] {name}: тест не напечатал «{RESULT_MARKER}» — "
              "вероятно, не выполнился до конца")
        return False

    return True


def _env() -> dict:
    import os
    return dict(os.environ)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    explicit = [a for a in args if a.endswith(".py")]
    flags = {a for a in args if a.startswith("--")}

    if explicit:
        selected = explicit
    elif "--all" in flags:
        selected = OFFLINE_TESTS + list(LIVE_TESTS)
    elif "--live" in flags:
        selected = list(LIVE_TESTS)
    else:
        selected = OFFLINE_TESTS

    if selected is not OFFLINE_TESTS and any(t in LIVE_TESTS for t in selected):
        print("Внимание: среди выбранных есть живые тесты —")
        for t in selected:
            if t in LIVE_TESTS:
                print(f"  • {t}: {LIVE_TESTS[t]}")

    passed, failed = [], []
    for name in selected:
        (passed if run_one(name) else failed).append(name)

    print(f"\n{'=' * 70}\nИТОГ: пройдено {len(passed)}, провалено {len(failed)}")
    for name in failed:
        print(f"  ПРОВАЛ: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
