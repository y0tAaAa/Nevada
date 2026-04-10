"""
AgentWorker — QThread для выполнения агента без блокировки UI
"""

from PyQt6.QtCore import QThread, pyqtSignal
from agent.loop import AgentLoop


class AgentWorker(QThread):
    """Выполняет агент в отдельном потоке"""
    
    # Сигналы
    token_received = pyqtSignal(str)  # Каждый токен
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
            
            # Итерируем по токенам из streaming
            for token in self.agent.stream(self.user_input):
                full_response += token
                self.token_received.emit(token)
            
            # Испускаем финальный ответ
            self.response_ready.emit(full_response)
        
        except Exception as e:
            error_msg = f"❌ Ошибка агента: {str(e)}"
            self.error_occurred.emit(error_msg)
