"""
SkillManager — навыки Nevada как обычные markdown-файлы.

Навык = файл в папке skills/ с «шапкой» (name/description/triggers) и телом
с пошаговыми инструкциями. Агент видит каталог навыков, загружает нужный
и выполняет его шаги. Новый навык добавляется файлом, без правки кода.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# Длина основы слова для нечёткого сопоставления. 5 символов достаточно
# специфичны, чтобы «проверка»/«проверку» совпали, а разные слова — нет.
_STEM_LENGTH = 5
_MIN_WORD_LENGTH = 4


def _stems(text: str) -> set:
    """Основы слов длиной от 4 символов — для сопоставления с учётом падежей"""
    return {
        word[:_STEM_LENGTH]
        for word in re.findall(r"\w+", text.lower())
        if len(word) >= _MIN_WORD_LENGTH
    }


@dataclass
class Skill:
    """Один навык"""
    slug: str                      # имя файла без расширения
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    body: str = ""

    def matches(self, query: str) -> bool:
        """Похож ли запрос на этот навык (по имени, слагу или триггерам)"""
        q = query.strip().lower()
        if not q:
            return False
        if q in self.slug.lower() or q in self.name.lower():
            return True
        if any(q in trigger.lower() or trigger.lower() in q for trigger in self.triggers):
            return True

        # Сопоставление по основам слов: русская морфология мешает простому
        # вхождению подстроки («проверка» не найдётся во фразе «сделай проверку»)
        query_stems = _stems(q)
        if not query_stems:
            return False
        return any(_stems(trigger) & query_stems for trigger in self.triggers)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_skill(path: Path) -> Optional[Skill]:
    """Разбирает файл навыка. Возвращает None, если файл нечитаемый"""
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Не удалось прочитать навык {path.name}: {e}")
        return None

    meta: Dict[str, str] = {}
    body = raw

    match = _FRONTMATTER_RE.match(raw)
    if match:
        header, body = match.group(1), match.group(2)
        for line in header.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = value.strip()

    triggers = [t.strip() for t in meta.get("triggers", "").split(",") if t.strip()]

    return Skill(
        slug=path.stem,
        name=meta.get("name", path.stem),
        description=meta.get("description", "без описания"),
        triggers=triggers,
        body=body.strip(),
    )


class SkillManager:
    """Каталог навыков из папки skills/"""

    def __init__(self, skills_dir: Path = None):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).parent
        self.skills: Dict[str, Skill] = {}
        self.reload()

    def reload(self) -> int:
        """Пересканирует папку. Возвращает число загруженных навыков"""
        self.skills.clear()
        if not self.skills_dir.exists():
            return 0

        for path in sorted(self.skills_dir.glob("*.md")):
            skill = parse_skill(path)
            if skill:
                self.skills[skill.slug] = skill
        return len(self.skills)

    def catalog(self) -> str:
        """Короткий список навыков для системного промпта"""
        if not self.skills:
            return "Навыков пока нет"
        lines = []
        for skill in self.skills.values():
            lines.append(f"        - {skill.slug}: {skill.name} — {skill.description}")
        return "\n".join(lines)

    def get(self, query: str) -> Optional[Skill]:
        """Находит навык по слагу, имени или триггеру"""
        if not query:
            return None

        key = query.strip().lower()
        if key in self.skills:
            return self.skills[key]

        for skill in self.skills.values():
            if skill.matches(key):
                return skill
        return None

    def names(self) -> List[str]:
        return list(self.skills)
