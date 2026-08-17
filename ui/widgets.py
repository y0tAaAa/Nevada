"""
Общие виджеты чата: строка сообщения с аватаром и временем,
карточка результата инструмента.
"""

from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from config import Config


class Avatar(QLabel):
    """Круглый аватар с буквой"""

    def __init__(self, letter: str, bg: str, fg: str = "#ffffff", size: int = 30):
        super().__init__(letter)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: {size // 2}px;
            }}
        """)


class MessageBubble(QWidget):
    """
    Строка сообщения: аватар + имя/время + пузырь с текстом.
    Пузырь обнимает текст, переносит его по словам и растёт в высоту.
    """

    MAX_WIDTH_RATIO = 0.72
    MIN_BUBBLE_WIDTH = 140

    def __init__(self, text: str, is_user: bool, timestamp: str = None):
        super().__init__()
        self.config = Config()
        self.is_user = is_user

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.setAlignment(Qt.AlignmentFlag.AlignTop)

        time_text = timestamp or datetime.now().strftime("%H:%M")

        # Колонка: заголовок (имя + время) и сам пузырь
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)

        meta = QLabel(f"{'Вы' if is_user else 'Nevada'} · {time_text}")
        meta.setFont(QFont("Segoe UI", 8))
        meta.setStyleSheet(f"color: {self.config.TEXT_MUTED}; background: transparent;")

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", 10))
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)

        if is_user:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.config.BG_MSG_USER};
                    color: #ffffff;
                    border: none;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                    padding: 11px 14px;
                }}
            """)
            meta.setAlignment(Qt.AlignmentFlag.AlignRight)
            column.addWidget(meta)
            bubble_row = QHBoxLayout()
            bubble_row.setContentsMargins(0, 0, 0, 0)
            bubble_row.addStretch()
            bubble_row.addWidget(self.label)
            column.addLayout(bubble_row)

            row.addStretch()
            row.addLayout(column)
            row.addWidget(Avatar("В", self.config.BG_MSG_USER))
        else:
            self.label.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.config.BG_MSG_NEV};
                    color: {self.config.TEXT_PRIMARY};
                    border: 1px solid {self.config.BORDER};
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                    padding: 11px 14px;
                }}
            """)
            column.addWidget(meta)
            bubble_row = QHBoxLayout()
            bubble_row.setContentsMargins(0, 0, 0, 0)
            bubble_row.addWidget(self.label)
            bubble_row.addStretch()
            column.addLayout(bubble_row)

            row.addWidget(Avatar("N", self.config.ACCENT, "#12152b"))
            row.addLayout(column)
            row.addStretch()

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        max_width = max(int(self.width() * self.MAX_WIDTH_RATIO), self.MIN_BUBBLE_WIDTH)
        self.label.setMaximumWidth(max_width)

    # --- API для стриминга ---

    def text(self) -> str:
        return self.label.text()

    def set_text(self, text: str):
        self.label.setText(text)

    def append_text(self, chunk: str):
        self.label.setText(self.label.text() + chunk)


class ToolResultCard(QFrame):
    """
    Карточка результата инструмента: заголовок с именем инструмента
    и моноширинный блок с фактическим выводом.
    """

    def __init__(self, tool_name: str, result: str):
        super().__init__()
        self.config = Config()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.config.CODE_BG};
                border: 1px solid {self.config.BORDER};
                border-left: 3px solid {self.config.ACCENT};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(6)

        header = QLabel(f"🔧  {tool_name}")
        header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header.setStyleSheet(
            f"color: {self.config.ACCENT}; background: transparent; border: none; letter-spacing: 1px;"
        )
        layout.addWidget(header)

        body = QLabel(result.strip())
        body.setWordWrap(True)
        body.setFont(QFont("Consolas", 9))
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet(
            f"color: {self.config.TEXT_PRIMARY}; background: transparent; border: none;"
        )
        layout.addWidget(body)


class TypingBubble(MessageBubble):
    """Пузырь-заглушка «Nevada печатает…»"""

    def __init__(self):
        super().__init__("Nevada печатает…", is_user=False)
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.config.BG_MSG_NEV};
                color: {self.config.TEXT_MUTED};
                border: 1px solid {self.config.BORDER};
                border-radius: 16px;
                border-bottom-left-radius: 4px;
                padding: 11px 14px;
                font-style: italic;
            }}
        """)
