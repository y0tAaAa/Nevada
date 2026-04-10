"""
HotkeyManager — регистрация глобальной горячей клавиши
"""

from PyQt6.QtCore import QThread, pyqtSignal
import keyboard


class HotkeyManager(QThread):
    """Менеджер горячей клавиши (работает в отдельном потоке)"""
    
    triggered = pyqtSignal()  # Сигнал при срабатывании хоткея
    
    def __init__(self, hotkey: str = "ctrl+shift+space"):
        super().__init__()
        self.hotkey = hotkey
        self.is_running = False
    
    def run(self):
        """Основной цикл потока для ловли хоткейка"""
        self.is_running = True
        try:
            print(f"⌨️  Горячая клавиша зарегистрирована: {self.hotkey}")
            keyboard.add_hotkey(self.hotkey, self._on_hotkey_pressed)
            
            # Держим поток живым
            while self.is_running:
                self.msleep(100)
        
        except Exception as e:
            print(f"❌ Ошибка регистрации хоткея: {str(e)}")
    
    def _on_hotkey_pressed(self):
        """Вызывается при нажатии на хоткей"""
        self.triggered.emit()
    
    def stop(self):
        """Останавливает горячую клавишу"""
        self.is_running = False
        try:
            keyboard.remove_hotkey(self.hotkey)
        except:
            pass
