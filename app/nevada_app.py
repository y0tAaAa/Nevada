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
from ui.floating import FloatingWidget
from ui.dashboard import Dashboard
from ui.settings_dialog import SettingsDialog
from app.tray import TrayManager
from app.hotkey import HotkeyManager
from app.autostart import Autostart
from tools.registry import ToolRegistry
from tools.shell import ShellTool
from tools.file_tool import FileTool
from tools.system_tool import SystemTool
from scheduler.planner import DayPlanner


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
        
        # Инициализируем инструменты
        self.tool_registry = self._setup_tools()
        
        # Инициализируем компоненты
        self.memory = MemoryManager(self.config.db_path)
        self.agent_loop = AgentLoop(self.memory, tool_registry=self.tool_registry)
        
        # UI
        self.chat_window = ChatWindow(agent_loop=self.agent_loop)
        self.floating_widget = FloatingWidget(agent_loop=self.agent_loop)
        
        # Dashboard и настройки
        self.dashboard = Dashboard(
            memory=self.memory,
            planner=None,  # Будет инициализирован ниже
            tool_registry=self.tool_registry
        )
        self.settings_dialog = SettingsDialog(config=self.config)
        
        # Планировщик задач
        self.planner = DayPlanner(
            db_path=self.config.db_path,
            tray_manager=None  # Будет установлен ниже
        )
        
        # Обновляем dashboard с planner
        self.dashboard.planner = self.planner
        
        # Трей
        self.tray_manager = TrayManager()
        self._setup_signals()
        
        # Горячая клавиша
        self.hotkey_manager = HotkeyManager(hotkey=self.config.hotkey)
        self.hotkey_manager.triggered.connect(self._on_hotkey)
        
        # Автозапуск
        self.autostart_manager = Autostart()
    
    def _setup_tools(self) -> ToolRegistry:
        """Регистрирует все доступные инструменты"""
        registry = ToolRegistry()
        
        # Shell команды
        shell_tool = ShellTool()
        registry.register("shell", shell_tool, shell_tool.description)
        
        # Работа с файлами
        file_tool = FileTool()
        registry.register("file", file_tool, file_tool.description)
        
        # Системная информация
        system_tool = SystemTool()
        registry.register("system", system_tool, system_tool.description)
        
        return registry
    
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
    
    def _on_hotkey(self):
        """Вызывается при нажатии на горячую клавишу"""
        self.floating_widget.show_at_cursor()
    
    
    def _open_dashboard(self):
        """Открывает дашборд"""
        if not self.dashboard.isVisible():
            self.dashboard.show()
        else:
            self.dashboard.hide()
        self.dashboard.raise_()
        self.dashboard.activateWindow()
    
    def _open_settings(self):
        """Открывает диалог настроек"""
        self.settings_dialog.exec()
    
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
        
        # Регистрируем горячую клавишу
        self.hotkey_manager.start()
        
        # Запускаем планировщик задач
        self.planner.start()
        
        # Запускаем обновление дашборда
        self.dashboard.start()
        
        # Включаем автозапуск если нужно
        if self.config.autostart:
            self.autostart_manager.enable()
        
        print("✅ Nevada запущён!")
        print(f"🎯 API модель: {self.config.model}")
        print(f"🌍 Язык: {self.config.language}")
        print(f"⌨️ Горячая клавиша: {self.config.hotkey}")
        print(f"🔧 Инструменты: {', '.join(self.tool_registry.list())}")
    
    def cleanup(self):
        """Очистка при завершении"""
        self.dashboard.stop()
        self.planner.close()
        self.hotkey_manager.stop()
        self.memory.close()
