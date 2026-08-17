"""
MainWindow — frameless-окно с боковой навигацией (тёмная тема)
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QCalendarWidget, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QDialog, QCheckBox, QScrollArea, QFrame,
    QMessageBox, QSizeGrip
)
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor
from datetime import datetime, timedelta
from pathlib import Path
from config import Config
from agent.worker import AgentWorker
from ui.widgets import MessageBubble, ToolResultCard
from ui.commands_page import CommandsPage
from voice.voice_worker import ListenWorker


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
                background-color: {self.config.CARD};
                color: {self.config.TEXT_PRIMARY};
                alternate-background-color: {self.config.CARD};
                gridline-color: {self.config.BORDER};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {self.config.CARD};
                border-bottom: 1px solid {self.config.BORDER};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: {self.config.CARD};
                color: {self.config.TEXT_PRIMARY};
                selection-background-color: {self.config.ACCENT};
                selection-color: #ffffff;
                outline: none;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: #545b7d;
            }}
            QCalendarWidget QToolButton {{
                background-color: transparent;
                color: {self.config.INK};
                border: none;
                border-radius: 10px;
                padding: 6px 10px;
                margin: 3px;
                font-weight: bold;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: rgba(124, 140, 248, 0.14);
                color: {self.config.ACCENT};
            }}
            QCalendarWidget QMenu {{
                background-color: {self.config.CARD};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 8px;
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
                background-color: {self.config.CARD};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 14px;
                padding: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 10px;
            }}
            QListWidget::item:hover {{
                background-color: {self.config.BG_INPUT};
            }}
            QListWidget::item:selected {{
                background-color: {self.config.ACCENT};
                color: #ffffff;
            }}
        """)
        layout.addWidget(self.tasks_list)

        # Кнопка добавления задачи
        add_task_btn = QPushButton("➕ Добавить задачу")
        add_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_task_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.config.ACCENT_DARK};
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
                item.setForeground(QColor(self.config.TEXT_MUTED))
                self.tasks_list.addItem(item)


