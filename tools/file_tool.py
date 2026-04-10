"""
FileTool — работа с файлами и директориями
"""

from pathlib import Path
from typing import Optional, List


class FileTool:
    """Инструмент для работы с файловой системой"""
    
    def __init__(self):
        self.description = (
            "Работа с файлами: чтение, запись, удаление, список файлов в директории. "
            "Требует подтверждение перед удалением."
        )
        self.protected_dirs = [
            Path("C:\\Windows"),
            Path("C:\\Program Files"),
            Path("C:\\Program Files (x86)"),
            Path("C:\\System32"),
        ]
    
    def execute(self, action: str, path: str, content: Optional[str] = None) -> str:
        """
        Выполняет операцию с файлом.
        
        Args:
            action: 'read', 'write', 'append', 'list_dir', 'delete', 'exists'
            path: Путь к файлу или директории
            content: Содержимое для write/append
        
        Returns:
            Результат операции
        """
        try:
            path_obj = Path(path).resolve()
            
            # Проверяем защищённые директории
            if self._is_protected(path_obj):
                return f"❌ Доступ запрещён: {path} — защищённая директория"
            
            if action == "read":
                return self._read(path_obj)
            elif action == "write":
                return self._write(path_obj, content)
            elif action == "append":
                return self._append(path_obj, content)
            elif action == "list_dir":
                return self._list_dir(path_obj)
            elif action == "delete":
                return self._delete(path_obj)
            elif action == "exists":
                return "✅ Файл существует" if path_obj.exists() else "❌ Файл не найден"
            else:
                return f"❌ Неизвестное действие: {action}"
        
        except Exception as e:
            return f"❌ Ошибка операции с файлом: {str(e)}"
    
    def _read(self, path: Path) -> str:
        """Читает содержимое файла"""
        if not path.exists():
            return f"❌ Файл не найден: {path}"
        
        if not path.is_file():
            return f"❌ Это не файл: {path}"
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            return f"❌ Не удаётся прочитать файл (бинарный формат?): {path}"
    
    def _write(self, path: Path, content: str) -> str:
        """Записывает содержимое в файл (перезаписывает)"""
        if content is None:
            return "❌ Не указано содержимое для записи"
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ Файл записан: {path}"
        except Exception as e:
            return f"❌ Ошибка записи: {str(e)}"
    
    def _append(self, path: Path, content: str) -> str:
        """Добавляет содержимое в конец файла"""
        if content is None:
            return "❌ Не указано содержимое для добавления"
        
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)
            return f"✅ Содержимое добавлено в {path}"
        except Exception as e:
            return f"❌ Ошибка добавления: {str(e)}"
    
    def _list_dir(self, path: Path) -> str:
        """Список файлов в директории"""
        if not path.exists():
            return f"❌ Директория не найдена: {path}"
        
        if not path.is_dir():
            return f"❌ Это не директория: {path}"
        
        try:
            files = []
            for item in sorted(path.iterdir()):
                size = ""
                if item.is_file():
                    size = f" ({item.stat().st_size} б)"
                name = "📁 " if item.is_dir() else "📄 "
                files.append(f"{name}{item.name}{size}")
            
            return "\n".join(files) if files else "📭 Директория пуста"
        except Exception as e:
            return f"❌ Ошибка при чтении директории: {str(e)}"
    
    def _delete(self, path: Path) -> str:
        """Удаляет файл или директорию"""
        if not path.exists():
            return f"❌ Файл не найден: {path}"
        
        # Требуем подтверждение для delete
        return f"⚠️  Требуется подтверждение для удаления: {path}"
    
    def _is_protected(self, path: Path) -> bool:
        """Проверяет, находится ли путь в защищённой директории"""
        for protected in self.protected_dirs:
            try:
                path.relative_to(protected)
                return True
            except ValueError:
                continue
        return False
