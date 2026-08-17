"""
ShellTool — выполнение shell/cmd команд
"""

import subprocess
import re
from typing import Optional


class ShellTool:
    """Выполняет системные команды"""
    
    # Паттерны деструктивных команд
    DESTRUCTIVE_PATTERNS = [
        r'\brm\b',           # rm (Unix)
        r'\bdel\b',          # del (Windows)
        r'\bformat\b',       # format диска
        r'\brmdir\b',        # rmdir
        r'\brd\b',           # rd (Windows)
        r'\bclear\b',        # clear
        r'\bdiskpart\b',     # diskpart
        r'\bshutdown\b',     # shutdown
        r'\brestart\b',      # reboot/restart
        r'\bkill\b',         # kill процесс
        r'\btaskkill\b',     # taskkill (Windows)
    ]
    
    def __init__(self):
        self.description = (
            "Выполняет команду Windows и возвращает её реальный вывод.\n"
            "      Параметры: command (строка), timeout (сек, по умолчанию 30), confirm.\n"
            "      ВАЖНО: wmic в этой версии Windows УДАЛЁН — используй PowerShell.\n"
            "      Видеокарта: <input>{\"command\": \"powershell -NoProfile -Command \\\"Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name\\\"\"}</input>\n"
            "      Диски:      powershell -NoProfile -Command \"Get-CimInstance Win32_DiskDrive | Select-Object Model,Size\"\n"
            "      Сеть:       ipconfig\n"
            "      Годится для данных, которых нет в других инструментах.\n"
            "      Опасные команды (del, format, shutdown…) требуют повторного вызова с \"confirm\": true."
        )
    
    def execute(self, command: str, timeout: int = 30, confirm: bool = False) -> str:
        """
        Выполняет команду в shell.

        Args:
            command: Команда для выполнения
            timeout: Максимальное время выполнения в секундах
            confirm: Подтверждение выполнения потенциально опасной команды

        Returns:
            Stdout + stderr результат
        """
        # Проверяем на деструктивные команды
        if self._is_destructive(command) and not confirm:
            return (
                "⚠️  Эта команда потенциально опасна и требует подтверждения пользователя: "
                f"'{command}'. Спроси пользователя явно и, если он согласен, вызови "
                "этот же инструмент повторно с параметром \"confirm\": true."
            )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                # Консоль Windows отдаёт вывод в OEM-кодировке (на русской системе cp866).
                # Без этого русские сообщения превращаются в «­Ґ пў«пҐвбп ў­гваҐ­­Ґ©».
                encoding="oem",
                errors="replace",
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]: {result.stderr}"
            
            if result.returncode != 0:
                output += f"\n[Return Code: {result.returncode}]"
            
            return output if output else "✅ Команда выполнена без вывода"
        
        except subprocess.TimeoutExpired:
            return f"❌ Команда превысила лимит времени ({timeout}s)"
        except Exception as e:
            return f"❌ Ошибка выполнения команды: {str(e)}"
    
    def _is_destructive(self, command: str) -> bool:
        """Проверяет, содержит ли команда потенциально опасные операции"""
        command_lower = command.lower()
        
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command_lower):
                return True
        
        return False
