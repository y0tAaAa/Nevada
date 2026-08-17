"""
Контракт AgentWorker после переноса выполнения инструментов в AgentLoop:
воркер САМ инструменты не выполняет (иначе они отработали бы дважды),
а результаты пробрасывает наружу сигналом tool_result.
"""
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import types

failures = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# --- Заглушки PyQt6 / openai / dotenv ---
class BoundSignal:
    def __init__(self):
        self._cbs = []

    def connect(self, cb):
        self._cbs.append(cb)

    def emit(self, *a):
        for cb in list(self._cbs):
            cb(*a)


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


qtcore = types.ModuleType("PyQt6.QtCore")
qtcore.QThread = FakeQThread
qtcore.pyqtSignal = FakeSignal
pyqt6 = types.ModuleType("PyQt6")
pyqt6.QtCore = qtcore
sys.modules["PyQt6"] = pyqt6
sys.modules["PyQt6.QtCore"] = qtcore

dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda *a, **k: None
dotenv_mod.set_key = lambda *a, **k: None
sys.modules["dotenv"] = dotenv_mod

openai_mod = types.ModuleType("openai")
openai_mod.OpenAI = lambda *a, **k: None
openai_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})
openai_mod.APIError = type("APIError", (Exception,), {})
sys.modules["openai"] = openai_mod

from agent.worker import AgentWorker

registry_calls = []


class FakeToolRegistry:
    def execute(self, name, params):
        registry_calls.append((name, params))
        return "результат"


received = {}


class FakeAgentLoop:
    """Имитирует новый AgentLoop: сам выполняет инструмент и зовёт коллбек"""
    tool_registry = FakeToolRegistry()

    def stream(self, user_input, on_tool_result=None, confirm_callback=None):
        # Фиксируем, что воркер прокинул коллбек подтверждения
        received["confirm_callback"] = confirm_callback
        yield "Сейчас проверю. "
        # AgentLoop выполняет инструмент сам
        result = self.tool_registry.execute("system", {"action": "get_info"})
        if on_tool_result:
            on_tool_result("system", result)
        for tok in ["Готово", ": ", "12 ядер."]:
            yield tok


worker = AgentWorker(FakeAgentLoop(), "покажи систему")

tokens = []
tool_events = []
final = {}
worker.token_received.connect(tokens.append)
worker.tool_result.connect(lambda n, r: tool_events.append((n, r)))
worker.response_ready.connect(lambda r: final.setdefault("v", r))

worker.start()

check("инструмент выполнен ровно один раз", len(registry_calls) == 1, f"calls={registry_calls}")
check("воркер пробросил результат сигналом tool_result", tool_events == [("system", "результат")],
      f"got={tool_events}")
check("токены модели дошли до UI", "".join(tokens) == "Сейчас проверю. Готово: 12 ядер.",
      f"got={''.join(tokens)!r}")
check("сырой вывод инструмента НЕ попал в поток токенов", "результат" not in "".join(tokens))
check("финальный ответ собран", final.get("v") == "Сейчас проверю. Готово: 12 ядер.",
      f"got={final.get('v')!r}")


# Воркер без брокера не должен передавать коллбек
check("без брокера confirm_callback = None", received.get("confirm_callback") is None,
      f"got={received.get('confirm_callback')}")

# А с брокером — должен
class FakeBroker:
    def ask(self, tool, action, details):
        return True


worker2 = AgentWorker(FakeAgentLoop(), "ещё раз", confirm_broker=FakeBroker())
worker2.token_received.connect(lambda t: None)
worker2.response_ready.connect(lambda r: None)
worker2.start()
check("с брокером confirm_callback проброшен", callable(received.get("confirm_callback")),
      f"got={received.get('confirm_callback')}")

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
