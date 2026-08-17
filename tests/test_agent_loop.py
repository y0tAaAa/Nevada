"""
Проверка нового агентного цикла: инструмент реально выполняется, его РЕАЛЬНЫЙ
вывод возвращается в модель, XML вызова скрыт от пользователя.
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

from agent.parser import ToolTagFilter, parse_tool_call

print("=== 1. ToolTagFilter скрывает XML из видимого потока ===")

def run_filter(tokens):
    f = ToolTagFilter()
    out = "".join(f.feed(t) for t in tokens)
    return out + f.flush()

vis = run_filter(["Сейчас ", "посмотрю.", "<tool>", "system", "</tool>",
                  "<input>", '{"action": "get_info"}', "</input>"])
check("текст до вызова сохранён", "Сейчас посмотрю." in vis, f"got={vis!r}")
check("тег <tool> скрыт", "<tool>" not in vis, f"got={vis!r}")
check("тег </input> скрыт", "input" not in vis.lower(), f"got={vis!r}")

# теги разорваны между токенами
vis2 = run_filter(["Ок", "<to", "ol>", "shell", "</to", "ol>", "<inp", "ut>",
                   '{"command":"dir"}', "</inp", "ut>", " готово"])
check("разорванные теги тоже скрыты", "<" not in vis2 and "ut>" not in vis2, f"got={vis2!r}")
check("текст вокруг разорванных тегов уцелел", "Ок" in vis2 and "готово" in vis2, f"got={vis2!r}")

# обычный '<' не должен съедаться
vis3 = run_filter(["5 ", "< ", "10 и a<b"])
check("обычный символ '<' не теряется", "<" in vis3 and "a<b" in vis3, f"got={vis3!r}")

print("\n=== 2. Агентный цикл: инструмент выполняется и его вывод уходит в модель ===")

openai_mod = types.ModuleType("openai")
class AuthenticationError(Exception): pass
class APIError(Exception): pass


class _Delta:
    def __init__(self, c): self.content = c
class _Choice:
    def __init__(self, c): self.delta = _Delta(c)
class _Chunk:
    def __init__(self, c): self.choices = [_Choice(c)]


sent_conversations = []


last_kwargs = {}


class _FakeCompletions:
    def create(self, model, messages, **kwargs):
        sent_conversations.append(messages)
        last_kwargs.update(kwargs)
        # Первый вызов — модель просит инструмент. Второй — отвечает по данным.
        # ВАЖНО: имитируем реальное поведение stop=["</input>"] — закрывающий
        # тег НЕ приходит в потоке, обрыв происходит прямо на нём.
        if len(sent_conversations) == 1:
            toks = ["Сейчас проверю. ", "<tool>", "system", "</tool>",
                    "<input>", '{"action": "get_info"}']
        else:
            toks = ["По данным системы: ", "CPU 12 ядер, ", "RAM 15.7 GB."]
        return iter([_Chunk(t) for t in toks])


class _FakeChat:
    def __init__(self): self.completions = _FakeCompletions()
class _FakeClient:
    def __init__(self, *a, **k): self.chat = _FakeChat()


openai_mod.OpenAI = _FakeClient
openai_mod.AuthenticationError = AuthenticationError
openai_mod.APIError = APIError
sys.modules["openai"] = openai_mod

from agent.loop import AgentLoop

tool_calls = []


class FakeRegistry:
    def execute(self, name, params):
        tool_calls.append((name, params))
        return "CPU: 12 ядер (23%)\nRAM: 11.8 GB / 15.7 GB"

    def describe(self):
        return "system: инфо о системе"


class FakeMemory:
    def __init__(self): self.saved = []
    def get_recent(self, n=10): return []
    def save(self, u, a): self.saved.append((u, a))


mem = FakeMemory()
agent = AgentLoop(mem, tool_registry=FakeRegistry())
output = "".join(agent.stream("какая загрузка процессора"))

check("инструмент вызван ровно один раз", len(tool_calls) == 1, f"calls={tool_calls}")
check("вызван с верными параметрами", tool_calls and tool_calls[0] == ("system", {"action": "get_info"}),
      f"got={tool_calls}")
check("модель получила ВТОРОЙ запрос с результатом", len(sent_conversations) == 2,
      f"got={len(sent_conversations)}")

second = sent_conversations[1]
joined = "\n".join(m["content"] for m in second)
check("реальный вывод инструмента отправлен модели", "11.8 GB / 15.7 GB" in joined)
check("модели запрещено выдумывать (есть инструкция)", "Не придумывай" in joined)

check("XML вызова скрыт от пользователя", "<tool>" not in output and "<input>" not in output,
      f"got={output!r}")
check("виден маркер выполнения инструмента", "🔧 system" in output, f"got={output!r}")
check("виден реальный результат", "11.8 GB / 15.7 GB" in output)
check("виден финальный ответ модели по данным", "По данным системы" in output)
check("обмен сохранён в память", len(mem.saved) == 1)

print("\n=== 2b. Стоп-последовательность и чистота памяти ===")
check("stop=['</input>'] передан в API", last_kwargs.get("stop") == ["</input>"],
      f"got={last_kwargs.get('stop')!r}")
check("tool call распознан, хотя закрывающий тег обрезан stop-ом", len(tool_calls) == 1)

saved_user, saved_assistant = mem.saved[0]
check("в память НЕ попал маркер инструмента", "🔧" not in saved_assistant,
      f"saved={saved_assistant!r}")
check("в память НЕ попал сырой вывод инструмента", "11.8 GB / 15.7 GB" not in saved_assistant,
      f"saved={saved_assistant!r}")
check("в памяти осталась проза модели", "По данным системы" in saved_assistant,
      f"saved={saved_assistant!r}")
check("XML вызова не попал в память", "<tool>" not in saved_assistant and "<input>" not in saved_assistant,
      f"saved={saved_assistant!r}")

print("\n=== 2c. Отравленная история отбрасывается при загрузке ===")
from agent.loop import _sanitize_history

dirty = [
    {"role": "user", "content": "какие комплектующие"},
    {"role": "assistant", "content": "🔧 system → выполнено\n📋 КОМПЛЕКТУЕМЫЕ: GTX 1660"},
    {"role": "assistant", "content": "━━━━━━━━\n📊 СПИСОК ПРОЦЕССОВ"},
    {"role": "assistant", "content": "Обычный честный ответ"},
]
clean = _sanitize_history(dirty)
check("реплики с 🔧 отброшены", not any("🔧" in m["content"] for m in clean))
check("реплики с ━━━ отброшены", not any("━━━" in m["content"] for m in clean))
check("нормальные реплики сохранены", any("Обычный честный ответ" == m["content"] for m in clean))
check("сообщения пользователя не тронуты", any(m["role"] == "user" for m in clean))

print("\n=== 3. Без tool call — обычный ответ, один запрос ===")
sent_conversations.clear()
tool_calls.clear()


class _PlainCompletions:
    def create(self, model, messages, **kwargs):
        sent_conversations.append(messages)
        return iter([_Chunk(t) for t in ["Привет! ", "Чем помочь?"]])


agent2 = AgentLoop(FakeMemory(), tool_registry=FakeRegistry())
agent2.client.chat.completions = _PlainCompletions()
out2 = "".join(agent2.stream("привет"))
check("без инструмента — ровно один запрос к модели", len(sent_conversations) == 1)
check("инструмент не вызывался", len(tool_calls) == 0)
check("ответ отдан пользователю", out2 == "Привет! Чем помочь?", f"got={out2!r}")

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
