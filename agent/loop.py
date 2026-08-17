"""
AgentLoop — основной цикл агента, взаимодействие с Groq API
"""

import re
from typing import Generator, List, Dict

import openai
from config import Config
from memory.manager import MemoryManager
from agent.prompt import get_system_prompt
from agent.parser import parse_tool_call, ToolTagFilter


# Сколько раз подряд агент может вызвать инструмент в рамках одного запроса.
# Навыки съедают один шаг на загрузку инструкций, а сами сценарии обычно
# требуют 3-5 вызовов — поэтому запас должен быть заметным.
MAX_TOOL_STEPS = 8

# Признаки служебных блоков, которые раньше по ошибке сохранялись в память
# как реплика ассистента. Такие записи нужно отбрасывать при загрузке истории,
# иначе модель принимает их за образец и подделывает вывод инструментов.
CONTAMINATION_MARKERS = ("🔧", "━━━")

# Действия, которые нельзя выполнять без РЕАЛЬНОГО согласия пользователя.
# Проверка стоит здесь, а не внутри инструментов: модель может сама подставить
# "confirm": true, поэтому решение принимает человек через диалог в UI.
CONFIRM_REQUIRED = {
    ("app", "type_text"),
    ("app", "hotkey"),
    ("file", "delete"),
    ("file", "write"),
}


def _describe_action(tool_name: str, params: Dict) -> tuple:
    """Возвращает (краткое описание, подробности) для окна подтверждения"""
    action = params.get("action", "")

    if tool_name == "app" and action == "type_text":
        target = params.get("title") or "активное окно"
        return f"Вставить текст в окно «{target}»", params.get("text", "")
    if tool_name == "app" and action == "hotkey":
        target = params.get("title") or "активное окно"
        return f"Нажать сочетание клавиш в «{target}»", params.get("keys", "")
    if tool_name == "file" and action == "delete":
        return "Удалить файл или папку", params.get("path", "")
    if tool_name == "file" and action == "write":
        return f"Записать файл {params.get('path', '')}", (params.get("content") or "")[:400]
    if tool_name == "shell":
        return "Выполнить потенциально опасную команду", params.get("command", "")

    return f"Выполнить {tool_name} ({action})", str(params)


def _needs_confirmation(tool_name: str, params: Dict, tool_registry) -> bool:
    """Требует ли это конкретное действие подтверждения пользователя"""
    action = params.get("action", "")
    if (tool_name, action) in CONFIRM_REQUIRED:
        return True

    # Для shell спрашиваем сам инструмент — он знает свои деструктивные паттерны
    if tool_name == "shell":
        tool = getattr(tool_registry, "tools", {}).get("shell")
        command = params.get("command", "")
        if tool is not None and hasattr(tool, "_is_destructive"):
            try:
                return bool(tool._is_destructive(command))
            except Exception:
                return False
    return False

# Шаблон, которым результат инструмента возвращается модели.
# Жёстко требуем опираться только на реальные данные — иначе модель
# склонна выдумывать правдоподобный вывод инструмента.
TOOL_RESULT_TEMPLATE = (
    "РЕЗУЛЬТАТ ВЫПОЛНЕНИЯ ИНСТРУМЕНТА {tool_name}:\n"
    "```\n{result}\n```\n\n"
    "Это реальный вывод инструмента. Ответь пользователю на основе ТОЛЬКО этих данных. "
    "Не придумывай никаких значений, которых нет в выводе выше. "
    "Если нужных данных в выводе нет — честно скажи, что получить их не удалось."
)


# Признаки того, что модель называет КОНКРЕТНЫЕ показатели системы.
# Если при этом ни один инструмент не вызывался — это выдумка.
_FACT_KEYWORDS = re.compile(
    r"аптайм|работает уже|загрузк\w+ (?:процессор|цп|cpu)|"
    r"использовани\w+ (?:оперативн\w+ )?памят|оперативн\w+ памят|"
    r"свободно\s+\d|занято\s+\d|"
    r"\bCPU\b|\bRAM\b|\bГБ\b|\bGB\b|"
    r"сейчас\s+\d{1,2}[:.]\d{2}|\d{1,2}[:.]\d{2}\s*(?:утра|вечера|дня|ночи)|"
    r"текущее время|видеокарт|процессор\s+\w*\s*(?:intel|amd|ryzen|core)",
    re.IGNORECASE,
)
_HAS_DIGIT = re.compile(r"\d")


def _looks_like_unverified_facts(text: str) -> bool:
    """
    Похоже ли, что модель привела конкретные данные о системе «из головы».
    Проверяется только когда за ход не выполнялось ни одного инструмента.
    """
    if not text or not _HAS_DIGIT.search(text):
        return False
    return bool(_FACT_KEYWORDS.search(text))


