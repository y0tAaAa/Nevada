"""
ChatWindow — главное окно чата с кастомной шапкой и тёмной темой
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QScrollArea, QLabel, QPushButton, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
from config import Config
from agent.worker import AgentWorker


class TypingDots(QLabel):
    """Анимированный индикатор печати"""
    
    def __init__(self):
        super().__init__()
        self.setText("⠋")
        self.setStyleSheet("color: #3b82f6; font-size: 16px;")
        self.animation_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._animate)
        self.timer.start(80)
    
    def _animate(self):
        self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
        self.setText(self.animation_frames[self.current_frame])
    
    def stop(self):
        self.timer.stop()


class MessageBubble(QFrame):
    """Пузырь сообщения"""
    
    def __init__(self, text: str, is_user: bool):
        super().__init__()
        self.config = Config()
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 10))
        label.setStyleSheet(f"color: {self.config.TEXT_PRIMARY};")
        
        if is_user:
            # Сообщение пользователя справа
            layout.addStretch()
            self.setStyleSheet(f"background-color: {self.config.BG_MSG_USER}; border-radius: 8px;")
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            # Сообщение ассистента слева
            self.setStyleSheet(f"background-color: {self.config.BG_MSG_NEV}; border-radius: 8px;")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(label)
        if is_user:
            layout.addStretch()
        
        self.setLayout(layout)
        self.setMaximumWidth(600)


class AutoResizeEdit(QTextEdit):
    """Поле ввода, которое растёт до максимума"""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.setMaximumHeight(40)
        self.setMinimumHeight(40)
        self.max_height = 140
        
        # Стили
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 6px;
                padding: 8px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }}
        """)
        
        self.textChanged.connect(self._resize)
    
    def _resize(self):
        """Автоматически изменяет высоту"""
        doc = self.document()
        height = min(doc.size().height() + 10, self.max_height)
        self.setMaximumHeight(int(height))
    
    def keyPressEvent(self, event):
        """Enter = отправить, Shift+Enter = новая строка"""
        if event.key() == Qt.Key.Key_Return:
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_message.emit()
        else:
            super().keyPressEvent(event)
    
    send_message = pyqtSignal()


