"""
Build скрипт — сборка Nevada.exe через PyInstaller или Nuitka
Использование:
  python build.py              # PyInstaller
  python build.py --nuitka     # Nuitka
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv


def build_with_pyinstaller():
    """Сборка через PyInstaller"""
    print("[BUILD] Сборка Nevada.exe через PyInstaller...")
    
    try:
        # Проверяем PyInstaller
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], check=True, capture_output=True)
    except:
        print("[ERROR] PyInstaller не установлен. Установите: pip install pyinstaller")
        return False
    
    try:
        assets_path = Path(__file__).parent / "assets"
        icon_path = assets_path / "nevada.ico"
        icon_arg = f"--icon={icon_path}" if icon_path.exists() else ""
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", "Nevada",
            "--distpath", "./dist",
            "--workpath", "./build",
            "--specpath", "./build",
            "--hidden-import=PyQt6",
            "--hidden-import=faster_whisper",
            "--hidden-import=sounddevice",
            "--hidden-import=keyboard",
            "--hidden-import=psutil",
            "--hidden-import=apscheduler",
        ]
        
        if icon_arg:
            cmd.append(icon_arg)
        
        cmd.append("main.py")
        
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("[OK] Сборка завершена!")
            exe_path = Path("dist") / "Nevada.exe"
            
            if exe_path.exists():
                print(f"[PACKAGE] Nevada.exe создана: {exe_path}")
                _create_readme_and_env(exe_path.parent)
                return True
    
    except Exception as e:
        print(f"[ERROR] Ошибка сборки: {e}")
    
    return False


def build_with_nuitka():
    """Сборка через Nuitka"""
    print("[BUILD] Сборка Nevada.exe через Nuitka...")
    
    try:
        # Проверяем Nuitka
        subprocess.run(["python", "-m", "nuitka", "--version"], check=True, capture_output=True)
    except:
        print("[ERROR] Nuitka не установлена. Установите: pip install nuitka")
        return False
    
    try:
        assets_path = Path(__file__).parent / "assets"
        icon_path = assets_path / "nevada.ico"
        icon_arg = f'--windows-icon-from-ico="{icon_path}"' if icon_path.exists() else ""
        
        cmd = f"""
python -m nuitka \
    --onefile \
    --windows-disable-console \
    --follow-imports \
    {icon_arg} \
    --output-dir=./dist \
    main.py
        """.replace("\n", " ")
        
        result = subprocess.run(cmd, shell=True)
        
        if result.returncode == 0:
            print("[OK] Сборка завершена!")
            exe_path = Path("dist") / "main.exe"
            
            if exe_path.exists():
                # Переименовываем в Nevada.exe
                nevada_exe = exe_path.parent / "Nevada.exe"
                exe_path.rename(nevada_exe)
                print(f"[PACKAGE] Nevada.exe создана: {nevada_exe}")
                _create_readme_and_env(nevada_exe.parent)
                return True
    
    except Exception as e:
        print(f"❌ Ошибка сборки: {e}")
    
    return False


def _create_readme_and_env(dist_path: Path):
    """Создаёт README.txt и .env.example рядом с exe"""
    
    # README.txt
    readme_content = """Nevada — Автономный desktop-ассистент
=====================================

Для запуска приложения:
1. Создайте файл .env в той же папке
2. Скопируйте содержимое из .env.example
3. Добавьте ключ API одного из провайдеров:
   • Groq (по умолчанию): https://console.groq.com/keys
     GROQ_API_KEY=gsk_...
   • NVIDIA NIM: https://build.nvidia.com
     NEVADA_PROVIDER=nvidia
     NVIDIA_API_KEY=nvapi-...
     NEVADA_MODEL=meta/llama-3.3-70b-instruct
4. Запустите Nevada.exe

Горячая клавиша по умолчанию: Ctrl+Shift+Space
Чтобы изменить, отредактируйте NEVADA_HOTKEY в .env

Требования:
- Windows 10/11
- Интернет для API
- Микрофон (опционально, для голоса)

