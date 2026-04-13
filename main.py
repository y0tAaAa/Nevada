"""
Nevada — Автономный desktop-ассистент на PyQt6 + Groq API
Точка входа приложения
"""

import sys
from PyQt6.QtWidgets import QApplication
from app.nevada_app import NevadaApp


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