class ChatTab(QWidget):
    """Вкладка чата"""

    def __init__(self, agent_loop=None, voice_manager=None, confirm_broker=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.voice_manager = voice_manager
        self.confirm_broker = confirm_broker
        self.worker = None
        self.listen_worker = None
        self._pending_listen = False
        self._streaming_bubble = None
        self._autoscroll = True
        
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # «Hero» — градиентная полоса с крупным приветствием
        layout.addWidget(self._build_hero())

        # Оболочка чата — карточка со скруглением
        shell = QWidget()
        shell.setObjectName("chatShell")
        shell.setStyleSheet(f"""
            QWidget#chatShell {{
                background-color: {self.config.CARD};
                border: 1px solid {self.config.BORDER};
                border-radius: 18px;
            }}
        """)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Область сообщений — настоящий QScrollArea (раньше был обычный QWidget,
        # из-за чего лента сообщений уезжала за пределы окна и обрезалась)
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(12)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.addStretch()  # прижимаем сообщения к низу

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.chat_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #39406a;
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #4b5488; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        # Автопрокрутка: диапазон скролла пересчитывается уже ПОСЛЕ вставки виджета,
        # поэтому прокручиваем по rangeChanged, а не сразу после добавления сообщения
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.rangeChanged.connect(self._on_scroll_range_changed)
        scrollbar.valueChanged.connect(self._on_scroll_value_changed)

        shell_layout.addWidget(self.scroll_area, 1)

        # Строка ввода
        input_row = QWidget()
        input_row.setStyleSheet(f"border-top: 1px solid {self.config.BORDER}; background: transparent;")
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(14, 12, 14, 12)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите сообщение...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 14px;
                padding: 11px 13px;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.config.ACCENT};
            }}
        """)
        self.input_field.setMinimumHeight(44)
        self.input_field.returnPressed.connect(self._send_message)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.ACCENT};
                border: 1px solid {self.config.BORDER};
                border-radius: 14px;
                font-size: 12pt;
            }}
            QPushButton:hover {{ background-color: {self.config.BORDER}; }}
        """)
        self.mic_btn.setFixedSize(44, 44)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self._on_mic_clicked)

        send_btn = QPushButton("Отправить")
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.config.ACCENT_DARK}; }}
        """)
        send_btn.setMinimumHeight(44)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._send_message)

        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(send_btn)
        shell_layout.addWidget(input_row)

        layout.addWidget(shell, 1)
        self.setLayout(layout)

        if self.voice_manager:
            self.voice_manager.ready.connect(self._on_voice_ready)
            self.voice_manager.error.connect(self._on_voice_error)

    def _build_hero(self) -> QWidget:
        """Градиентный баннер с крупным приветствием по времени суток"""
        hero = QWidget()
        hero.setFixedHeight(128)
        hero.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self.config.HERO_FROM},
                    stop:0.55 {self.config.HERO_MID},
                    stop:1 {self.config.HERO_TO}
                );
                border-radius: 18px;
            }}
        """)

        inner = QVBoxLayout(hero)
        inner.setContentsMargins(26, 20, 26, 20)
        inner.setSpacing(8)

        hour = datetime.now().hour
        if hour < 6:
            greeting = "Доброй ночи"
        elif hour < 12:
            greeting = "Доброе утро"
        elif hour < 18:
            greeting = "Добрый день"
        else:
            greeting = "Добрый вечер"

        title = QLabel(f"{greeting}. Чем помочь?")
        title.setFont(QFont("Segoe UI", 23, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; background: transparent;")
        inner.addWidget(title)

        subtitle = QLabel("Спросите о системе, файлах или задачах — и я выполню это на компьютере.")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.80); background: transparent;")
        inner.addWidget(subtitle)

        inner.addStretch()
        return hero

    def _send_message(self):
        """Отправляет сообщение"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        self.input_field.clear()
        self._add_message(text, is_user=True)
        
        if self.agent_loop:
            self.worker = AgentWorker(self.agent_loop, text, confirm_broker=self.confirm_broker)
            self.worker.token_received.connect(self._on_token)
            self.worker.tool_result.connect(self._on_tool_result)
            self.worker.response_ready.connect(self._on_response_ready)
            self.worker.error_occurred.connect(lambda err: self._add_message(err, is_user=False))
            self.worker.start()
    
    def _add_message(self, text: str, is_user: bool = False) -> MessageBubble:
        """Добавляет сообщение в чат перед финальным stretch"""
        bubble = MessageBubble(text, is_user)
        # Вставляем перед stretch, чтобы лента прижималась к низу
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._autoscroll = True  # новое сообщение — всегда показываем его
        return bubble

    def _on_scroll_range_changed(self, _min: int, maximum: int):
        """Диапазон вырос (добавилось сообщение) — держим ленту внизу"""
        if self._autoscroll:
            self.scroll_area.verticalScrollBar().setValue(maximum)

    def _on_scroll_value_changed(self, value: int):
        """Если пользователь отлистал вверх — не дёргаем ленту обратно вниз"""
        bar = self.scroll_area.verticalScrollBar()
        self._autoscroll = value >= bar.maximum() - 40

    def _scroll_to_bottom(self):
        """Принудительно прокручивает ленту сообщений вниз"""
        self._autoscroll = True
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_token(self, token: str):
        """Получен токен — дописываем его в текущий пузырь ответа"""
        if self._streaming_bubble is None:
            self._streaming_bubble = self._add_message("", is_user=False)

        self._streaming_bubble.append_text(token)

    def _on_tool_result(self, tool_name: str, result: str):
        """Инструмент отработал — показываем его РЕАЛЬНЫЙ вывод отдельной карточкой"""
        card = ToolResultCard(tool_name, result)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, card)
        self._autoscroll = True
        # Дальнейший текст модели пойдёт в новый пузырь, а не в тот, что был до вызова
        self._streaming_bubble = None

    def _on_response_ready(self, response: str):
        """Ответ готов"""
        self._streaming_bubble = None
        self._scroll_to_bottom()

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
                background-color: {self.config.CARD};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 14px;
                padding: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 10px;
            }}
            QListWidget::item:hover {{
                background-color: {self.config.BG_INPUT};
            }}
        """)
        layout.addWidget(self.history_list)
        
        self._refresh_history()
        
        # Кнопка очистки
        clear_btn = QPushButton("🗑️ Очистить историю")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.CARD};
                color: {self.config.DANGER};
                border: 1px solid rgba(248, 113, 113, 0.35);
                border-radius: 12px;
                padding: 11px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(248, 113, 113, 0.12);
                border-color: rgba(248, 113, 113, 0.6);
            }}
        """)
        clear_btn.clicked.connect(self._clear_history)
        layout.addWidget(clear_btn)
        
        self.setLayout(layout)
    
    def _refresh_history(self):
        """Обновляет список истории"""
        self.history_list.clear()
        if not self.memory:
            return

        history = self.memory.get_recent(n=50)
        if not history:
            item = QListWidgetItem("История пуста")
            item.setForeground(QColor(self.config.TEXT_MUTED))
            self.history_list.addItem(item)
            return

        for msg in history:
            content = " ".join(msg["content"].split())
            preview = content[:70] + ("…" if len(content) > 70 else "")
            prefix = "👤" if msg["role"] == "user" else "🤖"
            item = QListWidgetItem(f"{prefix}  {preview}")
            if msg["role"] != "user":
                item.setForeground(QColor(self.config.TEXT_MUTED))
            self.history_list.addItem(item)

    def _clear_history(self):
        """Очищает историю диалогов после подтверждения"""
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Очистить историю")
        confirm.setText("Удалить всю историю диалогов?")
        confirm.setIcon(QMessageBox.Icon.Question)
        yes_btn = confirm.addButton("Удалить", QMessageBox.ButtonRole.AcceptRole)
        confirm.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        confirm.exec()

        if confirm.clickedButton() is yes_btn and self.memory:
            self.memory.clear()
            self._refresh_history()


class MainWindow(QMainWindow):
    """Главное окно приложения Nevada"""
    
    def __init__(self, agent_loop=None, memory=None, planner=None, tool_registry=None, voice_manager=None, confirm_broker=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.memory = memory
        self.planner = planner
        self.tool_registry = tool_registry
        self.voice_manager = voice_manager
        self.confirm_broker = confirm_broker

        self.setWindowTitle("Nevada — Desktop Assistant")
        icon_path = Path(__file__).parent.parent / "assets" / "nevada.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Frameless-окно вместо стандартной рамки Windows
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None

        self.setStyleSheet(f"""
            QWidget {{
                color: {self.config.TEXT_PRIMARY};
                font-family: "Segoe UI Variable", "Bahnschrift", "Segoe UI";
            }}
        """)

        # Корневой контейнер со скруглением и рамкой
        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet(f"""
            QWidget#root {{
                background-color: {self.config.BG_WINDOW};
                border: 1px solid {self.config.BORDER};
                border-radius: 14px;
            }}
        """)
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_title_bar())

        # Тело: боковая навигация + страницы
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.pages = QStackedWidget()
        self.chat_tab = ChatTab(agent_loop=self.agent_loop, voice_manager=self.voice_manager, confirm_broker=self.confirm_broker)
        self.commands_page = CommandsPage(tool_registry=self.tool_registry)
        self.commands_page.example_chosen.connect(self._use_example)
        self.calendar_tab = CalendarTab(memory=self.memory, planner=self.planner)
        self.history_tab = HistoryTab(memory=self.memory)
        for page in (self.chat_tab, self.commands_page, self.calendar_tab, self.history_tab):
            self.pages.addWidget(page)

        body.addWidget(self._build_sidebar())
        body.addWidget(self.pages, 1)
        root_layout.addLayout(body, 1)

        # Уголок для изменения размера (frameless окно теряет системный ресайз)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 6, 6)
        grip_row.addStretch()
        grip = QSizeGrip(root)
        grip.setFixedSize(16, 16)
        grip_row.addWidget(grip)
        root_layout.addLayout(grip_row)

        self._select_page(0)

        # Размеры окна
        self.resize(1060, 720)
        self.setMinimumSize(860, 600)

        screen = self.screen().availableGeometry()
        self.move(
            screen.left() + (screen.width() - self.width()) // 2,
            screen.top() + (screen.height() - self.height()) // 2
        )

    # --- Кастомная шапка ---

    def _build_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: transparent; border-bottom: 1px solid {self.config.BORDER};")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {self.config.ACCENT}; background: transparent; font-size: 11pt;")
        layout.addWidget(dot)

        title = QLabel("Nevada")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.config.INK}; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("автономный ассистент")
        subtitle.setStyleSheet(f"color: {self.config.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        layout.addWidget(subtitle)

        layout.addStretch()

        btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {self.config.TEXT_MUTED};
                border: none;
                border-radius: 6px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
            }}
        """
        for text, slot in (("─", self.showMinimized), ("▢", self._toggle_maximize)):
            btn = QPushButton(text)
            btn.setFixedSize(30, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 26)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.config.TEXT_MUTED};
                border: none;
                border-radius: 6px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {self.config.DANGER};
                color: #ffffff;
            }}
        """)
        close_btn.clicked.connect(self.hide)  # живём в трее
        layout.addWidget(close_btn)

        self._title_bar = bar
        return bar

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # --- Боковая навигация вместо вкладок ---

    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(198)
        side.setStyleSheet(f"background-color: {self.config.BG_ALT}; border-right: 1px solid {self.config.BORDER};")

        layout = QVBoxLayout(side)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(6)

        self.nav_buttons = []
        for index, (icon, name) in enumerate((("💬", "Чат"), ("📖", "Команды"), ("📅", "Календарь"), ("📜", "История"))):
            btn = QPushButton(f"  {icon}   {name}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.config.TEXT_MUTED};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    padding-left: 10px;
                    font-size: 10pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.config.BG_INPUT};
                    color: {self.config.TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background-color: {self.config.ACCENT};
                    color: #08211f;
                }}
            """)
            btn.clicked.connect(lambda _, i=index: self._select_page(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        self.status_pill = QLabel("● на связи")
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(124, 140, 248, 0.14);
                color: {self.config.ACCENT};
                border: 1px solid rgba(124, 140, 248, 0.32);
                border-radius: 13px;
                padding: 7px 12px;
                font-weight: bold;
                font-size: 9pt;
            }}
        """)
        layout.addWidget(self.status_pill)

        return side

    def _select_page(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        if index == 1:
            self.commands_page.refresh()
        elif index == 3:
            self.history_tab._refresh_history()

    def _use_example(self, text: str):
        """Пример со страницы «Команды» — подставляем в чат и переходим туда"""
        self._select_page(0)
        self.chat_tab.input_field.setText(text)
        self.chat_tab.input_field.setFocus()

    # --- Перетаскивание окна за шапку ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 46:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.position().y() <= 46:
            self._toggle_maximize()
