"""
Смоук-тест сборки UI: создаём все окна с брокером подтверждения.
Ловит ошибки проводки вроде «object has no attribute confirm_broker»
до запуска приложения на экране.
"""
import os
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=True)
import os
os.chdir(PROJECT_ROOT)


from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

app = QApplication(sys.argv)

failures = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


from ui.main_window import MainWindow, ChatTab
from ui.floating import FloatingWidget
from ui.hud_widget import HudWidget
from ui.confirm_dialog import ConfirmationBroker


class StubVoiceManager(QObject):
    ready = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.stt = None
        self.tts = None
        self.is_ready = False

    def ensure_loaded(self):
        pass


broker = ConfirmationBroker()
vm = StubVoiceManager()

win = MainWindow(agent_loop=None, memory=None, planner=None, tool_registry=None,
                 voice_manager=vm, confirm_broker=broker)
check("MainWindow создан", win is not None)
check("MainWindow хранит брокер", win.confirm_broker is broker)
check("ChatTab получил брокер", win.chat_tab.confirm_broker is broker)

floating = FloatingWidget(agent_loop=None, voice_manager=StubVoiceManager(), confirm_broker=broker)
check("FloatingWidget получил брокер", floating.confirm_broker is broker)

hud = HudWidget(agent_loop=None, voice_manager=StubVoiceManager(), confirm_broker=broker)
check("HudWidget получил брокер", hud.confirm_broker is broker)

# Проверяем, что окна реально отрисовываются
win.resize(1000, 700)
win.show()
for _ in range(4):
    app.processEvents()
check("MainWindow отрисовался", win.isVisible())
check("боковая навигация построена (4 пункта)", len(win.nav_buttons) == 4, f"got={len(win.nav_buttons)}")
check("страниц четыре", win.pages.count() == 4, f"got={win.pages.count()}")
check("страница команд создана", win.commands_page is not None)

# Пример со страницы «Команды» должен подставляться в чат
win._use_example("какие у меня комплектующие?")
check("пример подставился в поле ввода чата",
      win.chat_tab.input_field.text() == "какие у меня комплектующие?",
      f"got={win.chat_tab.input_field.text()!r}")
check("после выбора примера открыт чат", win.pages.currentIndex() == 0)

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
