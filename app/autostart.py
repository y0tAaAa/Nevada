"""
Autostart — управление автозапуском приложения через реестр Windows
"""

import winreg
from pathlib import Path


class Autostart:
    """Управляет автозапуском Nevada через реестр Windows"""
    
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "Nevada"
    
    @staticmethod
    def enable(exe_path: str = None) -> bool:
        """
        Включает автозапуск приложения.
        
        Args:
            exe_path: Полный путь к Nevada.exe (если None, используется текущий exe)
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if exe_path is None:
                # Пытаемся найти Nevada.exe в текущей директории
                exe_path = str(Path(__file__).parent.parent / "Nevada.exe")
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Autostart.REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, Autostart.APP_NAME, 0, winreg.REG_SZ, exe_path)
            
            print(f"✅ Автозапуск включен: {exe_path}")
            return True
        
        except Exception as e:
            print(f"❌ Ошибка при включении автозапуска: {str(e)}")
            return False
    
    @staticmethod
    def disable() -> bool:
        """
        Отключает автозапуск приложения.
        
        Returns:
            True если успешно, False если ошибка или не найдено
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Autostart.REGISTRY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, Autostart.APP_NAME)
            
            print(f"✅ Автозапуск отключен")
            return True
        
        except FileNotFoundError:
            print(f"ℹ️  Nevada не был установлен на автозапуск")
            return False
        except Exception as e:
            print(f"❌ Ошибка при отключении автозапуска: {str(e)}")
            return False
    
    @staticmethod
    def is_enabled() -> bool:
        """
        Проверяет, включен ли автозапуск.
        
        Returns:
            True если автозапуск включен, False иначе
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, Autostart.REGISTRY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, Autostart.APP_NAME)
                return bool(value)
        
        except FileNotFoundError:
            return False
        except Exception:
            return False
