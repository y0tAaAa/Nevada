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
            "Выполняет shell/cmd команду и возвращает результат. "
            "Требует подтверждение для деструктивных операций."
        )
    
    def execute(self, command: str, timeout: int = 30) -> str:
        """
        Выполняет команду в shell.
        
        Args:
            command: Команда для выполнения
            timeout: Максимальное время выполнения в секундах
        
        Returns:
            Stdout + stderr результат
        """
        # Проверяем на деструктивные команды
        if self._is_destructive(command):
            return (
                "⚠️  Эта команда может быть опасной и требует подтверждения: "
                f"'{command}'. Пожалуйста, используй инструмент для подтверждения."
            )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
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
