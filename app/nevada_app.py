"""
NevadaApp — главный класс приложения
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, Qt
from pathlib import Path
from config import Config
from memory.manager import MemoryManager
from agent.loop import AgentLoop
from ui.main_window import MainWindow
from ui.floating import FloatingWidget
from ui.settings_dialog import SettingsDialog
from ui.hud_widget import HudWidget
from ui.confirm_dialog import ConfirmationBroker, show_confirm_dialog
from app.tray import TrayManager
from app.hotkey import HotkeyManager
from app.autostart import Autostart
from tools.registry import ToolRegistry
from tools.shell import ShellTool
from tools.file_tool import FileTool
from tools.system_tool import SystemTool
from tools.app_tool import AppTool
from tools.skill_tool import SkillTool
from tools.research_tool import ResearchTool
from scheduler.planner import DayPlanner
from voice.manager import VoiceManager


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

        # Голосовой ввод/вывод (STT + TTS), грузится лениво при первом использовании
        self.voice_manager = VoiceManager(language=self.config.language)

        # Настоящее подтверждение опасных действий: диалог с кнопками.
        # Сигнал приходит из потока агента, слот выполняется в UI-потоке.
        self.confirm_broker = ConfirmationBroker()
        self.confirm_broker.requested.connect(
            lambda request: show_confirm_dialog(request, self.main_window),
            Qt.ConnectionType.QueuedConnection,
        )

        # Главное окно приложения с вкладками
        self.main_window = MainWindow(
            agent_loop=self.agent_loop,
            memory=self.memory,
            planner=self.planner,
            tool_registry=self.tool_registry,
            voice_manager=self.voice_manager,
            confirm_broker=self.confirm_broker
        )

        # Плавающее окно для быстрого ввода
        self.floating_widget = FloatingWidget(agent_loop=self.agent_loop, voice_manager=self.voice_manager, confirm_broker=self.confirm_broker)

        # Jarvis HUD — голосовой режим
        self.hud_widget = HudWidget(agent_loop=self.agent_loop, voice_manager=self.voice_manager, confirm_broker=self.confirm_broker)

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

        # Управление программами: запуск, окна, ввод текста, поиск в браузере
        app_tool = AppTool(extra_programs=self._load_extra_programs())
        registry.register("app", app_tool, app_tool.description)

        # Поиск и чтение страниц в интернете
        research_tool = ResearchTool()
        registry.register("research", research_tool, research_tool.description)

        # Навыки — markdown-сценарии из папки skills/
        skill_tool = SkillTool()
        registry.register("skill", skill_tool, skill_tool.description)
        print(f"[OK] Навыков загружено: {len(skill_tool.manager.skills)}")

        return registry

    def _load_extra_programs(self) -> dict:
        """
        Читает пользовательский белый список программ из apps.json рядом с config.py.
        Формат: {"имя для агента": "команда или путь к exe"}
        """
        apps_path = Path(__file__).parent.parent / "apps.json"
        if not apps_path.exists():
            return {}

        try:
            import json
            with open(apps_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {str(k).lower(): str(v) for k, v in data.items()}
            print("⚠️  apps.json должен содержать объект вида {\"имя\": \"команда\"}")
        except Exception as e:
            print(f"⚠️  Не удалось прочитать apps.json: {e}")
        return {}
    
    def _setup_signals(self):
        """Подключает сигналы трея"""
        self.tray_manager.signals.open_chat.connect(self._show_main_window)
        self.tray_manager.signals.open_dashboard.connect(self._show_main_window)
        self.tray_manager.signals.open_settings.connect(self._open_settings)
        self.tray_manager.signals.open_hud.connect(self.hud_widget.toggle)
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

            # Прогреваем голосовой движок в фоне заранее, чтобы первое
            # нажатие на микрофон не "съедало" начало фразы во время загрузки
            self.voice_manager.ensure_loaded()

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
