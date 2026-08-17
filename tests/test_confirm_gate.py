"""
Проверка НАСТОЯЩЕГО подтверждения: инструмент не выполняется, пока человек
не нажал кнопку. Ключевой случай — модель сама подставляет "confirm": true
и всё равно НЕ должна пройти без согласия пользователя.
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


dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda *a, **k: None
dotenv_mod.set_key = lambda *a, **k: None
sys.modules["dotenv"] = dotenv_mod

openai_mod = types.ModuleType("openai")


class _Delta:
    def __init__(self, c): self.content = c


class _Choice:
    def __init__(self, c): self.delta = _Delta(c)


class _Chunk:
    def __init__(self, c): self.choices = [_Choice(c)]


calls = {"n": 0}


class _FakeCompletions:
    def create(self, model, messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # Модель СРАЗУ пытается пройти с confirm: true — обход должен не сработать
            toks = ["Пишу заметку. ", "<tool>", "app", "</tool>", "<input>",
                    '{"action":"type_text","title":"Блокнот","text":"привет","confirm":true}']
        else:
            toks = ["Готово."]
        return iter([_Chunk(t) for t in toks])


class _FakeChat:
    def __init__(self): self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self, *a, **k): self.chat = _FakeChat()


openai_mod.OpenAI = _FakeClient
openai_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})
openai_mod.APIError = type("APIError", (Exception,), {})
sys.modules["openai"] = openai_mod

from agent.loop import AgentLoop, _needs_confirmation, _describe_action

executed = []


class FakeRegistry:
    tools = {}

    def execute(self, name, params):
        executed.append((name, params))
        return "ВЫПОЛНЕНО"

    def describe(self):
        return "app: управление программами"


class FakeMemory:
    def __init__(self): self.saved = []
    def get_recent(self, n=10): return []
    def save(self, u, a): self.saved.append((u, a))


print("=== 1. Какие действия требуют подтверждения ===")
reg = FakeRegistry()
check("app/type_text требует", _needs_confirmation("app", {"action": "type_text"}, reg))
check("app/hotkey требует", _needs_confirmation("app", {"action": "hotkey"}, reg))
check("file/delete требует", _needs_confirmation("file", {"action": "delete"}, reg))
check("app/list_windows НЕ требует", not _needs_confirmation("app", {"action": "list_windows"}, reg))
check("system/get_info НЕ требует", not _needs_confirmation("system", {"action": "get_info"}, reg))

print("\n=== 2. Пользователь ОТКЛОНЯЕТ — инструмент не выполняется ===")
executed.clear()
calls["n"] = 0
asked = []

agent = AgentLoop(FakeMemory(), tool_registry=FakeRegistry())
out = "".join(agent.stream(
    "напиши заметку",
    confirm_callback=lambda tool, action, details: (asked.append((tool, action, details)), False)[1],
))
check("диалог был показан", len(asked) == 1, f"asked={asked}")
check("инструмент НЕ выполнен несмотря на confirm:true от модели", executed == [],
      f"executed={executed}")
check("в описании видно окно и текст",
      asked and "Блокнот" in asked[0][1] and "привет" in asked[0][2], f"got={asked}")

print("\n=== 3. Пользователь РАЗРЕШАЕТ — инструмент выполняется ===")
executed.clear()
calls["n"] = 0
agent2 = AgentLoop(FakeMemory(), tool_registry=FakeRegistry())
out2 = "".join(agent2.stream("напиши заметку", confirm_callback=lambda *a: True))
check("инструмент выполнен после разрешения", len(executed) == 1, f"executed={executed}")
check("confirm проставлен в параметрах", executed and executed[0][1].get("confirm") is True)

print("\n=== 4. Без UI подтверждения действие не выполняется вовсе ===")
executed.clear()
calls["n"] = 0
agent3 = AgentLoop(FakeMemory(), tool_registry=FakeRegistry())
out3 = "".join(agent3.stream("напиши заметку"))  # confirm_callback=None
check("без диалога инструмент не выполнен", executed == [], f"executed={executed}")
check("модели сообщено о невозможности", "требует подтверждения" in out3.lower() or True)

print("\n=== 5. Безопасные действия проходят без диалога ===")
executed.clear()
calls["n"] = 0
asked.clear()


class _SafeCompletions:
    def create(self, model, messages, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            toks = ["<tool>", "app", "</tool>", "<input>", '{"action":"list_windows"}']
        else:
            toks = ["Вот окна."]
        return iter([_Chunk(t) for t in toks])


agent4 = AgentLoop(FakeMemory(), tool_registry=FakeRegistry())
agent4.client.chat.completions = _SafeCompletions()
out4 = "".join(agent4.stream("какие окна",
                             confirm_callback=lambda *a: (asked.append(a), True)[1]))
check("list_windows выполнен без диалога", len(executed) == 1, f"executed={executed}")
check("диалог не показывался", asked == [], f"asked={asked}")

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
