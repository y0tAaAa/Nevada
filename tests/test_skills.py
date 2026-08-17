"""Проверка системы навыков: парсинг, поиск по триггерам, каталог, живая перезагрузка."""
import shutil
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)
import tempfile
from pathlib import Path

failures = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


from skills.manager import SkillManager, parse_skill
from tools.skill_tool import SkillTool

print("=== 1. Парсинг файла навыка ===")
tmp = Path(tempfile.mkdtemp())
(tmp / "тест-навык.md").write_text(
    "---\n"
    "name: Тестовый навык\n"
    "description: Проверяет разбор шапки\n"
    "triggers: тест, проверка, ещё один триггер\n"
    "---\n\n"
    "## Шаги\n\n1. Первый шаг\n2. Второй шаг\n",
    encoding="utf-8",
)

skill = parse_skill(tmp / "тест-навык.md")
check("слаг из имени файла", skill.slug == "тест-навык", f"got={skill.slug}")
check("имя разобрано", skill.name == "Тестовый навык", f"got={skill.name}")
check("описание разобрано", skill.description == "Проверяет разбор шапки")
check("триггеры разобраны (3 шт)", len(skill.triggers) == 3, f"got={skill.triggers}")
check("тело без шапки", skill.body.startswith("## Шаги"), f"got={skill.body[:40]!r}")
check("шапка не попала в тело", "description:" not in skill.body)

print("\n=== 2. Файл без шапки не ломает разбор ===")
(tmp / "без-шапки.md").write_text("Просто инструкции без frontmatter", encoding="utf-8")
plain = parse_skill(tmp / "без-шапки.md")
check("навык без шапки читается", plain is not None)
check("имя = слаг", plain.name == "без-шапки", f"got={plain.name}")
check("описание по умолчанию", plain.description == "без описания")
check("тело сохранено", "Просто инструкции" in plain.body)

print("\n=== 3. Поиск навыка ===")
mgr = SkillManager(skills_dir=tmp)
check("оба навыка загружены", len(mgr.skills) == 2, f"got={len(mgr.skills)}")
check("находится по слагу", mgr.get("тест-навык") is not None)
check("находится по имени", mgr.get("Тестовый навык") is not None)
check("находится по триггеру", mgr.get("проверка") is not None)
check("находится по триггеру в фразе", mgr.get("сделай проверку сейчас") is not None)
check("несуществующий не находится", mgr.get("щупальца кальмара") is None)
check("пустой запрос не находится", mgr.get("") is None)
check("морфология: «проверку» → триггер «проверка»", mgr.get("сделай проверку") is not None)
check("нет ложного совпадения по коротким словам", mgr.get("как дела") is None)

print("\n=== 4. Каталог для промпта ===")
catalog = mgr.catalog()
check("в каталоге есть слаг", "тест-навык" in catalog)
check("в каталоге есть описание", "Проверяет разбор шапки" in catalog)

print("\n=== 5. Живая перезагрузка (новый файл без перезапуска) ===")
tool = SkillTool(manager=mgr)
check("нового навыка ещё нет", tool.manager.get("свежий") is None)

(tmp / "свежий.md").write_text(
    "---\nname: Свежий навык\ndescription: Добавлен на ходу\ntriggers: свежий\n---\nШаг один",
    encoding="utf-8",
)
result = tool.execute("reload")
check("reload сообщает количество", "3" in result, f"got={result}")
check("новый навык найден после reload", tool.manager.get("свежий") is not None)
check("описание инструмента обновилось", "Свежий навык" in tool.description)

print("\n=== 6. Действия инструмента ===")
check("list перечисляет навыки", "тест-навык" in tool.execute("list"))
loaded = tool.execute("load", name="тест-навык")
check("load возвращает инструкции", "Первый шаг" in loaded, f"got={loaded[:80]}")
check("load содержит требование выполнять шаги", "Выполняй эти шаги" in loaded)
check("load без имени отклонён", "Не указано имя" in tool.execute("load"))
check("load несуществующего отклонён", "не найден" in tool.execute("load", name="нетакого"))
check("неизвестное действие отклонено", "Неизвестное действие" in tool.execute("прыгать"))

print("\n=== 7. Реальные навыки проекта ===")
real = SkillManager()
check("реальные навыки загружены", len(real.skills) >= 4, f"got={len(real.skills)}")
check("есть заметка", real.get("заметка") is not None)
check("есть проверка-пк", real.get("комплектующие") is not None)
check("у всех есть описание",
      all(s.description != "без описания" for s in real.skills.values()))
check("у всех есть триггеры", all(s.triggers for s in real.skills.values()))

shutil.rmtree(tmp, ignore_errors=True)

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
