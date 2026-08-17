"""
Страж выдумок: если модель называет показатели системы, не вызвав инструменты,
цикл обязан её остановить и заставить проверить данные.
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


class _FakeChat:
    def __init__(self, completions): self.completions = completions


class _FakeClient:
    def __init__(self, *a, **k): self.chat = _FakeChat(None)


openai_mod.OpenAI = _FakeClient
openai_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})
openai_mod.APIError = type("APIError", (Exception,), {})
sys.modules["openai"] = openai_mod

from agent.loop import AgentLoop, _looks_like_unverified_facts

print("=== 1. Детектор выдуманных показателей ===")
# Точный текст из скриншота пользователя
screenshot = ("Доброе утро! Сейчас 8:45 утра. Ваш компьютер работает уже 2 часа и 15 минут. "
              "Загрузка процессора составляет 10%, а использование оперативной памяти — 60%.")
check("ловит текст со скриншота", _looks_like_unverified_facts(screenshot))
check("ловит аптайм", _looks_like_unverified_facts("Аптайм 6 дней"))
check("ловит RAM в ГБ", _looks_like_unverified_facts("Занято 12.5 ГБ памяти"))
check("ловит время", _looks_like_unverified_facts("Сейчас 14:30"))
check("ловит видеокарту", _looks_like_unverified_facts("Видеокарта RTX 4090, 24 ГБ"))

print("\n=== 2. Не срабатывает на безобидных ответах ===")
check("обычное приветствие", not _looks_like_unverified_facts("Привет! Чем помочь?"))
check("текст без цифр", not _looks_like_unverified_facts("Могу открыть поиск или программу"))
check("математика без системных слов", not _looks_like_unverified_facts("15% от 200 это 30"))
check("предложение помощи", not _looks_like_unverified_facts(
    "Я готов помочь. Например, могу запустить программу или выполнить другое действие."))

print("\n=== 3. Цикл заставляет перепроверить данные ===")
calls = []
executed = []


class _GuardCompletions:
    """1-й ответ — выдумка без инструментов. 2-й — вызов инструмента. 3-й — честный ответ."""
    def create(self, model, messages, **kwargs):
        calls.append(messages)
        n = len(calls)
        if n == 1:
            toks = ["Доброе утро! ", "Сейчас 8:45 утра. ",
                    "Загрузка процессора 10%, использование оперативной памяти 60%."]
        elif n == 2:
            toks = ["<tool>", "system", "</tool>", "<input>", '{"action":"get_info"}']
        else:
            toks = ["По данным системы: CPU 24.3%, RAM 13.3 GB из 15.7 GB."]
        return iter([_Chunk(t) for t in toks])


class FakeRegistry:
    tools = {}

    def execute(self, name, params):
        executed.append((name, params))
        return "CPU: 12 ядер (24.3%)\nRAM: 13.3 GB / 15.7 GB (85.0%)"

    def describe(self):
        return "system: информация о системе"


class FakeMemory:
    def __init__(self): self.saved = []
    def get_recent(self, n=10): return []
    def save(self, u, a): self.saved.append((u, a))


mem = FakeMemory()
agent = AgentLoop(mem, tool_registry=FakeRegistry())
agent.client.chat.completions = _GuardCompletions()
out = "".join(agent.stream("утро"))

check("страж вмешался (есть предупреждение)", "не подтверждены инструментами" in out,
      f"got={out[:200]}")
check("после вмешательства инструмент вызван", len(executed) == 1, f"executed={executed}")
check("сделано 3 обращения к модели", len(calls) == 3, f"got={len(calls)}")
check("модели передано требование перепроверить",
      any("СТОП" in m["content"] for m in calls[1] if isinstance(m.get("content"), str)))
check("итоговый ответ содержит реальные данные", "24.3" in out, f"got={out[-200:]}")

saved_answer = mem.saved[0][1] if mem.saved else ""
check("выдумка НЕ попала в память", "8:45" not in saved_answer, f"saved={saved_answer!r}")
check("в память попал честный ответ", "24.3" in saved_answer, f"saved={saved_answer!r}")

print("\n=== 4. Страж не мешает, когда инструменты уже вызывались ===")
calls.clear()
executed.clear()


class _NormalCompletions:
    def create(self, model, messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:
            toks = ["<tool>", "system", "</tool>", "<input>", '{"action":"get_info"}']
        else:
            toks = ["Загрузка процессора 24.3%, память 13.3 ГБ."]
        return iter([_Chunk(t) for t in toks])


agent2 = AgentLoop(FakeMemory(), tool_registry=FakeRegistry())
agent2.client.chat.completions = _NormalCompletions()
out2 = "".join(agent2.stream("что с системой"))
check("предупреждения нет", "не подтверждены инструментами" not in out2)
check("лишних обращений нет", len(calls) == 2, f"got={len(calls)}")

print("\n=== 5. Навык подставляется в промпт автоматически ===")


class SkillStub:
    class _Skill:
        name = "Утренний дайджест"
        body = "1. Узнай время через system/get_time"
    class _Manager:
        skills = {}
        def get(self, q):
            return SkillStub._Skill() if "утро" in q.lower() else None
    manager = _Manager()


class RegistryWithSkill(FakeRegistry):
    tools = {"skill": SkillStub()}


agent3 = AgentLoop(FakeMemory(), tool_registry=RegistryWithSkill())
hint = agent3._active_skill_instructions("утро")
check("навык найден по короткому запросу", "Утренний дайджест" in hint, f"got={hint[:80]}")
check("в промпт попали шаги навыка", "system/get_time" in hint)
check("есть запрет отвечать по памяти", "не знаешь" in hint.lower())
check("для нерелевантного запроса пусто", agent3._active_skill_instructions("привет") == "")

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
