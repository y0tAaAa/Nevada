"""
Сквозной тест голосового стека и HudWidget на РЕАЛЬНОМ коде проекта.
Заглушки только для PyQt6/openai/dotenv/sounddevice/faster_whisper/pyttsx3 —
т.е. для вещей, которых физически нет в этом sandbox (реальный микрофон,
реальная модель Whisper, реальный SAPI5). numpy — настоящий (доустановлен).
Вся бизнес-логика (VoiceEngine, TTSEngine, VoiceManager, HudWidget, AgentWorker)
выполняется как есть, без переписывания.
"""
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import types

import numpy as np

failures = []


def check(name, cond, detail=""):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# ============ Заглушка PyQt6 ============

class BoundSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, cb):
        self._callbacks.append(cb)

    def emit(self, *args):
        for cb in list(self._callbacks):
            cb(*args)


class FakeSignal:
    def __init__(self, *a, **k):
        pass

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        key = f"_bound_{self._name}"
        if not hasattr(obj, key):
            setattr(obj, key, BoundSignal())
        return getattr(obj, key)


class FakeQThread:
    def __init__(self, *a, **k):
        pass

    def start(self):
        self.run()


class FakeQObject:
    def __init__(self, *a, **k):
        pass


class _FlagNS:
    def __getattr__(self, name):
        return 0


class FakeQt:
    WindowType = _FlagNS()
    WidgetAttribute = _FlagNS()
    MouseButton = _FlagNS()
    Key = _FlagNS()
    AlignmentFlag = _FlagNS()
    PenStyle = _FlagNS()
    BrushStyle = _FlagNS()
    PenCapStyle = _FlagNS()
    KeyboardModifier = _FlagNS()
    ActivationReason = _FlagNS()


class FakeQTimer:
    def __init__(self, parent=None):
        self.timeout = BoundSignal()

    def start(self, ms):
        pass

    def stop(self):
        pass

    @staticmethod
    def singleShot(ms, callback):
        callback()  # выполняем сразу — детерминированность в тесте


class _NoOp:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        def _f(*a, **k):
            return _NoOp()
        return _f


class FakeQCursor:
    class _Pos:
        def x(self):
            return 500

        def y(self):
            return 500

    @staticmethod
    def pos():
        return FakeQCursor._Pos()


qtcore = types.ModuleType("PyQt6.QtCore")
qtcore.QThread = FakeQThread
qtcore.QObject = FakeQObject
qtcore.pyqtSignal = FakeSignal
qtcore.Qt = FakeQt
qtcore.QTimer = FakeQTimer
qtcore.QPointF = _NoOp
qtcore.QRectF = _NoOp
qtcore.QSize = _NoOp
qtcore.QRect = _NoOp
qtcore.QPoint = _NoOp
qtcore.QDateTime = _NoOp


class _WidgetBase:
    def __init__(self, *a, **k):
        self._visible = False
        self._text = ""

    def setStyleSheet(self, *a, **k): pass
    def setFixedSize(self, *a, **k): pass
    def setContentsMargins(self, *a, **k): pass
    def setSpacing(self, *a, **k): pass
    def setAttribute(self, *a, **k): pass
    def setWindowFlags(self, *a, **k): pass
    def setLayout(self, layout): self._layout = layout
    def layout(self): return getattr(self, "_layout", None)
    def show(self): self._visible = True
    def hide(self): self._visible = False
    def isVisible(self): return self._visible
    def move(self, *a, **k): pass
    def raise_(self): pass
    def activateWindow(self): pass
    def width(self): return 340
    def height(self): return 430
    def update(self): pass
    def setMinimumHeight(self, *a, **k): pass
    def setMinimumWidth(self, *a, **k): pass
    def setWordWrap(self, *a, **k): pass
    def setAlignment(self, *a, **k): pass
    def setFont(self, *a, **k): pass
    def setMaximumWidth(self, *a, **k): pass
    def setFixedWidth(self, *a, **k): pass
    def setPlaceholderText(self, *a, **k): pass
    def setText(self, t): self._text = t
    def text(self): return self._text
    def clear(self): self._text = ""
    def setFocus(self): pass

    def pos(self):
        class P:
            def x(self_): return 0
            def y(self_): return 0
        return P()


class FakeQWidget(_WidgetBase):
    pass


class FakeQLabel(_WidgetBase):
    def __init__(self, text="", *a, **k):
        super().__init__()
        self._text = text


class FakeQLineEdit(_WidgetBase):
    pass


class FakeQPushButton(_WidgetBase):
    def __init__(self, text="", *a, **k):
        super().__init__()
        self._text = text
        self.clicked = BoundSignal()


