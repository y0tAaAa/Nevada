"""
AgentWorker — QThread для выполнения агента без блокировки UI
"""

from PyQt6.QtCore import QThread, pyqtSignal
from agent.loop import AgentLoop


class AgentWorker(QThread):
    """Выполняет агент в отдельном потоке"""
    
    # Сигналы
    token_received = pyqtSignal(str)  # Каждый токен от ответа
    thinking_received = pyqtSignal(str)  # Промежуточное размышление
    tool_result = pyqtSignal(str, str)  # (имя инструмента, реальный вывод)
    response_ready = pyqtSignal(str)  # Полный ответ
    error_occurred = pyqtSignal(str)  # Ошибка
    
    def __init__(self, agent: AgentLoop, user_input: str, confirm_broker=None):
        super().__init__()
        self.agent = agent
        self.user_input = user_input
        # Брокер показывает пользователю диалог подтверждения и блокирует
        # выполнение инструмента до нажатия кнопки
        self.confirm_broker = confirm_broker
    
    def run(self):
        """Основной метод потока"""
        try:
            full_response = ""
            in_thinking = False

            # Итерируем по токенам из streaming; результаты инструментов
            # приходят отдельным сигналом, чтобы UI нарисовал их карточкой
            confirm_callback = None
            if self.confirm_broker is not None:
                confirm_callback = self.confirm_broker.ask

            stream = self.agent.stream(
                self.user_input,
                on_tool_result=lambda name, result: self.tool_result.emit(name, result),
                confirm_callback=confirm_callback,
            )
            for token in stream:
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
                    continue

                # Если внутри thinking, собираем в буфер
                if in_thinking:
                    self.thinking_received.emit(token)
                else:
                    # Основной ответ
                    self.token_received.emit(token)

            # Инструменты выполняет сам AgentLoop (он же возвращает их результат
            # в модель), поэтому здесь ничего вызывать не нужно — иначе инструмент
            # отработал бы дважды.

            # Испускаем финальный ответ
            self.response_ready.emit(full_response)
        
        except Exception as e:
            error_msg = f"❌ Ошибка агента: {str(e)}"
            self.error_occurred.emit(error_msg)
