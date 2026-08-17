"""
FloatingWidget — маленький виджет для быстрого ввода у курсора
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QLabel
from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtGui import QCursor, QFont
from config import Config
from agent.worker import AgentWorker
from ui.widgets import MessageBubble
from voice.voice_worker import ListenWorker


class FloatingWidget(QWidget):
    """Маленький виджет для быстрого ввода и просмотра последних сообщений"""

    def __init__(self, agent_loop=None, voice_manager=None, confirm_broker=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.voice_manager = voice_manager
        self.confirm_broker = confirm_broker
        self.worker = None
        self.listen_worker = None
        self._pending_listen = False
        self.is_expanded = False
        self.messages = []
        
        # Для перетаскивания
        self.drag_pos = None
        self.is_dragging = False
        
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.config.CARD};
                color: {self.config.TEXT_PRIMARY};
                font-family: "Segoe UI Variable", "Bahnschrift", "Segoe UI";
            }}
        """)
        
        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Заголовок с кнопкой закрытия
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 6, 6, 6)
        title_layout.setSpacing(0)
        
        title_label = QLabel("Nevada")
        title_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {self.config.INK};
                border: none;
                font-weight: bold;
                font-size: 10pt;
            }}
        """)
        title_label.setMaximumHeight(20)

        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.config.TEXT_MUTED};
                border: none;
                font-weight: bold;
                font-size: 12pt;
                padding: 0px;
            }}
            QPushButton:hover {{
                color: {self.config.DANGER};
            }}
        """)
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(title_label, 1)
        title_layout.addWidget(close_btn, 0)
        main_layout.addLayout(title_layout)
        
        # Основной content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(8)
        
        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите команду...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid #d8d1c5;
                border-radius: 12px;
                padding: 8px 11px;
                font-size: 9pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.config.ACCENT};
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
                border-radius: 11px;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 8pt;
            }}
            QPushButton:hover {{
                background-color: {self.config.ACCENT_DARK};
            }}
        """
        
        send_btn = QPushButton("📤")
        send_btn.setStyleSheet(btn_style)
        send_btn.setFixedSize(32, 32)
        send_btn.clicked.connect(self._send_message)
        
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setStyleSheet(btn_style)
        self.mic_btn.setFixedSize(32, 32)
        self.mic_btn.clicked.connect(self._on_mic_clicked)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(send_btn)
        
        content_layout.addLayout(input_layout)
        
        # Область для сообщений (скрыта по умолчанию)
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet(f"background-color: {self.config.CARD}; border: none;")
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(0)
        self.scroll.setVisible(False)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout()
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_container.setLayout(self.messages_layout)
        self.scroll.setWidget(self.messages_container)
        
        content_layout.addWidget(self.scroll)
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)
        self.setMaximumWidth(360)
        self.setMinimumHeight(60)

        if self.voice_manager:
            self.voice_manager.ready.connect(self._on_voice_ready)
            self.voice_manager.error.connect(self._on_voice_error)
    
    def mousePressEvent(self, event):
        """Обработчик нажатия мыши для начала перетаскивания"""
        # Если нажата левая кнопка мыши на заголовке
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 32:
            self.is_dragging = True
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Обработчик движения мыши для перетаскивания"""
        if self.is_dragging and self.drag_pos:
            new_pos = event.globalPosition().toPoint() - self.drag_pos
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Обработчик отпускания мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
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
            self.worker = AgentWorker(self.agent_loop, text, confirm_broker=self.confirm_broker)
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

    def _on_mic_clicked(self):
        """Нажатие на кнопку микрофона — push-to-talk"""
        if not self.voice_manager:
            self._add_message("❌ Голосовой ввод не настроен", is_user=False)
            return

        if self.listen_worker is not None:
            return  # уже слушаем/грузимся

        if not self.voice_manager.is_ready:
            self._pending_listen = True
            self.mic_btn.setText("⏳")
            self.voice_manager.ensure_loaded()
            return

        self._start_listening()

    def _start_listening(self):
        stt = self.voice_manager.stt
        if not stt or not stt.is_available():
            self._add_message("❌ Микрофон недоступен", is_user=False)
            self.mic_btn.setText("🎤")
            return

        self.mic_btn.setText("⏺")
        self._expand()
        self.listen_worker = ListenWorker(stt, max_duration=12)
        self.listen_worker.text_ready.connect(self._on_text_recognized)
        self.listen_worker.no_speech.connect(self._on_no_speech)
        self.listen_worker.error.connect(self._on_listen_error)
        self.listen_worker.start()

    def _on_voice_ready(self):
        if self._pending_listen:
            self._pending_listen = False
            self._start_listening()

    def _on_voice_error(self, message: str):
        self._pending_listen = False
        self.mic_btn.setText("🎤")
        self._add_message(f"❌ {message}", is_user=False)

    def _on_text_recognized(self, text: str):
        self.listen_worker = None
        self.mic_btn.setText("🎤")
        self.input_field.setText(text)
        self.input_field.setFocus()

    def _on_no_speech(self):
        self.listen_worker = None
        self.mic_btn.setText("🎤")

    def _on_listen_error(self, message: str):
        self.listen_worker = None
        self.mic_btn.setText("🎤")
        self._add_message(f"❌ {message}", is_user=False)

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
