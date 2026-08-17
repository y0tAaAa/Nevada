"""
Настоящее подтверждение опасных действий: блокирующий диалог с кнопками.

Модель не может его обойти — гейт стоит в AgentLoop перед вызовом инструмента,
и выполнение реально ждёт клика пользователя, а не «обещания» модели.
"""

import threading

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QFont

from config import Config


class ConfirmRequest:
    """Запрос на подтверждение, передаваемый из рабочего потока в UI-поток"""

    def __init__(self, title: str, action: str, details: str):
        self.title = title
        self.action = action
        self.details = details
        self.approved = False
        self.event = threading.Event()

    def answer(self, approved: bool):
        self.approved = approved
        self.event.set()


class ConfirmationBroker(QObject):
    """
    Мост между потоком агента и UI. `ask()` вызывается из рабочего потока
    и блокируется до ответа пользователя.
    """

    requested = pyqtSignal(object)  # ConfirmRequest

    def __init__(self, parent=None):
        super().__init__(parent)

    def ask(self, title: str, action: str, details: str, timeout: float = 180.0) -> bool:
        """Блокирующий запрос подтверждения. False — отклонено или истекло время."""
        request = ConfirmRequest(title, action, details)
        self.requested.emit(request)  # уйдёт в UI-поток очередью
        if not request.event.wait(timeout):
            return False
        return request.approved


class ConfirmDialog(QDialog):
    """Модальное окно подтверждения в тёмной индиго-теме"""

    def __init__(self, request: ConfirmRequest, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.request = request

        self.setWindowTitle("Подтверждение действия")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.config.CARD};
            }}
            QLabel {{
                color: {self.config.TEXT_PRIMARY};
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QLabel("⚠️  Nevada просит разрешение")
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.config.ACCENT_2}; background: transparent;")
        layout.addWidget(header)

        action_label = QLabel(request.action)
        action_label.setWordWrap(True)
        action_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(action_label)

        if request.details:
            details_frame = QFrame()
            details_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.config.CODE_BG};
                    border: 1px solid {self.config.BORDER};
                    border-left: 3px solid {self.config.ACCENT};
                    border-radius: 10px;
                }}
            """)
            details_layout = QVBoxLayout(details_frame)
            details_layout.setContentsMargins(12, 10, 12, 10)

            details_label = QLabel(request.details)
            details_label.setWordWrap(True)
            details_label.setFont(QFont("Consolas", 9))
            details_label.setStyleSheet(
                f"color: {self.config.TEXT_PRIMARY}; background: transparent; border: none;"
            )
            details_layout.addWidget(details_label)
            layout.addWidget(details_frame)

        hint = QLabel("Действие выполнится только после вашего разрешения.")
        hint.setStyleSheet(f"color: {self.config.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch()

        deny_btn = QPushButton("Отклонить")
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.setMinimumHeight(38)
        deny_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 11px;
                padding: 9px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{ border-color: {self.config.DANGER}; color: {self.config.DANGER}; }}
        """)
        deny_btn.clicked.connect(self._deny)

        allow_btn = QPushButton("Разрешить")
        allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        allow_btn.setMinimumHeight(38)
        allow_btn.setDefault(True)
        allow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: #12152b;
                border: none;
                border-radius: 11px;
                padding: 9px 22px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.config.ACCENT_DARK}; }}
        """)
        allow_btn.clicked.connect(self._allow)

        buttons.addWidget(deny_btn)
        buttons.addWidget(allow_btn)
        layout.addLayout(buttons)

    def _allow(self):
        self.request.answer(True)
        self.accept()

    def _deny(self):
        self.request.answer(False)
        self.reject()

    def closeEvent(self, event):
        # Закрытие крестиком = отказ, поток агента не должен зависнуть
        if not self.request.event.is_set():
            self.request.answer(False)
        super().closeEvent(event)


def show_confirm_dialog(request: ConfirmRequest, parent=None):
    """Слот для ConfirmationBroker.requested — выполняется в UI-потоке"""
    dialog = ConfirmDialog(request, parent)
    dialog.exec()
    # Страховка: если диалог закрыли необычным способом
    if not request.event.is_set():
        request.answer(False)
