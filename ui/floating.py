"""
FloatingWidget — маленький виджет для быстрого ввода у курсора
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QCursor, QFont
from config import Config
from agent.worker import AgentWorker
from ui.chat_window import MessageBubble


class FloatingWidget(QWidget):
    """Маленький виджет для быстрого ввода и просмотра последних сообщений"""
    
    def __init__(self, agent_loop=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.worker = None
        self.is_expanded = False
        self.messages = []
        
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(f"background-color: {self.config.BG_WINDOW};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите команду...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 4px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 9pt;
            }}
        """)
        self.input_field.setMinimumWidth(300)
        self.input_field.returnPressed.connect(self._send_message)
        
        # Кнопки
        btn_style = f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 8pt;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """
        
        send_btn = QPushButton("📤")
        send_btn.setStyleSheet(btn_style)
        send_btn.setFixedSize(32, 32)
        send_btn.clicked.connect(self._send_message)
        
        mic_btn = QPushButton("🎤")
        mic_btn.setStyleSheet(btn_style)
        mic_btn.setFixedSize(32, 32)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(mic_btn)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # Область для сообщений (скрыта по умолчанию)
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet(f"background-color: {self.config.BG_WINDOW}; border: none;")
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(0)
        self.scroll.setVisible(False)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout()
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_container.setLayout(self.messages_layout)
        self.scroll.setWidget(self.messages_container)
        
        layout.addWidget(self.scroll)
        
        self.setLayout(layout)
        self.setMaximumWidth(360)
        self.setMinimumHeight(60)
    
    def show_at_cursor(self):
        """Показывает виджет у позиции курсора"""
        cursor_pos = QCursor.pos()
        self.move(cursor_pos.x() - 180, cursor_pos.y() - 30)
        self.show()
        self.activateWindow()
        self.input_field.setFocus()
        self.input_field.selectAll()
    
    def _send_message(self):
        """Отправляет сообщение"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.input_field.clear()
        
        # Добавляем сообщение пользователя
        self._add_message(text, is_user=True)
        
        # Отправляем агенту
        if self.agent_loop:
            self.worker = AgentWorker(self.agent_loop, text)
            self.worker.token_received.connect(self._on_token)
            self.worker.response_ready.connect(self._on_response_ready)
            self.worker.error_occurred.connect(lambda err: self._add_message(err, is_user=False))
            self.worker.start()
            
            # Разворачиваем виджет
            self._expand()
        else:
            self._add_message("❌ Агент не инициализирован", is_user=False)
    
    def _add_message(self, text: str, is_user: bool = False):
        """Добавляет сообщение"""
        # Ограничиваем к 3 сообщениям
        while len(self.messages) >= 6:  # 3 пары
            widget = self.messages_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
            self.messages.pop(0)
        
        bubble = MessageBubble(text, is_user)
        self.messages_layout.addWidget(bubble)
        self.messages.append((text, is_user))
        
        # Прокручиваем вниз
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )
    
    def _on_token(self, token: str):
        """Получен токен от агента"""
        if not hasattr(self, '_streaming_label'):
            self._add_message("", is_user=False)
            from PyQt6.QtWidgets import QLabel
            self._streaming_label = self.messages_layout.itemAt(self.messages_layout.count() - 1).widget().findChild(QLabel)
        
        if hasattr(self, '_streaming_label') and self._streaming_label:
            self._streaming_label.setText(self._streaming_label.text() + token)
    
    def _on_response_ready(self, response: str):
        """Ответ готов"""
        if hasattr(self, '_streaming_label'):
            delattr(self, '_streaming_label')
    
    def _expand(self):
        """Разворачивает виджет для показа сообщений"""
        if not self.is_expanded:
            self.is_expanded = True
            self.scroll.setVisible(True)
            self.scroll.setMaximumHeight(300)
            self.setMinimumHeight(400)
    
    def _collapse(self):
        """Сворачивает виджет"""
        if self.is_expanded:
            self.is_expanded = False
            self.scroll.setVisible(False)
            self.scroll.setMaximumHeight(0)
            self.setMinimumHeight(60)
    
    def focusOutEvent(self, event):
        """Закрывает виджет при потере фокуса"""
        self.hide()
        self._collapse()
        super().focusOutEvent(event)
    
    def keyPressEvent(self, event):
        """Закрывает на Escape"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self._collapse()
        else:
            super().keyPressEvent(event)