class _FakeLayout:
    def __init__(self, *a, **k):
        self.items = []

    def addWidget(self, w, *a, **k): self.items.append(w)
    def addLayout(self, l, *a, **k): self.items.append(l)
    def addStretch(self, *a, **k): pass
    def setContentsMargins(self, *a, **k): pass
    def setSpacing(self, *a, **k): pass


qtwidgets = types.ModuleType("PyQt6.QtWidgets")
qtwidgets.QWidget = FakeQWidget
qtwidgets.QLabel = FakeQLabel
qtwidgets.QLineEdit = FakeQLineEdit
qtwidgets.QPushButton = FakeQPushButton
qtwidgets.QVBoxLayout = _FakeLayout
qtwidgets.QHBoxLayout = _FakeLayout
qtwidgets.QScrollArea = FakeQWidget
qtwidgets.QTextEdit = FakeQWidget
qtwidgets.QFrame = FakeQWidget
qtwidgets.QMainWindow = FakeQWidget
qtwidgets.QApplication = _NoOp
qtwidgets.QTabWidget = FakeQWidget
qtwidgets.QCalendarWidget = FakeQWidget
qtwidgets.QListWidget = FakeQWidget
qtwidgets.QListWidgetItem = _NoOp
qtwidgets.QDialog = FakeQWidget
qtwidgets.QCheckBox = FakeQWidget

qtgui = types.ModuleType("PyQt6.QtGui")
qtgui.QPainter = _NoOp
qtgui.QColor = _NoOp
qtgui.QPen = _NoOp
qtgui.QCursor = FakeQCursor
qtgui.QFont = _NoOp
qtgui.QPalette = _NoOp
qtgui.QIcon = _NoOp
qtgui.QScreen = _NoOp

pyqt6 = types.ModuleType("PyQt6")
pyqt6.QtCore = qtcore
pyqt6.QtWidgets = qtwidgets
pyqt6.QtGui = qtgui
sys.modules["PyQt6"] = pyqt6
sys.modules["PyQt6.QtCore"] = qtcore
sys.modules["PyQt6.QtWidgets"] = qtwidgets
sys.modules["PyQt6.QtGui"] = qtgui

# ============ Заглушка dotenv / openai ============

dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda *a, **k: None
dotenv_mod.set_key = lambda *a, **k: None
sys.modules["dotenv"] = dotenv_mod

openai_mod = types.ModuleType("openai")
class _FakeOpenAIClient:
    def __init__(self, *a, **k): pass
class AuthenticationError(Exception): pass
class APIError(Exception): pass
openai_mod.OpenAI = _FakeOpenAIClient
openai_mod.AuthenticationError = AuthenticationError
openai_mod.APIError = APIError
sys.modules["openai"] = openai_mod

# ============ Заглушка sounddevice ============

class _FakeInputStream:
    def __init__(self, channels, samplerate, callback, blocksize):
        self.callback = callback
        self.blocksize = blocksize

    def __enter__(self):
        for _ in range(5):
            block = np.ones((self.blocksize, 1), dtype=np.float32) * 0.5
            self.callback(block, self.blocksize, None, None)
        for _ in range(10):
            block = np.zeros((self.blocksize, 1), dtype=np.float32)
            self.callback(block, self.blocksize, None, None)
        return self

    def __exit__(self, *a):
        return False


sd_mod = types.ModuleType("sounddevice")
sd_mod.InputStream = _FakeInputStream
sd_mod.sleep = lambda ms: None
sd_mod.query_devices = lambda: [{"name": "Fake Mic"}]
sd_mod.rec = lambda frames, **k: np.zeros((frames, 1), dtype=np.float32)
sd_mod.wait = lambda: None
sys.modules["sounddevice"] = sd_mod

# ============ Заглушка faster_whisper ============

class _FakeSegment:
    def __init__(self, text):
        self.text = text


class _FakeWhisperModel:
    def __init__(self, *a, **k):
        pass

    def transcribe(self, audio, language=None, beam_size=5):
        return ([_FakeSegment("привет ассистент")], None)


fw_mod = types.ModuleType("faster_whisper")
fw_mod.WhisperModel = _FakeWhisperModel
sys.modules["faster_whisper"] = fw_mod

# ============ Заглушка pyttsx3 ============

_tts_instances = []


class _FakeVoice:
    def __init__(self, id_, name, languages):
        self.id = id_
        self.name = name
        self.languages = languages


class _FakeTTSEngineImpl:
    def __init__(self):
        self._props = {}
        self.said = []
        _tts_instances.append(self)

    def getProperty(self, name):
        if name == "voices":
            return [
                _FakeVoice("com.fake.ru", "Russian Fake Voice", ["ru-RU"]),
                _FakeVoice("com.fake.en", "English Fake Voice", ["en-US"]),
            ]
        return self._props.get(name)

    def setProperty(self, name, value):
        self._props[name] = value

    def say(self, text):
        self.said.append(text)

    def runAndWait(self):
        pass

    def stop(self):
        pass