Поддержка: https://github.com
"""
    
    readme_path = dist_path / "README.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    # .env.example — берём актуальный шаблон из проекта, чтобы он не устаревал
    project_example = Path(__file__).parent / ".env.example"
    env_path = dist_path / ".env.example"
    if project_example.exists():
        shutil.copy(project_example, env_path)
    else:
        env_path.write_text(
            "NEVADA_PROVIDER=groq\n"
            "GROQ_API_KEY=gsk_your_api_key_here\n"
            "NEVADA_MODEL=llama-3.3-70b-versatile\n"
            "NEVADA_AUTOSTART=true\n"
            "NEVADA_HOTKEY=ctrl+shift+space\n"
            "NEVADA_LANGUAGE=ru\n",
            encoding="utf-8",
        )

    # ВАЖНО: рабочий .env с настоящим API-ключом в сборку НЕ копируем.
    # Иначе ключ уедет вместе с папкой dist при любой передаче сборки.
    print(f"[INFO] Созданы README.txt и .env.example в {dist_path}")
    print("[INFO] Рабочий .env намеренно не скопирован — ключ не должен попасть в сборку")


def clean():
    """Очищает временные файлы сборки"""
    print("🧹 Очистка временных файлов...")
    
    dirs_to_remove = ["build", "dist"]
    files_to_remove = ["main.spec", "Nevada.spec"]
    
    for dir_name in dirs_to_remove:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  Удалили {dir_name}/")
    
    for file_name in files_to_remove:
        if Path(file_name).exists():
            Path(file_name).unlink()
            print(f"  Удалили {file_name}")


def main():
    """Главная функция"""
    
    # Проверяем что мы в папке проекта
    if not Path("main.py").exists():
        print("[ERROR] Ошибка: main.py не найден")
        print("   Убедитесь, что вы в корневой папке Nevada")
        return
    
    print("Nevada — Builder")
    print("=" * 40)
    
    # Парсим аргументы
    use_nuitka = "--nuitka" in sys.argv
    do_clean = "--clean" in sys.argv
    
    if do_clean:
        clean()
        return
    
    # Выбираем метод сборки
    if use_nuitka:
        success = build_with_nuitka()
    else:
        success = build_with_pyinstaller()
    
    if success:
        print("\n[OK] Nevada собрана успешно!")
        print("[PACKAGE] Найти Nevada.exe в папке dist/")
        
        # Создаём ярлык на рабочем столе
        if sys.platform == "win32":
            create_desktop_shortcut()
    else:
        print("\n[ERROR] Ошибка при сборке")


def create_desktop_shortcut():
    """Создаёт ярлык Nevada.exe на рабочем столе"""
    
    try:
        exe_path = Path("dist") / "Nevada.exe"
        
        if not exe_path.exists():
            print("[WARNING] Nevada.exe не найден")
            return
        
        desktop_path = Path.home() / "Desktop"
        shortcut_path = desktop_path / "Nevada.lnk"
        
        # Используем Windows API для создания ярлычка
        try:
            from win32com.client import Dispatch
            
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.TargetPath = str(exe_path.resolve())
            shortcut.WorkingDirectory = str(exe_path.parent)
            shortcut.Description = "Autonomous Desktop Assistant"
            shortcut.IconLocation = str(exe_path.resolve())
            shortcut.save()
            
            print(f"🔗 Ярлык создан на рабочем столе: {shortcut_path}")
            
        except ImportError:
            # Альтернативный метод через простой текстовый файл
            print("⚠️  pywin32 не установлен, создаю ярлычок вручную...")
            print(f"   Для создания ярлычка:")
            print(f"   1. Перейдите в папку: {exe_path.parent}")
            print(f"   2. Перетащите Nevada.exe на рабочий стол")
            print(f"   3. Выберите 'Создать ярлычок'")
    
    except Exception as e:
        print(f"⚠️  Ошибка при создании ярлычка: {e}")


if __name__ == "__main__":
    main()
