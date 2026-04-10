"""
MemoryManager — SQLite хранилище истории диалогов
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class MemoryManager:
    """Управляет историей сообщений в SQLite"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Инициализирует базу данных и таблицы"""
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()
        
        # Таблица сообщений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def save(self, user_msg: str, assistant_msg: str) -> None:
        """Сохраняет пару сообщений (пользователь + ассистент)"""
        cursor = self.conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            ("user", user_msg)
        )
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            ("assistant", assistant_msg)
        )
        
        self.conn.commit()
    
    def get_recent(self, n: int = 10) -> List[Dict[str, str]]:
        """
        Возвращает последние N пар диалогов в формате API.
        Формат: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            "SELECT role, content FROM messages ORDER BY timestamp DESC LIMIT ?",
            (n * 2,)  # N пар = N*2 сообщений
        )
        
        rows = cursor.fetchall()
        # Разворачиваем в обратном порядке (старые сообщения первыми)
        messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
        
        return messages
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Возвращает всю историю для Dashboard.
        Включает timestamp для сортировки по времени.
        """
        cursor = self.conn.cursor()
        
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
    
    def clear(self) -> None:
        """Очищает всю историю"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages")
        self.conn.commit()
    
    def close(self) -> None:
        """Закрывает соединение с БД"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
