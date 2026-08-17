"""
HudWidget — голосовой HUD в стиле Jarvis: круговой анимированный индикатор
("arc reactor") вместо текстового чата. Клик по кругу = говорите, Nevada
слушает, думает и отвечает голосом.
"""

import math

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor

from config import Config
from agent.worker import AgentWorker
from voice.voice_worker import ListenWorker, SpeakWorker
from voice.tts_engine import prepare_response_for_speech

IDLE_HINT = "Нажмите на круг и говорите"

# Пауза после ответа: ответ остаётся на экране и новый цикл не стартует сразу
COOLDOWN_MS = 6000

STATE_LABELS = {
    "idle": "НАЖМИТЕ, ЧТОБЫ ГОВОРИТЬ",
    "listening": "СЛУШАЮ...",
    "thinking": "ДУМАЮ...",
    "speaking": "ГОВОРЮ...",
    "error": "ОШИБКА",
}


class _RingCanvas(QWidget):
    """Анимированное кольцо в духе arc reactor / Jarvis HUD"""

    clicked = pyqtSignal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setFixedSize(260, 260)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.state = "idle"
        self._tick = 0
        self._level = 0.0

    def set_state(self, state: str):
        self.state = state
        self.update()

    def set_level(self, level: float):
        target = min(level * 12.0, 1.0)
        self._level = self._level * 0.6 + target * 0.4
        self.update()

    def advance(self):
        self._tick += 1
        if self.state != "listening":
            self._level *= 0.9
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        base_radius = min(self.width(), self.height()) / 2 - 10
        t = self._tick

        palette = {
            "idle": QColor(self.config.ACCENT),
            "listening": QColor("#a78bfa"),
            "thinking": QColor(self.config.ACCENT),
            "speaking": QColor("#6ee7b7"),
            "error": QColor(self.config.DANGER),
        }
        color = palette.get(self.state, QColor(self.config.ACCENT))

        if self.state == "listening":
            level_boost = self._level * 0.28
            radius = base_radius * (0.82 + level_boost)
            self._draw_glow(painter, cx, cy, radius * 1.1, color, int(60 + 120 * self._level))
            self._draw_level_ticks(painter, cx, cy, base_radius, color)
            self._draw_ring(painter, cx, cy, radius, color, 3, 220)
            self._draw_core(painter, cx, cy, base_radius * (0.32 + level_boost * 0.5), color, 220)

        elif self.state == "thinking":
            for speed, span, radius_mult, alpha in (
                (6, 70, 0.95, 200), (-4, 50, 0.75, 140), (3, 40, 0.55, 100)
            ):
                angle = (t * speed) % 360
                self._draw_arc(painter, cx, cy, base_radius * radius_mult, color, angle, span, 4, alpha)
            self._draw_core(painter, cx, cy, base_radius * 0.3, color, 160)

        elif self.state == "speaking":
            cycle = 60
            phase = (t % cycle) / cycle
            for offset in (0.0, 0.33, 0.66):
                p = (phase + offset) % 1.0
                radius = base_radius * (0.5 + 0.5 * p)
                alpha = int(200 * (1 - p))
                self._draw_ring(painter, cx, cy, radius, color, 2, alpha)
            pulse = 1.0 + 0.06 * math.sin(t * 0.4)
            self._draw_core(painter, cx, cy, base_radius * 0.4 * pulse, color, 220)

        elif self.state == "error":
            self._draw_glow(painter, cx, cy, base_radius * 0.9, color, 90)
            self._draw_ring(painter, cx, cy, base_radius * 0.82, color, 2, 180)
            self._draw_core(painter, cx, cy, base_radius * 0.32, color, 200)

        else:  # idle
            pulse = 1.0 + 0.03 * math.sin(t * 0.05)
            self._draw_glow(painter, cx, cy, base_radius * pulse, color, 70)
            self._draw_ring(painter, cx, cy, base_radius * 0.82, color, 2, 140)
            self._draw_core(painter, cx, cy, base_radius * 0.35, color, 180)

        painter.end()

    def _draw_glow(self, painter, cx, cy, radius, color, alpha):
        steps = 6
        for i in range(steps, 0, -1):
            c = QColor(color)
            c.setAlpha(max(int(alpha * (i / steps) * 0.18), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c)
            r = radius * (0.7 + 0.3 * i / steps)
            painter.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_ring(self, painter, cx, cy, radius, color, width, alpha):
        c = QColor(color)
        c.setAlpha(alpha)
        painter.setPen(QPen(c, width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

    def _draw_arc(self, painter, cx, cy, radius, color, start_angle, span, width, alpha):
        c = QColor(color)
        c.setAlpha(alpha)
        pen = QPen(c, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(rect, int(start_angle * 16), int(span * 16))

    def _draw_core(self, painter, cx, cy, radius, color, alpha):
        c = QColor(color)
        c.setAlpha(alpha)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

    def _draw_level_ticks(self, painter, cx, cy, radius, color):
        tick_count = 24
        for i in range(tick_count):
            angle = (2 * math.pi * i / tick_count) + self._tick * 0.01
            active = (i / tick_count) < min(self._level, 1.0)
            length = 6 + (10 if active else 0)
            inner, outer = radius * 0.92, radius * 0.92 + length
            x1, y1 = cx + inner * math.cos(angle), cy + inner * math.sin(angle)
            x2, y2 = cx + outer * math.cos(angle), cy + outer * math.sin(angle)
            c = QColor(color)
            c.setAlpha(220 if active else 60)
            painter.setPen(QPen(c, 2))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))


class HudWidget(QWidget):
    """Голосовой HUD-режим Nevada"""

    def __init__(self, agent_loop, voice_manager, confirm_broker=None):
        super().__init__()
        self.config = Config()
        self.agent_loop = agent_loop
        self.voice_manager = voice_manager
        self.confirm_broker = confirm_broker

        self.listen_worker = None
        self.agent_worker = None
        self.speak_worker = None
        self._pending_listen = False
        self._speak_failed = False
        self._cooldown = False  # пауза после ответа, чтобы он не слетал мгновенно
        self.drag_pos = None

        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(340, 440)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Карточка в стиле TeacherSupport: светлая поверхность со скруглением
        card = QWidget()
        card.setObjectName("hudCard")
        card.setStyleSheet(f"""
            QWidget#hudCard {{
                background-color: {self.config.CARD};
                border: 1px solid {self.config.BORDER};
                border-radius: 24px;
            }}
        """)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 18)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        eyebrow = QLabel("ГОЛОСОВОЙ РЕЖИМ")
        eyebrow.setStyleSheet(
            f"color: {self.config.ACCENT}; font-weight: bold; font-size: 8pt; "
            f"letter-spacing: 2px; background: transparent;"
        )
        top_row.addWidget(eyebrow)
        top_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {self.config.TEXT_MUTED}; "
            f"border: none; font-size: 12pt; }} QPushButton:hover {{ color: {self.config.DANGER}; }}"
        )
        close_btn.clicked.connect(self.hide)
        top_row.addWidget(close_btn)
        layout.addLayout(top_row)

        self.canvas = _RingCanvas(self.config)
        self.canvas.clicked.connect(self._on_ring_clicked)
        self.canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        canvas_row = QHBoxLayout()
        canvas_row.addStretch()
        canvas_row.addWidget(self.canvas)
        canvas_row.addStretch()
        layout.addLayout(canvas_row)

        self.state_label = QLabel(STATE_LABELS["idle"])
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet(
            f"color: {self.config.ACCENT}; font-weight: bold; font-size: 9pt; "
            f"letter-spacing: 1px; background: transparent;"
        )
        layout.addWidget(self.state_label)

        self.caption_label = QLabel(IDLE_HINT)
        self.caption_label.setWordWrap(True)
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setStyleSheet(
            f"color: {self.config.TEXT_PRIMARY}; font-size: 10pt; background: transparent;"
        )
        self.caption_label.setMinimumHeight(70)
        layout.addWidget(self.caption_label)

        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.canvas.advance)
        self.timer.start(33)

        self.voice_manager.ready.connect(self._on_voice_ready)
        self.voice_manager.error.connect(self._on_voice_error)

    # --- окно ---

    def show_at_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_at_cursor()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    # --- состояние ---

    def _set_state(self, state: str, caption: str = None):
        self.canvas.set_state(state)
        self.state_label.setText(STATE_LABELS.get(state, ""))
        if caption is not None:
            self.caption_label.setText(caption)

    def _back_to_idle_later(self, delay_ms: int = 2500):
        QTimer.singleShot(delay_ms, lambda: self._set_state("idle", IDLE_HINT))

    # --- голосовой цикл ---

    def _on_ring_clicked(self):
        if self.canvas.state in ("listening", "thinking", "speaking"):
            return

        if self._cooldown:
            # Даём дочитать ответ; повторный клик до конца паузы игнорируем
            return

        if not self.voice_manager.is_ready:
            self._pending_listen = True
            self._set_state("idle", "Загружаю голосовой движок...")
            self.voice_manager.ensure_loaded()
            return

        self._start_listening()

    def _on_voice_ready(self):
        if self._pending_listen:
            self._pending_listen = False
            self._start_listening()

    def _on_voice_error(self, message: str):
        self._pending_listen = False
        self._set_state("error", message)
        self._back_to_idle_later()

    def _start_listening(self):
        stt = self.voice_manager.stt
        if not stt or not stt.is_available():
            self._set_state("error", "Микрофон недоступен")
            self._back_to_idle_later()
            return

        self._set_state("listening", "Говорите...")
        self.listen_worker = ListenWorker(stt, max_duration=12)
        self.listen_worker.level_changed.connect(self.canvas.set_level)
        self.listen_worker.text_ready.connect(self._on_text_recognized)
        self.listen_worker.no_speech.connect(self._on_no_speech)
        self.listen_worker.error.connect(self._on_listen_error)
        self.listen_worker.start()

    def _on_no_speech(self):
        self._set_state("idle", "Не расслышала, попробуйте ещё раз")

    def _on_listen_error(self, message: str):
        self._set_state("error", message)
        self._back_to_idle_later()

    def _on_text_recognized(self, text: str):
        self._set_state("thinking", f"Вы: {text}")
        self.agent_worker = AgentWorker(self.agent_loop, text, confirm_broker=self.confirm_broker)
        self.agent_worker.response_ready.connect(self._on_response_ready)
        self.agent_worker.error_occurred.connect(self._on_agent_error)
        self.agent_worker.start()

    def _on_agent_error(self, message: str):
        self._set_state("error", message)
        self._back_to_idle_later()

    def _on_response_ready(self, full_response: str):
        speech_text = prepare_response_for_speech(full_response)
        display_text = (speech_text if speech_text else full_response.strip())[:400]

        if self.voice_manager.tts and speech_text:
            self._set_state("speaking", display_text)
            self._speak_failed = False
            self.speak_worker = SpeakWorker(self.voice_manager.tts, speech_text)
            self.speak_worker.finished_speaking.connect(lambda: self._on_speaking_finished(display_text))
            self.speak_worker.error.connect(self._on_speak_error)
            self.speak_worker.start()
        else:
            # Озвучка недоступна — оставляем ответ на экране, не сбрасывая его
            self._enter_cooldown(display_text or IDLE_HINT)

    def _on_speak_error(self, message: str):
        # TTS не смог озвучить ответ (например, недоступен системный голос) —
        # хотя бы не терять текст ответа молча
        print(f"⚠️  Не удалось озвучить ответ: {message}")
        self._speak_failed = True

    def _on_speaking_finished(self, display_text: str = ""):
        # Ответ остаётся на экране — раньше он мгновенно затирался подсказкой
        self._enter_cooldown(display_text or IDLE_HINT)

    def _enter_cooldown(self, text_to_keep: str):
        """
        Пауза после ответа: текст ответа остаётся видимым, а новый цикл
        прослушивания не стартует, пока не пройдёт COOLDOWN_MS — иначе HUD
        сразу же начинал слушать снова и ответ «слетал».
        """
        self._set_state("idle", text_to_keep)
        self._cooldown = True
        QTimer.singleShot(COOLDOWN_MS, self._end_cooldown)

    def _end_cooldown(self):
        self._cooldown = False
        # Подсказку возвращаем только если пользователь ничего не начал заново
        if self.canvas.state == "idle":
            self.state_label.setText(STATE_LABELS["idle"])
