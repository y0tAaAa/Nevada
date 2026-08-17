"""
Проверка AppTool. Реально ничего не печатаем в чужие окна и не жмём клавиши —
проверяем перечисление, белый список и то, что защита от ввода без подтверждения
действительно срабатывает.
"""
import os
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from tests.conftest_paths import setup_paths, PROJECT_ROOT
setup_paths(offscreen=False)
import os
os.chdir(PROJECT_ROOT)

# Python 3.8+ на Windows не берёт DLL из PATH — нужен add_dll_directory

failures = []


def check(name, cond, detail=""):
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


from tools.app_tool import AppTool

tool = AppTool()

print("=== 1. Белый список программ ===")
progs = tool.execute("list_programs")
check("блокнот в списке", "блокнот" in progs)
check("claude в списке", "claude" in progs)
check("незнакомая программа отклоняется", "не в белом списке" in tool.execute("launch", program="virus.exe"))
print(progs.split(chr(10))[0], "...")

print("\n=== 2. Перечисление реальных окон ===")
wins = tool.execute("list_windows")
check("окна перечислены (реальные данные)", "Сейчас открыты окна" in wins, f"got={wins[:120]}")
print(chr(10).join(wins.splitlines()[:6]), "...")

print("\n=== 3. Ввод текста БЕЗ подтверждения блокируется ===")
r = tool.execute("type_text", title="Блокнот", text="секретный текст")
check("без confirm ввод не выполняется", "Требуется подтверждение" in r, f"got={r[:120]}")
check("показан предпросмотр текста", "секретный текст" in r)
check("указано целевое окно", "Блокнот" in r)

print("\n=== 4. Горячие клавиши без подтверждения блокируются ===")
r2 = tool.execute("hotkey", keys="ctrl+s")
check("без confirm клавиши не жмутся", "Требуется подтверждение" in r2, f"got={r2[:120]}")

print("\n=== 5. Опасные окна запрещены даже с подтверждением ===")
r3 = tool.execute("type_text", title="Диспетчер задач", text="x", confirm=True)
check("ввод в диспетчер задач запрещён", "запрещён" in r3, f"got={r3[:120]}")

print("\n=== 6. Валидация параметров ===")
check("неизвестное действие отклонено", "Неизвестное действие" in tool.execute("fly_to_moon"))
check("поиск без запроса отклонён", "Не указан поисковый запрос" in tool.execute("search"))
check("неизвестная поисковая система отклонена",
      "Неизвестная поисковая система" in tool.execute("search", query="тест", engine="bing"))
check("focus без title отклонён", "Не указан заголовок" in tool.execute("focus"))
check("launch без program отклонён", "Не указано" in tool.execute("launch"))

print("\n=== 6b. Слепой ввод без указания окна запрещён ===")
blind = tool.execute("type_text", text="куда-нибудь", confirm=True)
check("ввод без title отклонён", "Нужно явно указать окно" in blind, f"got={blind[:120]}")

print("\n=== 6c. Ввод в несуществующее окно не отправляет нажатия ===")
ghost = tool.execute("type_text", title="ОкноКоторогоНетНаСвете12345", text="x", confirm=True)
check("несуществующее окно отклонено", "не найдено" in ghost, f"got={ghost[:120]}")

print("\n=== 7. Добавление программы в белый список ===")
tool.add_program("мой редактор", "notepad.exe")
check("программа добавилась", "мой редактор" in tool.execute("list_programs"))

print()
if failures:
    print(f"ИТОГ: провалено {len(failures)}: {failures}")
    sys.exit(1)
print("ИТОГ: все проверки пройдены")
