"""
TrayManager — управление иконкой в системном трее
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject
from pathlib import Path


class TraySignals(QObject):
    """Сигналы для трея"""
    open_chat = pyqtSignal()
    open_dashboard = pyqtSignal()
    open_settings = pyqtSignal()
    quit_app = pyqtSignal()


class TrayManager(QSystemTrayIcon):
    """Иконка приложения в системном трее"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = TraySignals()
        
        # Пытаемся загрузить иконку
        icon_path = Path(__file__).parent.parent / "assets" / "nevada.ico"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        else:
            # Если иконки нет, используем стандартную иконку
            self.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        # Контекстное меню
        menu = QMenu()
        
        action_chat = QAction("💬 Открыть чат")
        action_chat.triggered.connect(self.signals.open_chat.emit)
        menu.addAction(action_chat)
        
        action_dashboard = QAction("📊 Дашборд")
        action_dashboard.triggered.connect(self.signals.open_dashboard.emit)
        menu.addAction(action_dashboard)
        
        action_settings = QAction("⚙️ Настройки")
        action_settings.triggered.connect(self.signals.open_settings.emit)
        menu.addAction(action_settings)
        
        menu.addSeparator()
        
        action_exit = QAction("❌ Выход")
        action_exit.triggered.connect(self.signals.quit_app.emit)
        menu.addAction(action_exit)
        
        self.setContextMenu(menu)
        
        # Одиночный клик по иконке
        self.activated.connect(self._on_tray_activated)
    
    def _on_tray_activated(self, reason):
        """Обработчик клика по иконке"""
        from PyQt6.QtWidgets import QSystemTrayIcon
        
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Одиночный клик
            self.signals.open_chat.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleTrigger:
            # Двойной клик
            self.signals.open_dashboard.emit()
    
    def show_notification(self, title: str, message: str, duration: int = 5000):
        """Показывает уведомление в системном трее"""
        self.showMessage(title, message, duration=duration)
