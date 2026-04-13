"""
MainWindow — главное окно приложения с вкладками
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTabWidget, QCalendarWidget, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QColor
from datetime import datetime, timedelta
from config import Config
from agent.worker import AgentWorker
from ui.chat_window import MessageBubble


class CalendarTab(QWidget):
    """Вкладка календаря с возможностью просмотра задач на день"""
    
    def __init__(self, memory=None, planner=None):
        super().__init__()
        self.config = Config()
        self.memory = memory
        self.planner = planner
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Календарь
        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                alternate-background-color: {self.config.BG_WINDOW};
                gridline-color: {self.config.BORDER};
            }}
            QCalendarWidget QToolButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
                margin: 2px;
            }}
            QCalendarWidget QMenu {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
            }}
        """)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        
        layout.addWidget(self.calendar, 1)
        
        # Задачи на выбранный день
        tasks_label = QLabel("📋 Задачи на день:")
        tasks_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        tasks_label.setStyleSheet(f"color: {self.config.ACCENT};")
        layout.addWidget(tasks_label)
        
        self.tasks_list = QListWidget()
        self.tasks_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {self.config.ACCENT};
            }}
        """)
        layout.addWidget(self.tasks_list)
        
        # Кнопка добавления задачи
        add_task_btn = QPushButton("➕ Добавить задачу")
        add_task_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        layout.addWidget(add_task_btn)
        
        self.setLayout(layout)
        self._on_date_selected()
    
    def _on_date_selected(self):
        """Обновляет список задач для выбранной даты"""
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString(Qt.DateFormat.ISODate)
        
        self.tasks_list.clear()
        
        if self.planner:
            tasks = self.planner.get_tasks_by_date(date_str)
            if tasks:
                for task in tasks:
                    item = QListWidgetItem(f"📌 {task['title']}")
                    if task.get('done'):
                        item.setText(f"✅ {task['title']}")
                    self.tasks_list.addItem(item)
            else:
                item = QListWidgetItem("Нет задач на этот день")
                item.setForeground(QColor("#888888"))
                self.tasks_list.addItem(item)


class ChatTab(QWidget):
    """Вкладка чата"""
    
    def __init__(self, agent_loop=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.worker = None
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Область сообщений
        self.chat_scroll = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setSpacing(8)
        self.chat_layout.setContentsMargins(15, 15, 15, 15)
        self.chat_scroll.setLayout(self.chat_layout)
        
        scroll_area = QWidget()
        scroll_area.setStyleSheet(f"background-color: {self.config.BG_WINDOW};")
        scroll_wrapper = QVBoxLayout()
        scroll_wrapper.addWidget(self.chat_scroll)
        scroll_wrapper.addStretch()
        scroll_area.setLayout(scroll_wrapper)
        
        layout.addWidget(scroll_area, 1)
        
        # Ввод сообщения
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(15, 10, 15, 15)
        input_layout.setSpacing(8)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите сообщение...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 4px;
                padding: 8px;
                font-size: 10pt;
            }}
        """)
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self._send_message)
        
        send_btn = QPushButton("📤")
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        send_btn.setFixedSize(40, 40)
        send_btn.clicked.connect(self._send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
    
    def _send_message(self):
        """Отправляет сообщение"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.input_field.clear()
        self._add_message(text, is_user=True)
        
        if self.agent_loop:
            self.worker = AgentWorker(self.agent_loop, text)
            self.worker.token_received.connect(self._on_token)
            self.worker.response_ready.connect(self._on_response_ready)
            self.worker.error_occurred.connect(lambda err: self._add_message(err, is_user=False))
            self.worker.start()
    
    def _add_message(self, text: str, is_user: bool = False):
        """Добавляет сообщение в чат"""
        bubble = MessageBubble(text, is_user)
        self.chat_layout.addWidget(bubble)
    
    def _on_token(self, token: str):
        """Получен токен"""
        if not hasattr(self, '_streaming_label'):
            self._add_message("", is_user=False)
            from PyQt6.QtWidgets import QLabel
            self._streaming_label = self.chat_layout.itemAt(self.chat_layout.count() - 1).widget().findChild(QLabel)
        
        if hasattr(self, '_streaming_label') and self._streaming_label:
            self._streaming_label.setText(self._streaming_label.text() + token)
    
    def _on_response_ready(self, response: str):
        """Ответ готов"""
        if hasattr(self, '_streaming_label'):
            delattr(self, '_streaming_label')


class HistoryTab(QWidget):
    """Вкладка истории диалогов"""
    
    def __init__(self, memory=None):
        super().__init__()
        self.config = Config()
        self.memory = memory
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("📜 История диалогов")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.config.ACCENT};")
        layout.addWidget(title)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 4px;
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {self.config.BORDER};
            }}
        """)
        layout.addWidget(self.history_list)
        
        self._refresh_history()
        
        # Кнопка очистки
        clear_btn = QPushButton("🗑️ Очистить историю")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #dc2626;
            }}
        """)
        layout.addWidget(clear_btn)
        
        self.setLayout(layout)
    
    def _refresh_history(self):
        """Обновляет список истории"""
        self.history_list.clear()
        if self.memory:
            history = self.memory.get_recent(n=50)
            if history:
                for msg in history:
                    if msg['role'] == 'user':
                        item = QListWidgetItem(f"👤 {msg['content'][:60]}...")
                        self.history_list.addItem(item)


class MainWindow(QMainWindow):
    """Главное окно приложения Nevada"""
    
    def __init__(self, agent_loop=None, memory=None, planner=None, tool_registry=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.memory = memory
        self.planner = planner
        self.tool_registry = tool_registry
        
        self.setWindowTitle("Nevada — Desktop Assistant")
        self.setWindowIcon(QIcon())
        self.setStyleSheet(f"background-color: {self.config.BG_WINDOW}; color: {self.config.TEXT_PRIMARY};")
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Заголовок
        header = QWidget()
        header.setStyleSheet(f"background-color: {self.config.BG_INPUT}; border-bottom: 1px solid {self.config.BORDER};")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title_label = QLabel("🤖 Nevada")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.config.ACCENT};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget {{
                background-color: {self.config.BG_WINDOW};
                border: none;
            }}
            QTabBar {{
                background-color: {self.config.BG_INPUT};
                border-bottom: 1px solid {self.config.BORDER};
            }}
            QTabBar::tab {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                padding: 10px 20px;
                margin-right: 2px;
                border: none;
            }}
            QTabBar::tab:selected {{
                background-color: {self.config.ACCENT};
                color: white;
                border-radius: 4px 4px 0 0;
            }}
        """)
        
        # Вкладка Чата
        self.chat_tab = ChatTab(agent_loop=self.agent_loop)
        self.tabs.addTab(self.chat_tab, "💬 Чат")
        
        # Вкладка Календаря
        self.calendar_tab = CalendarTab(memory=self.memory, planner=self.planner)
        self.tabs.addTab(self.calendar_tab, "📅 Календарь")
        
        # Вкладка Истории
        self.history_tab = HistoryTab(memory=self.memory)
        self.tabs.addTab(self.history_tab, "📜 История")
        
        layout.addWidget(self.tabs, 1)
        
        central_widget.setLayout(layout)
        
        # Размеры окна
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)
        
        # Центрируем окно на экране
        from PyQt6.QtGui import QScreen
        screen = self.screen().availableGeometry()
        self.move(
            screen.left() + (screen.width() - self.width()) // 2,
            screen.top() + (screen.height() - self.height()) // 2
        )
