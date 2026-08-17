"""
Parser — парсит tool calls из ответов модели
"""

import json
import re
from typing import Optional, Tuple, Dict, Any


def parse_tool_call(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Ищет tool call в формате XML в тексте:
    <tool>название_инструмента</tool>
    <input>{"параметр": "значение"}</input>
    
    Args:
        text: Текст для парсинга
    
    Returns:
        Кортеж (tool_name, params_dict) или None если tool call не найден
    """
    
    # Ищем теги <tool> ... </tool>
    tool_match = re.search(r'<tool>([^<]+)</tool>', text)
    if not tool_match:
        return None
    
    tool_name = tool_match.group(1).strip()
    
    # Ищем теги <input> ... </input>
    input_match = re.search(r'<input>([^<]+)</input>', text, re.DOTALL)
    if not input_match:
        return None
    
    input_str = input_match.group(1).strip()
    
    # Парсим JSON параметры
    try:
        params = json.loads(input_str)
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        print(f"   Текст: {input_str}")
        return None
    
    return (tool_name, params)


class ToolTagFilter:
    """
    Фильтрует поток токенов: прячет от пользователя XML вызова инструмента
    (<tool>...</tool><input>...</input>), отдавая наружу только обычный текст.
    Умеет работать с тегами, разорванными между токенами.
    """

    START_TAG = "<tool>"
    END_TAG = "</input>"

    def __init__(self):
        self._pending = ""
        self._in_tool = False

    def feed(self, token: str) -> str:
        """Принимает очередной токен, возвращает текст, который можно показать"""
        self._pending += token
        out = []

        while self._pending:
            if not self._in_tool:
                idx = self._pending.find("<")
                if idx == -1:
                    out.append(self._pending)
                    self._pending = ""
                    break

                out.append(self._pending[:idx])
                rest = self._pending[idx:]

                if self.START_TAG.startswith(rest):
                    # Возможно, это начало <tool> — ждём продолжения
                    self._pending = rest
                    break

                if rest.startswith(self.START_TAG):
                    self._in_tool = True
                    self._pending = rest[len(self.START_TAG):]
                    continue

                # Обычный символ '<', не начало тега
                out.append(rest[0])
                self._pending = rest[1:]
            else:
                end = self._pending.find(self.END_TAG)
                if end == -1:
                    # Держим хвост на случай, если </input> разорван между токенами
                    keep = len(self.END_TAG) - 1
                    self._pending = self._pending[-keep:] if keep else ""
                    break

                self._pending = self._pending[end + len(self.END_TAG):]
                self._in_tool = False

        return "".join(out)

    def flush(self) -> str:
        """Отдаёт остаток буфера по завершении стрима"""
        if self._in_tool:
            self._pending = ""
            return ""
        tail, self._pending = self._pending, ""
        return tail


def extract_text_before_tool(text: str) -> str:
    """Возвращает текст до первого tool call"""
    match = re.search(r'<tool>', text)
    if not match:
        return text
    return text[:match.start()]


def extract_text_after_tool(text: str) -> str:
    """Возвращает текст после последнего </input>"""
    match = re.search(r'</input>', text)
    if not match:
        return ""
    return text[match.end():]
