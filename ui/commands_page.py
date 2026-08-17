"""
CommandsPage — страница «Команды»: что Nevada умеет и как её попросить.

Список строится из живого реестра инструментов и папки навыков, поэтому
не устаревает: добавили навык файлом — он появился здесь сам.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config import Config


# Примеры фраз для инструментов: что писать, чтобы это сработало
TOOL_EXAMPLES = {
    "system": [
        "какие у меня комплектующие?",
        "покажи загрузку процессора и памяти",
        "сколько места на дисках?",
        "какие процессы жрут память?",
    ],
    "app": [
        "какие программы открыты?",
        "открой блокнот",
        "найди в интернете рецепт борща",
        "открой калькулятор",
    ],
    "file": [
        "покажи файлы в папке Загрузки",
        "прочитай файл C:\\temp\\notes.txt",
    ],
    "shell": [
        "какая версия Windows?",
        "покажи сетевые настройки",
    ],
    "research": [
        "расскажи, что такое трансформеры в нейросетях",
        "что известно про язык Rust?",
        "прочитай страницу https://example.com",
    ],
    "skill": [
        "дай утренний дайджест",
        "какие у тебя есть навыки?",
    ],
}

TOOL_TITLES = {
    "system": ("🖥️", "Система и железо"),
    "app": ("🪟", "Программы и окна"),
    "file": ("📁", "Файлы"),
    "shell": ("⌨️", "Команды Windows"),
    "research": ("🔎", "Поиск и чтение в интернете"),
    "skill": ("✨", "Навыки"),
}


class CommandCard(QFrame):
    """Карточка группы команд с кликабельными примерами"""

    example_clicked = pyqtSignal(str)

    def __init__(self, icon: str, title: str, subtitle: str, examples: list):
        super().__init__()
        self.config = Config()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.config.CARD};
                border: 1px solid {self.config.BORDER};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)

        header = QLabel(f"{icon}  {title}")
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {self.config.INK}; background: transparent; border: none;")
        layout.addWidget(header)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setStyleSheet(
                f"color: {self.config.TEXT_MUTED}; background: transparent; "
                f"border: none; font-size: 9pt;"
            )
            layout.addWidget(sub)

        for example in examples:
            layout.addWidget(self._make_example_button(example))

    def _make_example_button(self, text: str) -> QPushButton:
        button = QPushButton(f"  «{text}»")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 10px;
                text-align: left;
                padding: 6px 10px;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                border-color: {self.config.ACCENT};
                color: {self.config.ACCENT};
            }}
        """)
        button.clicked.connect(lambda: self.example_clicked.emit(text))
        return button


class CommandsPage(QWidget):
    """Страница со списком возможностей и примерами запросов"""

    # Пользователь выбрал пример — вставить его в чат
    example_chosen = pyqtSignal(str)

    def __init__(self, tool_registry=None):
        super().__init__()
        self.config = Config()
        self.tool_registry = tool_registry

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        title = QLabel("Что умеет Nevada")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.config.INK}; background: transparent;")
        outer.addWidget(title)

        hint = QLabel("Нажмите на пример — он подставится в чат. Просто пишите своими словами.")
        hint.setStyleSheet(f"color: {self.config.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        outer.addWidget(hint)

        # Прокручиваемая область с карточками
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidget(self.container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
            QScrollBar::handle:vertical {{
                background: #39406a; border-radius: 5px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #4b5488; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        outer.addWidget(scroll, 1)

        self.refresh()

    def refresh(self):
        """Пересобирает список из живого реестра инструментов и навыков"""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        available = set(self.tool_registry.list()) if self.tool_registry else set(TOOL_EXAMPLES)

        # Навыки — отдельной карточкой с их собственными триггерами
        skill_examples = self._skill_examples()
        if skill_examples:
            self._add_card("✨", "Навыки — готовые сценарии",
                           "Добавляются файлами .md в папку skills/, код менять не нужно",
                           skill_examples)

        for name in ("research", "system", "app", "file", "shell"):
            if name not in available:
                continue
            icon, title = TOOL_TITLES.get(name, ("•", name))
            self._add_card(icon, title, "", TOOL_EXAMPLES.get(name, []))

        # Пояснение про подтверждения
        note = QLabel(
            "⚠️  Действия, которые меняют что-то на компьютере — ввод текста в окна, "
            "нажатие клавиш, удаление и запись файлов, опасные команды — выполняются "
            "только после вашего подтверждения в отдельном окне."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(196, 181, 253, 0.10);
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid rgba(196, 181, 253, 0.30);
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 9pt;
            }}
        """)
        self.cards_layout.addWidget(note)
        self.cards_layout.addStretch()

    def _skill_examples(self) -> list:
        """Берёт по одному примеру-триггеру на каждый навык"""
        if not self.tool_registry:
            return []
        skill_tool = getattr(self.tool_registry, "tools", {}).get("skill")
        manager = getattr(skill_tool, "manager", None)
        if manager is None:
            return []

        examples = []
        for skill in manager.skills.values():
            phrase = skill.triggers[0] if skill.triggers else skill.name
            examples.append(f"{phrase}")
        return examples

    def _add_card(self, icon: str, title: str, subtitle: str, examples: list):
        if not examples:
            return
        card = CommandCard(icon, title, subtitle, examples)
        card.example_clicked.connect(self.example_chosen.emit)
        self.cards_layout.addWidget(card)
