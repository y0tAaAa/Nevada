"""
AgentLoop — основной цикл агента, взаимодействие с Groq API
"""

from typing import Generator, Optional
import openai
from config import Config
from memory.manager import MemoryManager
from agent.prompt import get_system_prompt
from agent.parser import parse_tool_call


class AgentLoop:
    """Главный цикл агента с поддержкой streaming"""
    
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
    
    def stream(self, user_input: str) -> Generator[str, None, str]:
        """
        Streaming ответ от агента токен-за-токеном.
        
        Yields:
            Токены ответа
        
        Returns:
            Полный ответ в конце
        """
        # Получаем недавнюю историю
        history = self.memory.get_recent(n=10)
        
        # Генерируем системный промпт
        tools_desc = (
            self.tool_registry.describe() 
            if self.tool_registry 
            else "Инструменты: нет доступных инструментов"
        )
        system_prompt = get_system_prompt(tools_desc)
        
        # Строим сообщения для API
        messages = history + [{"role": "user", "content": user_input}]
        
        # Стриминг от Groq
        full_response = ""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=0.7,
                max_tokens=2048,
                stream=True,
                top_p=0.95
            )
            
            # Итерируем по токенам
            for chunk in response:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield token
        
        except openai.AuthenticationError:
            error_msg = "❌ Ошибка аутентификации: проверьте GROQ_API_KEY в .env"
            full_response = error_msg
            yield error_msg
        except openai.APIError as e:
            error_msg = f"❌ Ошибка API: {str(e)}"
            full_response = error_msg
            yield error_msg
        
        # Сохраняем в память
        self.memory.save(user_input, full_response)
        
        return full_response
    
    def run(self, user_input: str) -> str:
        """
        Синхронный вызов агента (ждёт полного ответа).
        
        Args:
            user_input: Текст от пользователя
        
        Returns:
            Полный ответ ассистента
        """
        full_response = ""
        
        for token in self.stream(user_input):
            full_response += token
            # Проверяем наличие tool call
            tool_call = parse_tool_call(full_response)
            if tool_call and self.tool_registry:
                tool_name, params = tool_call
                try:
                    result = self.tool_registry.execute(tool_name, params)
                    print(f"✅ Инструмент {tool_name} выполнен: {result}")
                except Exception as e:
                    print(f"❌ Ошибка выполнения инструмента {tool_name}: {e}")
        
        return full_response
