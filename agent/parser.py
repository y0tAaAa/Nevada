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
