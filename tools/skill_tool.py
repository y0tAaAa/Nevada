"""
SkillTool — доступ агента к навыкам (markdown-инструкциям из папки skills/).

Агент видит каталог навыков в описании инструмента, загружает нужный
действием load и затем выполняет его шаги обычными инструментами.
"""

from skills.manager import SkillManager


class SkillTool:
    """Навыки Nevada"""

    def __init__(self, manager: SkillManager = None):
        self.manager = manager or SkillManager()

    @property
    def description(self) -> str:
        """
        Описание пересобирается на каждый запрос — так свежедобавленные
        файлы навыков попадают в промпт без перезапуска приложения.
        """
        return (
            "Навыки — готовые пошаговые сценарии. Параметр action — ТОЛЬКО одно из:\n"
            "      • list — перечислить доступные навыки\n"
            "      • load — загрузить инструкции навыка: {\"action\":\"load\",\"name\":\"утренний-дайджест\"}\n"
            "      • reload — перечитать папку навыков с диска\n"
            "      Если запрос пользователя похож на один из навыков ниже — СНАЧАЛА загрузи его\n"
            "      через load и дальше действуй строго по полученным инструкциям.\n"
            "      Доступные навыки:\n"
            f"{self.manager.catalog()}"
        )

    def execute(self, action: str = "list", name: str = None) -> str:
        try:
            if action == "list":
                return self._list()
            if action == "load":
                return self._load(name)
            if action == "reload":
                count = self.manager.reload()
                return f"✅ Перечитано навыков: {count}"
            return f"❌ Неизвестное действие: {action}. Доступны: list, load, reload"
        except Exception as e:
            return f"❌ Ошибка работы с навыками: {e}"

    def _list(self) -> str:
        if not self.manager.skills:
            return "Навыков пока нет. Добавьте .md файл в папку skills/"
        lines = ["Доступные навыки:"]
        for skill in self.manager.skills.values():
            triggers = f" (триггеры: {', '.join(skill.triggers)})" if skill.triggers else ""
            lines.append(f"  • {skill.slug} — {skill.name}: {skill.description}{triggers}")
        return "\n".join(lines)

    def _load(self, name: str) -> str:
        if not name:
            return "❌ Не указано имя навыка (параметр name)"

        skill = self.manager.get(name)
        if not skill:
            available = ", ".join(self.manager.names()) or "нет навыков"
            return f"❌ Навык '{name}' не найден. Доступны: {available}"

        return (
            f"ИНСТРУКЦИИ НАВЫКА «{skill.name}»\n"
            f"{'-' * 50}\n"
            f"{skill.body}\n"
            f"{'-' * 50}\n"
            "Выполняй эти шаги по порядку, используя доступные инструменты. "
            "Данные бери только из реального вывода инструментов."
        )
