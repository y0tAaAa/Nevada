"""
DayPlanner — планировщик задач на день
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.qt import QtScheduler
from typing import List, Dict, Any, Optional


class DayPlanner:
    """Планировщик задач с уведомлениями"""
    
    def __init__(self, db_path: Path, tray_manager=None):
        self.db_path = db_path
        self.tray_manager = tray_manager
        self.conn = None
        self.scheduler = QtScheduler()
        self._init_db()
        self._load_today_tasks()
    
    def _init_db(self):
        """Инициализирует БД для задач"""
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                time TEXT NOT NULL,
                repeat TEXT DEFAULT 'once',
                done BOOLEAN DEFAULT 0,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_scheduled DATE
            )
        """)
        
        self.conn.commit()
    
    def add_task(self, title: str, time: str, repeat: str = "once") -> bool:
        """
        Добавляет новую задачу.
        
        Args:
            title: Название задачи
            time: Время в формате HH:MM
            repeat: 'once', 'daily', 'weekly'
        
        Returns:
            True если успешно
        """
        try:
            cursor = self.conn.cursor()
            today = datetime.now().date()
            
            cursor.execute("""
                INSERT INTO tasks (title, time, repeat, date_scheduled)
                VALUES (?, ?, ?, ?)
            """, (title, time, repeat, today))
            
            self.conn.commit()
            
            # Регистрируем в scheduler
            self._schedule_task(title, time)
            
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления задачи: {e}")
            return False
    
    def get_today(self) -> List[Dict[str, Any]]:
        """Получает все задачи на сегодня"""
        try:
            cursor = self.conn.cursor()
            today = datetime.now().date()
            
            cursor.execute("""
                SELECT id, title, time, done FROM tasks
                WHERE date_scheduled = ? AND done = 0
                ORDER BY time ASC
            """, (today,))
            
            rows = cursor.fetchall()
            tasks = [
                {
                    "id": row[0],
                    "title": row[1],
                    "time": row[2],
                    "done": bool(row[3])
                }
                for row in rows
            ]
            
            return tasks
        except Exception as e:
            print(f"❌ Ошибка получения задач: {e}")
            return []
    
    def mark_done(self, task_id: int) -> bool:
        """Отмечает задачу как выполненную"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка отметки задачи: {e}")
            return False
    
    def _schedule_task(self, title: str, time_str: str):
        """Регистрирует задачу в scheduler для уведомления"""
        try:
            hour, minute = map(int, time_str.split(':'))
            
            def notify():
                if self.tray_manager:
                    self.tray_manager.show_notification("📋 Напоминание:", title, duration=10000)
                else:
                    print(f"🔔 Напоминание: {title}")
            
            self.scheduler.add_job(
                notify,
                'cron',
                hour=hour,
                minute=minute,
                id=f"task_{title}_{time_str}"
            )
        except Exception as e:
            print(f"❌ Ошибка планирования: {e}")
    
    def _load_today_tasks(self):
        """Загружает и регистрирует все задачи на сегодня"""
        tasks = self.get_today()
        for task in tasks:
            self._schedule_task(task['title'], task['time'])
    
    def start(self):
        """Запускает планировщик"""
        if not self.scheduler.running:
            self.scheduler.start()
            print("✅ Планировщик запущен")
    
    def stop(self):
        """Останавливает планировщик"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("✅ Планировщик остановлен")
    
    def close(self):
        """Закрывает БД и планировщик"""
        self.stop()
        if self.conn:
            self.conn.close()
