"""
Проверка на РЕАЛЬНОМ Qt (offscreen): пузыри сообщений не обрезаются,
лента скроллится, HUD выдерживает cooldown после ответа.
"""
import os
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=True)
import os
os.chdir(PROJECT_ROOT)


from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import QTimer

app = QApplication(sys.argv)

failures = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


from ui.widgets import MessageBubble
from ui.main_window import ChatTab

print("=== 1. MessageBubble: длинный текст не обрезается ===")
LONG = ("Это очень длинное сообщение, которое обязано переноситься по словам и "
        "увеличивать высоту пузыря, а не обрезаться в одну строку, как было раньше. " * 3)

bubble = MessageBubble(LONG, is_user=False)
bubble.resize(700, 10)
bubble.show()
app.processEvents()

label = bubble.label
check("wordWrap включён", label.wordWrap())
check("высота пузыря выросла под текст (>60px)", bubble.sizeHint().height() > 60,
      f"height={bubble.sizeHint().height()}")
check("ширина пузыря ограничена ~78% ленты", label.maximumWidth() <= int(700 * 0.78) + 1,
      f"maxW={label.maximumWidth()}")

short = MessageBubble("Привет", is_user=True)
short.resize(700, 10)
short.show()
app.processEvents()
check("короткий пузырь не растянут на всю ширину",
      short.label.sizeHint().width() < 400, f"w={short.label.sizeHint().width()}")

print("\n=== 2. ChatTab: реальная прокрутка ленты ===")
tab = ChatTab(agent_loop=None, voice_manager=None)
tab.resize(800, 500)
tab.show()
app.processEvents()

from PyQt6.QtWidgets import QScrollArea
check("используется настоящий QScrollArea", isinstance(tab.scroll_area, QScrollArea))
check("widgetResizable включён", tab.scroll_area.widgetResizable())

for i in range(30):
    tab._add_message(f"Сообщение номер {i}: " + "текст " * 12, is_user=(i % 2 == 0))

# даём Qt пересчитать геометрию (диапазон скролла обновляется отложенно)
for _ in range(5):
    app.processEvents()

bar = tab.scroll_area.verticalScrollBar()
check("после 30 сообщений появилась прокрутка", bar.maximum() > 0, f"max={bar.maximum()}")
check("лента сама прокрутилась вниз (rangeChanged)", bar.value() == bar.maximum(),
      f"value={bar.value()} max={bar.maximum()}")

# пользователь отлистал вверх — лента не должна дёргаться обратно
bar.setValue(0)
app.processEvents()
tab._add_message("Ещё одно сообщение", is_user=False)
for _ in range(5):
    app.processEvents()
check("после ручной прокрутки вверх новое сообщение всё же показывается",
      bar.value() == bar.maximum(), f"value={bar.value()} max={bar.maximum()}")

count_bubbles = sum(
    1 for i in range(tab.chat_layout.count())
    if isinstance(tab.chat_layout.itemAt(i).widget(), MessageBubble)
)
check("все 31 пузырь в ленте (30 + добавленный при проверке прокрутки)",
      count_bubbles == 31, f"got={count_bubbles}")

print("\n=== 3. Стриминг дописывает в один пузырь ===")
tab2 = ChatTab(agent_loop=None, voice_manager=None)
tab2.resize(800, 500)
before = sum(1 for i in range(tab2.chat_layout.count())
             if isinstance(tab2.chat_layout.itemAt(i).widget(), MessageBubble))
for tok in ["При", "вет", ", мир", "!"]:
    tab2._on_token(tok)
app.processEvents()
after = sum(1 for i in range(tab2.chat_layout.count())
            if isinstance(tab2.chat_layout.itemAt(i).widget(), MessageBubble))
check("создан ровно один пузырь на весь стрим", after - before == 1, f"delta={after-before}")
check("текст собран целиком", tab2._streaming_bubble.text() == "Привет, мир!",
      f"got={tab2._streaming_bubble.text()!r}")
tab2._on_response_ready("Привет, мир!")
check("после завершения стрим-пузырь сброшен", tab2._streaming_bubble is None)

print("\n=== 4. HUD: cooldown удерживает ответ на экране ===")
from ui.hud_widget import HudWidget, COOLDOWN_MS, IDLE_HINT


class FakeVM:
    from PyQt6.QtCore import pyqtSignal
    stt = None
    tts = None
    is_ready = False

    def __init__(self):
        from PyQt6.QtCore import QObject, pyqtSignal

    def ensure_loaded(self): pass


# Простейший QObject с нужными сигналами
from PyQt6.QtCore import QObject, pyqtSignal


class StubVoiceManager(QObject):
    ready = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.stt = None
        self.tts = None      # TTS недоступен -> ветка без озвучки
        self.is_ready = True

    def ensure_loaded(self):
        pass


hud = HudWidget(agent_loop=None, voice_manager=StubVoiceManager())
hud.show()
app.processEvents()

hud._on_response_ready("Вот ваш ответ от Nevada")
app.processEvents()

check("ответ показан в caption сразу после готовности",
      "Вот ваш ответ" in hud.caption_label.text(), f"got={hud.caption_label.text()!r}")
check("активен cooldown", hud._cooldown is True)

# Клик во время cooldown не должен запускать новое прослушивание
state_before = hud.canvas.state
hud._on_ring_clicked()
check("клик во время cooldown игнорируется", hud.canvas.state == state_before)
check("ответ всё ещё на экране во время cooldown",
      "Вот ваш ответ" in hud.caption_label.text(), f"got={hud.caption_label.text()!r}")

check(f"cooldown задан разумно ({COOLDOWN_MS}ms >= 3000)", COOLDOWN_MS >= 3000)

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
