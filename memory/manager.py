"""
MemoryManager — SQLite хранилище истории диалогов (потокобезопасно)
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import threading


class MemoryManager:
    """Управляет историей сообщений в SQLite (работает в разных потоках)"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.local = threading.local()  # Потокобезопасное хранилище соединений
        self._init_db()
    
    def _get_connection(self):
        """Получает или создаёт соединение для текущего потока"""
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            # check_same_thread=False позволяет использовать одну БД из разных потоков
            self.local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10.0)
        return self.local.conn
    
    def _init_db(self):
        """Инициализирует базу данных и таблицы"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблица сообщений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
    
    def save(self, user_msg: str, assistant_msg: str) -> None:
        """Сохраняет пару сообщений (пользователь + ассистент)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO messages (role, content) VALUES (?, ?)",
                ("user", user_msg)
            )
            cursor.execute(
                "INSERT INTO messages (role, content) VALUES (?, ?)",
                ("assistant", assistant_msg)
            )
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка сохранения сообщений: {e}")
    
    def get_recent(self, n: int = 10) -> List[Dict[str, str]]:
        """
        Возвращает последние N пар диалогов в формате API.
        Формат: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT role, content FROM messages ORDER BY timestamp DESC LIMIT ?",
                (n * 2,)  # N пар = N*2 сообщений
            )
            
            rows = cursor.fetchall()
            # Разворачиваем в обратном порядке (старые сообщения первыми)
            messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
            
            return messages
        except Exception as e:
            print(f"❌ Ошибка получения истории: {e}")
            return []
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Возвращает всю историю для Dashboard.
        Включает timestamp для сортировки по времени.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT role, content, timestamp FROM messages ORDER BY timestamp ASC"
            )
            
            rows = cursor.fetchall()
            messages = [
                {
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2]
                }
                for row in rows
            ]
            
            return messages
        except Exception as e:
            print(f"❌ Ошибка получения полной истории: {e}")
            return []
    
    def clear(self) -> None:
        """Очищает всю историю"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages")
            conn.commit()
        except Exception as e:
            print(f"❌ Ошибка очистки истории: {e}")
    
    def close(self) -> None:
        """Закрывает соединение с БД"""
        if hasattr(self.local, 'conn') and self.local.conn:
            try:
                self.local.conn.close()
            except:
                pass
            self.local.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