pyttsx3_mod = types.ModuleType("pyttsx3")
pyttsx3_mod.init = lambda: _FakeTTSEngineImpl()
sys.modules["pyttsx3"] = pyttsx3_mod

# ============ Теперь импортируем настоящий код проекта ============

from voice.engine import VoiceEngine
from voice.tts_engine import TTSEngine, prepare_response_for_speech
from voice.manager import VoiceManager
from agent.worker import AgentWorker
from ui.hud_widget import HudWidget

print("=== 1. VoiceEngine.listen_until_silence ===")
levels_seen = []
ve = VoiceEngine(language="ru")
text = ve.listen_until_silence(max_duration=5, on_level=lambda lvl: levels_seen.append(lvl))
check("VoiceEngine распознал текст из заглушки Whisper", text == "привет ассистент", f"got={text!r}")
check("on_level вызывался на каждый аудио-блок", len(levels_seen) == 15, f"got {len(levels_seen)} вызовов")
check("on_level видел и громкие, и тихие блоки", max(levels_seen) > 0.1 and min(levels_seen) < 0.01)

print("\n=== 2. TTSEngine.speak + очистка markdown ===")
tts = TTSEngine(language="ru")
tts.speak("**Привет** мир `код` #заголовок")
last_said = _tts_instances[-1].said
check("TTS реально вызвал say() с очищенным текстом", last_said == ["Привет мир код заголовок"], f"got={last_said!r}")

print("\n=== 3. prepare_response_for_speech ===")
raw = 'Хорошо, выполняю.\n<tool>shell</tool><input>{"command": "dir"}</input>\n\nРезультат: файлы показаны\n'
cleaned = prepare_response_for_speech(raw)
check("tool-call теги убраны из текста для озвучки", "<tool>" not in cleaned and "<input>" not in cleaned, f"got={cleaned!r}")
check("текст до и после тега сохранён", "Хорошо, выполняю." in cleaned and "Результат: файлы показаны" in cleaned)

print("\n=== 4. VoiceManager (ленивая загрузка) ===")
vm_ready_fired = {"n": 0}
vm = VoiceManager(language="ru")
vm.ready.connect(lambda: vm_ready_fired.__setitem__("n", vm_ready_fired["n"] + 1))
check("VoiceManager изначально не готов", not vm.is_ready)
vm.ensure_loaded()
check("после ensure_loaded() VoiceManager готов (STT+TTS загружены)", vm.is_ready)
check("signal ready выстрелил ровно один раз", vm_ready_fired["n"] == 1)
check("stt — реальный VoiceEngine", isinstance(vm.stt, VoiceEngine))
check("tts — реальный TTSEngine", isinstance(vm.tts, TTSEngine))

print("\n=== 5. HudWidget — полный голосовой цикл (клик -> слушаю -> думаю -> говорю -> idle) ===")


class FakeToolRegistry:
    def execute(self, name, params):
        return "OK"


class FakeAgentLoop:
    tool_registry = FakeToolRegistry()

    def stream(self, user_input):
        for tok in ["Здравствуйте! ", "Чем ", "могу ", "помочь?"]:
            yield tok


state_log = []
_orig_set_state = HudWidget._set_state


def _traced_set_state(self, state, caption=None):
    state_log.append((state, caption))
    _orig_set_state(self, state, caption)


HudWidget._set_state = _traced_set_state

voice_manager2 = VoiceManager(language="ru")  # свежий, ещё не загружен — проверяем "холодный старт"
hud = HudWidget(agent_loop=FakeAgentLoop(), voice_manager=voice_manager2)

check("HUD стартует в состоянии idle", hud.canvas.state == "idle")

hud._on_ring_clicked()  # единственный клик должен прогнать весь пайплайн благодаря синхронным FakeQThread

states_only = [s for s, _ in state_log]
check(
    "Последовательность состояний верна: idle(loading)->listening->thinking->speaking->idle",
    states_only == ["idle", "listening", "thinking", "speaking", "idle"],
    f"got={states_only!r}",
)
check("HUD вернулся в idle после озвучки ответа", hud.canvas.state == "idle")
check(
    "Распознанный текст показан пользователю в caption на шаге thinking",
    any(c and "привет ассистент" in c for s, c in state_log if s == "thinking"),
)
check(
    "TTS реально озвучил ответ агента",
    any("Здравствуйте" in s for s in _tts_instances[-1].said),
    f"last said={_tts_instances[-1].said!r}",
)

print()
if failures:
    print(f"ИТОГ: {len(failures)} провалено из {len(failures) + (0)}: {failures}")
    sys.exit(1)
else:
    print("ИТОГ: все проверки пройдены")
