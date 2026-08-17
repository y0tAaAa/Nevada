"""
SystemTool — получение информации о системе
"""

import subprocess

import psutil
import platform
from datetime import datetime


class SystemTool:
    """Инструмент для получения системной информации"""
    
    def __init__(self):
        self.description = (
            "Информация о системе. Параметр action — ТОЛЬКО одно из:\n"
            "      • get_info — имя ПК, ОС, ядра и загрузка CPU, использование RAM, аптайм\n"
            "      • get_hardware — комплектующие: процессор, видеокарты, модули ОЗУ,\n"
            "        материнская плата, накопители (для вопросов «какое у меня железо»)\n"
            "      • list_processes — топ-10 процессов по памяти\n"
            "      • get_time — текущие дата и время\n"
            "      • get_disk — разделы дисков: всего / занято / свободно\n"
            "      Пример: <input>{\"action\": \"get_hardware\"}</input>\n"
            "      Температуру и напряжение этот инструмент НЕ даёт."
        )
    
    def execute(self, action: str = "get_info") -> str:
        """
        Выполняет операцию получения системной информации.
        
        Args:
            action: 'get_info', 'list_processes', 'get_time', 'get_disk'
        
        Returns:
            Результат в строковом формате
        """
        try:
            if action == "get_info":
                return self._get_info()
            elif action == "get_hardware":
                return self._get_hardware()
            elif action == "list_processes":
                return self._list_processes()
            elif action == "get_time":
                return self._get_time()
            elif action == "get_disk":
                return self._get_disk()
            else:
                return f"❌ Неизвестное действие: {action}"
        except Exception as e:
            return f"❌ Ошибка получения информации: {str(e)}"
    
    def _get_info(self) -> str:
        """Получает основную информацию о системе"""
        try:
            # Имя ПК
            computer_name = platform.node()
            
            # ОС
            os_name = platform.system()
            os_version = platform.release()
            
            # CPU
            cpu_count = psutil.cpu_count()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # RAM
            memory = psutil.virtual_memory()
            ram_used = memory.used / (1024**3)  # GB
            ram_total = memory.total / (1024**3)  # GB
            ram_percent = memory.percent
            
            # Аптайм
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = f"{uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м"
            
            info = f"""
📊 ИНФОРМАЦИЯ О СИСТЕМЕ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  Компьютер: {computer_name}
🔧 ОС: {os_name} {os_version}
⚙️  CPU: {cpu_count} ядер ({cpu_percent}%)
💾 RAM: {ram_used:.1f} GB / {ram_total:.1f} GB ({ram_percent}%)
⏱️  Аптайм: {uptime_str}
            """.strip()
            
            return info
        
        except Exception as e:
            return f"❌ Ошибка получения системной информации: {str(e)}"
    
    def _run_powershell(self, script: str, timeout: int = 25) -> str:
        """Выполняет PowerShell-скрипт и возвращает вывод (в OEM-кодировке консоли)"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="oem",
            errors="replace",
            timeout=timeout,
        )
        return (result.stdout or "").strip()

    def _get_hardware(self) -> str:
        """
        Реальные комплектующие через CIM (wmic в Windows 11 24H2 удалён).
        Каждый блок запрашивается отдельно, чтобы сбой одного не убивал весь ответ.
        """
        queries = [
            ("Процессор", "Get-CimInstance Win32_Processor | "
                          "ForEach-Object { \"$($_.Name) | ядер: $($_.NumberOfCores) | \" + "
                          "\"потоков: $($_.NumberOfLogicalProcessors) | $([math]::Round($_.MaxClockSpeed/1000,2)) ГГц\" }"),
            ("Видеокарты", "Get-CimInstance Win32_VideoController | "
                           "ForEach-Object { \"$($_.Name) | $([math]::Round($_.AdapterRAM/1GB,1)) ГБ\" }"),
            ("Оперативная память", "Get-CimInstance Win32_PhysicalMemory | "
                                   "ForEach-Object { \"$([math]::Round($_.Capacity/1GB,0)) ГБ | \" + "
                                   "\"$($_.Speed) МГц | $($_.Manufacturer)\" }"),
            ("Материнская плата", "Get-CimInstance Win32_BaseBoard | "
                                  "ForEach-Object { \"$($_.Manufacturer) $($_.Product)\" }"),
            ("Накопители", "Get-CimInstance Win32_DiskDrive | "
                           "ForEach-Object { \"$($_.Model) | $([math]::Round($_.Size/1GB,0)) ГБ\" }"),
        ]

        lines = ["КОМПЛЕКТУЮЩИЕ (данные системы):"]
        for title, script in queries:
            try:
                output = self._run_powershell(script)
            except subprocess.TimeoutExpired:
                output = ""
                lines.append(f"{title}: превышено время ожидания")
                continue
            except Exception as e:
                lines.append(f"{title}: ошибка запроса ({e})")
                continue

            if output:
                for i, entry in enumerate(output.splitlines()):
                    entry = entry.strip()
                    if entry:
                        lines.append(f"{title if i == 0 else ' ' * len(title)}: {entry}")
            else:
                lines.append(f"{title}: данные недоступны")

        return "\n".join(lines)

    def _list_processes(self) -> str:
        """Список запущенных процессов"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    processes.append({
                        'name': proc.info['name'],
                        'pid': proc.info['pid'],
                        'memory': proc.info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Сортируем по использованию памяти
            processes.sort(key=lambda x: x['memory'] or 0, reverse=True)
            
            lines = ["📋 ТОП 10 ПРОЦЕССОВ ПО ПАМЯТИ:"]
            for proc in processes[:10]:
                mem = proc['memory'] or 0
                lines.append(f"  {proc['name']:30} | PID: {proc['pid']:6} | Память: {mem:6.1f}%")
            
            return "\n".join(lines)
        
        except Exception as e:
            return f"❌ Ошибка получения списка процессов: {str(e)}"
    
    def _get_time(self) -> str:
        """Текущие дата и время"""
        now = datetime.now()
        return f"🕐 {now.strftime('%d.%m.%Y %H:%M:%S')} (по местному времени)"
    
    def _get_disk(self) -> str:
        """Информация о диске"""
        try:
            info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    total = usage.total / (1024**3)
                    used = usage.used / (1024**3)
                    free = usage.free / (1024**3)
                    percent = usage.percent
                    
                    info.append(
                        f"{partition.device:15} | Всего: {total:7.1f}GB | Использовано: {used:7.1f}GB | "
                        f"Свободно: {free:7.1f}GB | {percent:5.1f}%"
                    )
                except PermissionError:
                    pass
            
            if info:
                return "💿 ИНФОРМАЦИЯ О ДИСКАХ:\n" + "\n".join(info)
            return "❌ Не удаётся получить информацию о дисках"
        
        except Exception as e:
            return f"❌ Ошибка получения информации о дисках: {str(e)}"
