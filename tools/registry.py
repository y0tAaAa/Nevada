"""
ToolRegistry — реестр всех доступных инструментов агента
"""

from typing import Dict, Callable, Any, Tuple


class ToolRegistry:
    """Реестр инструментов с методом выполнения"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.descriptions: Dict[str, str] = {}
    
    def register(self, name: str, tool_instance, description: str = ""):
        """
        Регистрирует инструмент в реестре.
        
        Args:
            name: Уникальное имя инструмента
            tool_instance: Экземпляр инструмента с методом execute() или другой вызываемый объект
            description: Описание инструмента для системного промпта
        """
        self.tools[name] = tool_instance
        self.descriptions[name] = description or f"Инструмент {name}"
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Выполняет инструмент с переданными параметрами.
        
        Args:
            tool_name: Имя инструмента
            params: Словарь параметров
        
        Returns:
            Результат выполнения инструмента
        
        Raises:
            ValueError: Если инструмент не найден
        """
        if tool_name not in self.tools:
            raise ValueError(f"❌ Инструмент '{tool_name}' не зарегистрирован")
        
        tool = self.tools[tool_name]
        
        try:
            # Пытаеся вызвать execute() если есть
            if hasattr(tool, 'execute'):
                result = tool.execute(**params)
            else:
                # Или прямой вызов
                result = tool(**params)
            
            return str(result)
        
        except TypeError as e:
            return f"❌ Ошибка параметров инструмента {tool_name}: {str(e)}"
        except Exception as e:
            return f"❌ Ошибка выполнения инструмента {tool_name}: {str(e)}"
    
    def describe(self) -> str:
        """
        Возвращает отформатированное описание всех доступных инструментов.
        Используется в системном промпте агента.
        """
        if not self.tools:
            return "Инструменты: не зарегистрировано"
        
        lines = ["Доступные инструменты:"]
        for name, desc in self.descriptions.items():
            lines.append(f"  • {name}: {desc}")
        
        return "\n".join(lines)
    
    def list(self) -> list:
        """Возвращает список имён всех зарегистрированных инструментов"""
        return list(self.tools.keys())
