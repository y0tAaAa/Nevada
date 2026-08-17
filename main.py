"""
Nevada — Автономный desktop-ассистент на PyQt6 + Groq API
Точка входа приложения
"""

import sys


class _NullStream:
    """Заглушка для собранного .exe без консоли: печатать некуда"""

    encoding = "utf-8"

    def write(self, _data):
        return 0

    def flush(self):
        pass

    def isatty(self):
        return False


def _configure_output() -> None:
    """
    Готовит stdout/stderr до любых print().

    В собранном .exe консоль работает в системной кодировке (на русской Windows
    это cp1251), и любой print() с эмодзи падает с UnicodeEncodeError — именно
    так падал хоткей-поток. В windowed-сборке потоков вывода вообще нет.
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            setattr(sys, name, _NullStream())
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_output()

from PyQt6.QtWidgets import QApplication  # noqa: E402
from app.nevada_app import NevadaApp  # noqa: E402


def main():
    # Создаём QApplication
    app = QApplication(sys.argv)

    # Приложение живёт в трее даже после закрытия окна
    app.setQuitOnLastWindowClosed(False)

    # Инициализируем Nevada
    nevada = NevadaApp(app)

    # Запускаем приложение
    if not nevada.start():
        print("[ERROR] Nevada не удалось запустить")
        return 1

    # Обработчик при завершении
    def on_quit():
        nevada.cleanup()
        print("[OK] Nevada завершила работу")

    app.aboutToQuit.connect(on_quit)

    # Запускаем event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
