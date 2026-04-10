"""
Dashboard — информационная панель с задачами, историей и статусом
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from config import Config


class DashboardPanel(QFrame):
    """Панель в дашборде"""
    
    def __init__(self, title: str):
        super().__init__()
        self.config = Config()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.config.ACCENT};")
        
        layout.addWidget(title_label)
        
        # Области содержимого
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        layout.addLayout(self.content_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.config.BG_INPUT};
                border: 1px solid {self.config.BORDER};
                border-radius: 8px;
            }}
        """)


class Dashboard(QMainWindow):
    """Главная информационная панель"""
    
    def __init__(self, memory=None, planner=None, tool_registry=None):
        super().__init__()
        self.config = Config()
        self.memory = memory
        self.planner = planner
        self.tool_registry = tool_registry
        
        self.setWindowTitle("Nevada — Дашборд")
        self.setGeometry(200, 200, 1000, 600)
        self.setStyleSheet(f"background-color: {self.config.BG_WINDOW};")
        
        # Главный виджет
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title = QLabel("📊 Nevada Дашборд")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.config.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        # Три колонки
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        
        # Колонка 1: Задачи на сегодня
        self.tasks_panel = DashboardPanel("📋 Задачи на сегодня")
        columns_layout.addWidget(self.tasks_panel)
        
        # Колонка 2: История диалогов
        self.history_panel = DashboardPanel("💬 История диалогов")
        columns_layout.addWidget(self.history_panel)
        
        # Колонка 3: Статус системы
        self.status_panel = DashboardPanel("⚙️ Статус системы")
        columns_layout.addWidget(self.status_panel)
        
        layout.addLayout(columns_layout)
        central.setLayout(layout)
        
        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_all)
        
        # Метрики
        self.start_time = datetime.now()
        self.request_count = 0
    
    def _update_all(self):
        """Обновляет все панели"""
        self._update_tasks()
        self._update_history()
        self._update_status()
    
    def _update_tasks(self):
        """Обновляет панель задач"""
        # Очищаем содержимое
        while self.tasks_panel.content_layout.count():
            self.tasks_panel.content_layout.takeAt(0).widget().deleteLater()
        
        if self.planner:
            tasks = self.planner.get_today()
            if tasks:
                for task in tasks[:5]:  # Показываем первые 5
                    task_label = QLabel(f"✓ {task.get('title', 'Без названия')}")
                    task_label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY}; padding: 4px;")
                    self.tasks_panel.content_layout.addWidget(task_label)
            else:
                empty = QLabel("Нет задач на сегодня")
                empty.setStyleSheet(f"color: #888888; padding: 4px;")
                self.tasks_panel.content_layout.addWidget(empty)
        else:
            info = QLabel("📅 Планировщик недоступен")
            info.setStyleSheet(f"color: #888888; padding: 4px;")
            self.tasks_panel.content_layout.addWidget(info)
    
    def _update_history(self):
        """Обновляет панель истории"""
        # Очищаем содержимое
        while self.history_panel.content_layout.count():
            self.history_panel.content_layout.takeAt(0).widget().deleteLater()
        
        if self.memory:
            messages = self.memory.get_all()
            
            # Показываем только диалоги (пары сообщений)
            dialogs = []
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    user_msg = messages[i].get('content', '')[:50]
                    dialogs.append(user_msg)
            
            if dialogs:
                for dialog in dialogs[-10:]:  # Последние 10
                    dialog_label = QLabel(f"💬 {dialog}...")
                    dialog_label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY}; padding: 4px;")
                    dialog_label.setWordWrap(True)
                    self.history_panel.content_layout.addWidget(dialog_label)
            else:
                empty = QLabel("Нет истории диалогов")
                empty.setStyleSheet(f"color: #888888; padding: 4px;")
                self.history_panel.content_layout.addWidget(empty)
        else:
            info = QLabel("💾 Память недоступна")
            info.setStyleSheet(f"color: #888888; padding: 4px;")
            self.history_panel.content_layout.addWidget(info)
    
    def _update_status(self):
        """Обновляет панель статуса"""
        # Очищаем содержимое
        while self.status_panel.content_layout.count():
            self.status_panel.content_layout.takeAt(0).widget().deleteLater()
        
        # Аптайм
        uptime = datetime.now() - self.start_time
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        uptime_label = QLabel(f"⏱️  Аптайм: {hours}ч {minutes}м")
        uptime_label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY}; padding: 4px;")
        self.status_panel.content_layout.addWidget(uptime_label)
        
        # API модель
        model_label = QLabel(f"🤖 Модель: {self.config.model}")
        model_label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY}; padding: 4px;")
        self.status_panel.content_layout.addWidget(model_label)
        
        # Язык интерфейса
        lang_label = QLabel(f"🌍 Язык: {self.config.language.upper()}")
        lang_label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY}; padding: 4px;")
        self.status_panel.content_layout.addWidget(lang_label)
        
        # Инструменты
        if self.tool_registry:
            tools = ", ".join(self.tool_registry.list())
            tools_label = QLabel(f"🔧 Инструменты: {tools}")
            tools_label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY}; padding: 4px;")
            tools_label.setWordWrap(True)
            self.status_panel.content_layout.addWidget(tools_label)
    
    def start(self):
        """Начинает обновление панелей"""
        self._update_all()
        self.update_timer.start(30000)  # Обновляем каждые 30 секунд
    
    def stop(self):
        """Останавливает обновление"""
        self.update_timer.stop()