class TitleBar(QWidget):
    """Кастомная шапка окна"""
    
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.config = Config()
        self.drag_pos = None
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        title = QLabel("Nevada")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.config.TEXT_PRIMARY};")
        
        layout.addWidget(title)
        layout.addStretch()
        
        # Кнопки управления
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {self.config.TEXT_PRIMARY};
                border: none;
                width: 35px;
                height: 35px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {self.config.BORDER};
            }}
        """
        
        minimize_btn = QPushButton("−")
        minimize_btn.setFont(QFont("Arial", 14))
        minimize_btn.setStyleSheet(btn_style)
        minimize_btn.clicked.connect(lambda: window.showMinimized())
        
        maximize_btn = QPushButton("□")
        maximize_btn.setFont(QFont("Arial", 12))
        maximize_btn.setStyleSheet(btn_style)
        maximize_btn.clicked.connect(self._toggle_maximize)
        
        close_btn = QPushButton("×")
        close_btn.setFont(QFont("Arial", 16))
        close_btn.setStyleSheet(btn_style)
        close_btn.clicked.connect(lambda: window.hide())
        
        layout.addWidget(minimize_btn)
        layout.addWidget(maximize_btn)
        layout.addWidget(close_btn)
        
        self.maximize_btn = maximize_btn
        self.setLayout(layout)
        self.setStyleSheet(f"background-color: {self.config.BG_INPUT}; border-bottom: 1px solid {self.config.BORDER};")
    
    def _toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self.drag_pos)
    
    def mouseDoubleClickEvent(self, event):
        self._toggle_maximize()


class ChatWindow(QMainWindow):
    """Главное окно чата"""
    
    def __init__(self, agent_loop=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.worker = None
        
        self.setWindowTitle("Nevada — Ассистент")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Главный виджет
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Кастомная шапка
        title_bar = TitleBar(self)
        layout.addWidget(title_bar)
        
        # Область чата
        scroll = QScrollArea()
        scroll.setStyleSheet(f"background-color: {self.config.BG_WINDOW}; border: none;")
        scroll.setWidgetResizable(True)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(15, 15, 15, 15)
        self.chat_container.setLayout(self.chat_layout)
        scroll.setWidget(self.chat_container)
        
        layout.addWidget(scroll)
        
        # Нижняя панель (ввод)
        input_panel = QWidget()
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(8)
        
        self.input_field = AutoResizeEdit()
        self.input_field.send_message.connect(self._send_message)
        
        send_btn = QPushButton("📤 Отправить")
        send_btn.setFont(QFont("Segoe UI", 9))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        send_btn.clicked.connect(self._send_message)
        send_btn.setFixedSize(120, 40)
        
        mic_btn = QPushButton("🎤")
        mic_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.ACCENT};
                border: 1px solid {self.config.BORDER};
                border-radius: 6px;
                padding: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.config.BORDER};
            }}
        """)
        mic_btn.setFixedSize(40, 40)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(mic_btn)
        input_layout.addWidget(send_btn)
        input_panel.setLayout(input_layout)
        
        input_panel.setStyleSheet(f"background-color: {self.config.BG_WINDOW}; border-top: 1px solid {self.config.BORDER};")
        layout.addWidget(input_panel)
        
        central.setLayout(layout)
        central.setStyleSheet(f"background-color: {self.config.BG_WINDOW};")
    
    def add_message(self, text: str, is_user: bool = False):
        """Добавляет сообщение в чат"""
        bubble = MessageBubble(text, is_user)
        self.chat_layout.addWidget(bubble)
        self.chat_layout.addStretch()
    
    def append_text(self, text: str):
        """Добавляет текст к последнему сообщению (для streaming)"""
        # Если это первый токен - создаём новое сообщение
        if not hasattr(self, '_last_message_label'):
            self.add_message("", is_user=False)
            self._last_message_label = self.chat_layout.itemAt(self.chat_layout.count() - 2).widget().findChild(QLabel)
        
        if self._last_message_label:
            self._last_message_label.setText(self._last_message_label.text() + text)
    
    def _send_message(self):
        """Отправляет сообщение на обработку"""
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        # Добавляем сообщение пользователя
        self.add_message(text, is_user=True)
        self.input_field.clear()
        
        # Показываем индикатор печати
        typing = TypingDots()
        self.chat_layout.addWidget(typing)
        self.chat_layout.addStretch()
        
        # Отправляем агенту в отдельном потоке
        if self.agent_loop:
            self.worker = AgentWorker(self.agent_loop, text)
            self.worker.thinking_received.connect(lambda t: self._on_thinking(t, typing))
            self.worker.token_received.connect(lambda tok: self._on_token(tok, typing))
            self.worker.response_ready.connect(lambda resp: self._on_response_ready(resp, typing))
            self.worker.error_occurred.connect(lambda err: self._on_error(err, typing))
            self.worker.start()
        else:
            typing.stop()
            self.add_message("❌ Агент не инициализирован", is_user=False)
    
    def _on_thinking(self, thinking_text: str, typing_widget):
        """Обработчик промежуточного размышления"""
        if not hasattr(self, '_thinking_label'):
            # Первый раз - создаём thinking сообщение
            try:
                if typing_widget and typing_widget.isVisible():
                    typing_widget.stop()
                    typing_widget.deleteLater()
            except:
                pass
            self.add_message("", is_user=False)
            self._thinking_label = self.chat_layout.itemAt(self.chat_layout.count() - 2).widget().findChild(QLabel)
            self._thinking_label.setStyleSheet(f"color: #888888; font-style: italic; padding: 8px; border-left: 3px solid #3b82f6;")
        
        if self._thinking_label:
            if thinking_text == "":
                # Очищаем thinking
                delattr(self, '_thinking_label')
            else:
                self._thinking_label.setText(self._thinking_label.text() + thinking_text)
    
    def _on_token(self, token: str, typing_widget):
        """Обработчик получения токена"""
        if not hasattr(self, '_streaming_message'):
            try:
                if typing_widget and typing_widget.isVisible():
                    typing_widget.stop()
                    typing_widget.deleteLater()
            except:
                pass
            self.add_message("", is_user=False)
            self._streaming_message = self.chat_layout.itemAt(self.chat_layout.count() - 2).widget().findChild(QLabel)
        
        if self._streaming_message:
            self._streaming_message.setText(self._streaming_message.text() + token)
    
    def _on_response_ready(self, response: str, typing_widget):
        """Ответ получен полностью"""
        if hasattr(self, '_streaming_message'):
            delattr(self, '_streaming_message')
        if typing_widget:
            try:
                typing_widget.stop()
                typing_widget.deleteLater()
            except:
                pass
    
    def _on_error(self, error: str, typing_widget):
        """Ошибка при выполнении"""
        if typing_widget:
            try:
                typing_widget.stop()
                typing_widget.deleteLater()
            except:
                pass
        self.add_message(error, is_user=False)