def _sanitize_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Убирает из истории ассистентские реплики со служебными блоками вывода
    инструментов (наследие старых версий и уже существующих БД).
    """
    return [
        msg for msg in history
        if not (
            msg.get("role") == "assistant"
            and any(marker in msg.get("content", "") for marker in CONTAMINATION_MARKERS)
        )
    ]


class AgentLoop:
    """Главный цикл агента с поддержкой streaming и вызова инструментов"""

    def __init__(self, memory: MemoryManager, tool_registry=None):
        """
        Args:
            memory: MemoryManager для сохранения истории
            tool_registry: ToolRegistry для выполнения инструментов
        """
        self.memory = memory
        self.tool_registry = tool_registry
        self.config = Config()

        # Инициализируем клиент Groq
        self.client = openai.OpenAI(
            api_key=self.config.groq_api_key,
            base_url=self.config.api_base
        )

    def _active_skill_instructions(self, user_input: str) -> str:
        """
        Находит навык, подходящий под запрос, и возвращает его инструкции
        для подстановки в системный промпт. Пустая строка, если навыка нет.
        """
        if not self.tool_registry:
            return ""

        skill_tool = getattr(self.tool_registry, "tools", {}).get("skill")
        manager = getattr(skill_tool, "manager", None)
        if manager is None:
            return ""

        try:
            skill = manager.get(user_input)
        except Exception:
            return ""

        if not skill:
            return ""

        return (
            f"\n\nАКТИВНЫЙ НАВЫК ДЛЯ ЭТОГО ЗАПРОСА — «{skill.name}».\n"
            "Выполни его шаги по порядку, ОБЯЗАТЕЛЬНО вызывая указанные инструменты. "
            "Не отвечай по памяти: пока инструмент не вернул данные, ты их не знаешь.\n"
            f"{'-' * 50}\n{skill.body}\n{'-' * 50}"
        )

    def stream(self, user_input: str, on_tool_result=None, confirm_callback=None) -> Generator[str, None, str]:
        """
        Streaming ответ от агента токен-за-токеном.

        Если модель вызывает инструмент, цикл выполняет его, возвращает
        РЕАЛЬНЫЙ результат обратно в модель и продолжает диалог — поэтому
        итоговый ответ опирается на фактические данные, а не на выдумку.

        Args:
            user_input: Запрос пользователя
            on_tool_result: Необязательный коллбек (tool_name, result). Если задан,
                результат инструмента отдаётся через него (UI рисует карточку),
                а не вставляется текстом в поток токенов.

        Yields:
            Токены ответа (XML вызова инструмента скрыт от пользователя)
        """
        history = _sanitize_history(self.memory.get_recent(n=10))

        tools_desc = (
            self.tool_registry.describe()
            if self.tool_registry
            else "Инструменты: нет доступных инструментов"
        )
        system_prompt = get_system_prompt(tools_desc)

        # Если запрос попадает в навык — подставляем его инструкции сразу.
        # Раньше загрузка навыка зависела от желания модели вызвать skill/load,
        # и на коротких запросах вроде «утро» она отвечала выдумкой без инструментов.
        skill_instructions = self._active_skill_instructions(user_input)
        if skill_instructions:
            system_prompt += skill_instructions

        conversation: List[Dict[str, str]] = list(history) + [
            {"role": "user", "content": user_input}
        ]

        visible_response = ""
        # Отдельно копим ТОЛЬКО текст самой модели: служебные блоки с выводом
        # инструментов в память попадать не должны — иначе на следующих ходах
        # модель считает их своей репликой и начинает подделывать такие блоки
        model_prose = ""
        failed = False
        tools_used = 0
        retried_for_facts = False

        for step in range(MAX_TOOL_STEPS):
            raw_response = ""
            tag_filter = ToolTagFilter()

            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *conversation
                    ],
                    temperature=0.7,
                    max_tokens=2048,
                    stream=True,
                    top_p=0.95,
                    # Обрываем генерацию сразу после вызова инструмента — так модель
                    # физически не может дописать выдуманный «результат» в том же ответе
                    stop=["</input>"]
                )

                for chunk in response:
                    token = chunk.choices[0].delta.content
                    if not token:
                        continue
                    raw_response += token
                    visible = tag_filter.feed(token)
                    if visible:
                        visible_response += visible
                        model_prose += visible
                        yield visible

                tail = tag_filter.flush()
                if tail:
                    visible_response += tail
                    model_prose += tail
                    yield tail

            except openai.AuthenticationError:
                failed = True
                error_msg = "❌ Ошибка аутентификации: проверьте GROQ_API_KEY в .env"
                visible_response = error_msg
                yield error_msg
                break
            except openai.APIError as e:
                failed = True
                error_msg = f"❌ Ошибка API: {str(e)}"
                visible_response = error_msg
                yield error_msg
                break
            except Exception as e:
                failed = True
                error_msg = f"❌ Непредвиденная ошибка: {str(e)}"
                visible_response = error_msg
                yield error_msg
                break

            # Стоп-последовательность в ответ не включается — возвращаем закрывающий
            # тег на место, иначе parse_tool_call не распознает вызов
            if "<tool>" in raw_response and "<input>" in raw_response and "</input>" not in raw_response:
                raw_response += "</input>"

            # Есть ли вызов инструмента?
            tool_call = parse_tool_call(raw_response) if self.tool_registry else None
            if not tool_call:
                # Страж выдумок: модель назвала конкретные показатели системы,
                # ни разу не обратившись к инструментам. Требуем проверить данные.
                if (
                    self.tool_registry
                    and tools_used == 0
                    and not retried_for_facts
                    and _looks_like_unverified_facts(raw_response)
                ):
                    retried_for_facts = True
                    warning = (
                        "\n\n⚠️ Эти данные не подтверждены инструментами. Проверяю по системе…\n\n"
                    )
                    visible_response += warning
                    yield warning
                    # Выдуманный текст в память не пойдёт — начинаем ответ заново
                    model_prose = ""
                    conversation.append({"role": "assistant", "content": raw_response})
                    conversation.append({
                        "role": "user",
                        "content": (
                            "СТОП. Ты привёл конкретные показатели (время, аптайм, загрузку CPU/RAM, "
                            "характеристики), не вызвав ни одного инструмента — значит, ты их выдумал. "
                            "Ты НЕ ЗНАЕШЬ этих значений без инструментов. "
                            "Сейчас вызови нужные инструменты (system/get_time, system/get_info, "
                            "system/get_hardware) и ответь заново, используя ТОЛЬКО их реальный вывод. "
                            "Начни ответ сразу с вызова инструмента."
                        )
                    })
                    continue
                break

            tool_name, params = tool_call
            tools_used += 1

            # Гейт подтверждения. Модель могла сама подставить "confirm": true —
            # это не считается: разрешение даёт только человек через диалог.
            if _needs_confirmation(tool_name, params, self.tool_registry):
                if confirm_callback is None:
                    # UI недоступен (например, headless-прогон) — не выполняем
                    result = (
                        "❌ Действие требует подтверждения пользователя, "
                        "но окно подтверждения недоступно. Действие не выполнено."
                    )
                else:
                    action_text, details = _describe_action(tool_name, params)
                    approved = confirm_callback(tool_name, action_text, details)
                    if approved:
                        params = {**params, "confirm": True}
                        try:
                            result = self.tool_registry.execute(tool_name, params)
                        except Exception as e:
                            result = f"❌ Ошибка выполнения инструмента {tool_name}: {e}"
                    else:
                        result = (
                            "❌ Пользователь ОТКЛОНИЛ это действие. "
                            "Не пытайся выполнить его снова и не придумывай, "
                            "будто оно выполнено — сообщи пользователю об отказе."
                        )
            else:
                try:
                    result = self.tool_registry.execute(tool_name, params)
                except Exception as e:
                    result = f"❌ Ошибка выполнения инструмента {tool_name}: {e}"

            # Показываем пользователю, что инструмент реально отработал
            if on_tool_result is not None:
                # UI отрисует отдельную карточку результата
                on_tool_result(tool_name, result)
                visible_response += f"\n\n[{tool_name}]\n{result}\n\n"
            else:
                evidence = f"\n\n🔧 {tool_name} → выполнено\n{result}\n\n"
                visible_response += evidence
                yield evidence

            # Возвращаем настоящий результат модели и просим ответить по нему
            conversation.append({"role": "assistant", "content": raw_response})
            conversation.append({
                "role": "user",
                "content": TOOL_RESULT_TEMPLATE.format(tool_name=tool_name, result=result)
            })
        else:
            # Шаги исчерпаны. Не оставляем пользователя с одним предупреждением —
            # просим модель дать итоговый ответ по уже собранным данным, без инструментов
            conversation.append({
                "role": "user",
                "content": (
                    "Лимит вызовов инструментов исчерпан. Больше инструменты не вызывай. "
                    "Сформулируй итоговый ответ пользователю по уже полученным выше данным. "
                    "Ничего не выдумывай: если каких-то данных нет, так и скажи."
                )
            })
            try:
                final = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "system", "content": system_prompt}, *conversation],
                    temperature=0.7,
                    max_tokens=1024,
                    stream=True,
                    top_p=0.95,
                )
                for chunk in final:
                    token = chunk.choices[0].delta.content
                    if token:
                        visible_response += token
                        model_prose += token
                        yield token
            except Exception as e:
                fallback = f"\n\n⚠️ Достигнут лимит вызовов инструментов ({e})."
                visible_response += fallback
                yield fallback

        # Сохраняем в память только удачные обмены и только прозу самой модели:
        # маркеры выполнения и сырой вывод инструментов в историю не пишем
        if not failed and model_prose.strip():
            self.memory.save(user_input, model_prose.strip())

        return visible_response

    def run(self, user_input: str) -> str:
        """
        Синхронный вызов агента (ждёт полного ответа).

        Args:
            user_input: Текст от пользователя

        Returns:
            Полный ответ ассистента
        """
        return "".join(self.stream(user_input))
