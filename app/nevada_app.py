"""
NevadaApp — главный класс приложения
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
from pathlib import Path
from config import Config
from memory.manager import MemoryManager
from agent.loop import AgentLoop
from ui.chat_window import ChatWindow
from app.tray import TrayManager


class NevadaApp(QObject):
    """Главное приложение Nevada"""
    
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.config = Config()
        
        # Проверяем конфиг
        if not self.config.validate():
            print("⚠️  Ошибка конфигурации. Пожалуйста, проверьте .env файл")
            return
        
        # Инициализируем компоненты
        self.memory = MemoryManager(self.config.db_path)
        self.agent_loop = AgentLoop(self.memory, tool_registry=None)
        
        # UI
        self.chat_window = ChatWindow(agent_loop=self.agent_loop)
        
        # Трей
        self.tray_manager = TrayManager()
        self._setup_signals()
        
        # Горячая клавиша (будет инициализирована в Phase 2)
        self.hotkey_manager = None
        
        # Автозапуск (будет инициализирован в Phase 2)
        self.autostart_manager = None
    
    def _setup_signals(self):
        """Подключает сигналы трея"""
        self.tray_manager.signals.open_chat.connect(self._show_chat_window)
        self.tray_manager.signals.open_dashboard.connect(self._open_dashboard)
        self.tray_manager.signals.open_settings.connect(self._open_settings)
        self.tray_manager.signals.quit_app.connect(self._quit_app)
    
    def _show_chat_window(self):
        """Показывает окно чата"""
        if self.chat_window.isMinimized():
            self.chat_window.showNormal()
        elif not self.chat_window.isVisible():
            self.chat_window.show()
        else:
            self.chat_window.hide()
        self.chat_window.raise_()
        self.chat_window.activateWindow()
    
    def _open_dashboard(self):
        """Открывает дашборд (будет реализовано в Phase 3)"""
        self.tray_manager.show_notification("Nevada", "Дашборд будет доступен в Phase 3")
    
    def _open_settings(self):
        """Открывает диалог настроек (будет реализовано в Phase 3)"""
        self.tray_manager.show_notification("Nevada", "Настройки будут доступны в Phase 3")
    
    def _quit_app(self):
        """Завершает приложение"""
        self.memory.close()
        self.app.quit()
    
    def start(self):
        """Запускает приложение"""
        # Показываем трей
        self.tray_manager.show()
        
        # Показываем окно чата по умолчанию
        self._show_chat_window()
        
        print("✅ Nevada запущён!")
        print(f"🎯 API модель: {self.config.model}")
        print(f"🌍 Язык: {self.config.language}")
        print(f"⌨️ Горячая клавиша: {self.config.hotkey}")
    
    def cleanup(self):
        """Очистка при завершении"""
        self.memory.close()
