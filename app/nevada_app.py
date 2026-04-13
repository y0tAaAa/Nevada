"""
NevadaApp — главный класс приложения
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject
from pathlib import Path
from config import Config
from memory.manager import MemoryManager
from agent.loop import AgentLoop
from ui.main_window import MainWindow
from ui.floating import FloatingWidget
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
        
        # Инициализируем инструменты
        self.tool_registry = self._setup_tools()
        
        # Инициализируем компоненты
        self.memory = MemoryManager(self.config.db_path)
        self.agent_loop = AgentLoop(self.memory, tool_registry=self.tool_registry)
        
        # Планировщик задач
        self.planner = DayPlanner(db_path=self.config.db_path)
        
        # Главное окно приложения с вкладками
        self.main_window = MainWindow(
            agent_loop=self.agent_loop,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.tool_registry
        )
        
        # Плавающее окно для быстрого ввода
        self.floating_widget = FloatingWidget(agent_loop=self.agent_loop)
        
        # Диалог настроек
        self.settings_dialog = SettingsDialog(config=self.config)
        
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
    
    def _setup_signals(self):
        """Подключает сигналы трея"""
        self.tray_manager.signals.open_chat.connect(self._show_main_window)
        self.tray_manager.signals.open_dashboard.connect(self._show_main_window)
        self.tray_manager.signals.open_settings.connect(self._open_settings)
        self.tray_manager.signals.quit_app.connect(self._quit_app)
    
    def _show_main_window(self):
        """Показывает главное окно"""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        elif not self.main_window.isVisible():
            self.main_window.show()
        else:
            self.main_window.hide()
        self.main_window.raise_()
        self.main_window.activateWindow()
    
    def _on_hotkey(self):
        """Вызывается при нажатии на горячую клавишу"""
        self.floating_widget.show_at_cursor()
    
    def _open_settings(self):
        """Открывает диалог настроек"""
        self.settings_dialog.exec()
    
    def _quit_app(self):
        """Завершает приложение"""
        self.memory.close()
        self.app.quit()
    
    def start(self):
        """Запускает приложение"""
        try:
            # Проверяем конфиг
            if not self.config.validate():
                print("[ERROR] Ошибка конфигурации. Пожалуйста, проверьте .env файл")
                return False
            
            # Показываем трей
            self.tray_manager.show()
            
            # Показываем главное окно по умолчанию
            self._show_main_window()
            
            # Регистрируем горячую клавишу
            self.hotkey_manager.start()
            
            # Запускаем планировщик задач
            self.planner.start()
            
            # Включаем автозапуск если нужно
            if self.config.autostart:
                self.autostart_manager.enable()
            
            print("[OK] Nevada запущена!")
            print(f"Model: {self.config.model}")
            print(f"Language: {self.config.language}")
            print(f"Hotkey: {self.config.hotkey}")
            print(f"Tools: {', '.join(self.tool_registry.list())}")
            
            return True
        
        except Exception as e:
            print(f"[ERROR] Ошибка запуска приложения: {e}")
            return False
    
    def cleanup(self):
        """Очистка при завершении"""
        self.planner.close()
        self.hotkey_manager.stop()
        self.memory.close()
