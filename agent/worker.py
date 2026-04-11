"""
AgentWorker — QThread для выполнения агента без блокировки UI
"""

from PyQt6.QtCore import QThread, pyqtSignal
from agent.loop import AgentLoop
from agent.parser import parse_tool_call


class AgentWorker(QThread):
    """Выполняет агент в отдельном потоке"""
    
    # Сигналы
    token_received = pyqtSignal(str)  # Каждый токен от ответа
    thinking_received = pyqtSignal(str)  # Промежуточное размышление
    response_ready = pyqtSignal(str)  # Полный ответ
    error_occurred = pyqtSignal(str)  # Ошибка
    
    def __init__(self, agent: AgentLoop, user_input: str):
        super().__init__()
        self.agent = agent
        self.user_input = user_input
    
    def run(self):
        """Основной метод потока"""
        try:
            full_response = ""
            in_thinking = False
            thinking_buffer = ""
            
            # Итерируем по токенам из streaming
            for token in self.agent.stream(self.user_input):
                full_response += token
                
                # Проверяем открытие тега <think>
                if "<think>" in token:
                    in_thinking = True
                    self.thinking_received.emit("🤔 Размышляю...\n")
                    continue
                
                # Проверяем закрытие тега </think>
                if "</think>" in token:
                    in_thinking = False
                    self.thinking_received.emit("")  # Очищаем thinking
                    thinking_buffer = ""
                    continue
                
                # Если внутри thinking, собираем в буфер
                if in_thinking:
                    thinking_buffer += token
                    self.thinking_received.emit(token)
                else:
                    # Основной ответ
                    self.token_received.emit(token)
                    
                    # Проверяем наличие завершённого tool call
                    if "</input>" in full_response:
                        tool_call = parse_tool_call(full_response)
                        if tool_call and self.agent.tool_registry:
                            tool_name, params = tool_call
                            try:
                                result = self.agent.tool_registry.execute(tool_name, params)
                                # Отправляем результат как финальный ответ если нет других токенов после tool call
                                if token.strip() in ["</input>", ">"] or full_response.endswith("</input>"):
                                    self.token_received.emit(f"\n\n{result}\n")
                            except Exception as e:
                                error_msg = f"❌ Ошибка инструмента {tool_name}: {str(e)}"
                                self.token_received.emit(f"\n\n{error_msg}\n")
            
            # Испускаем финальный ответ
            self.response_ready.emit(full_response)
        
        except Exception as e:
            error_msg = f"❌ Ошибка агента: {str(e)}"
            self.error_occurred.emit(error_msg)
