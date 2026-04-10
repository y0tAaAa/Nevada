# Nevada — Структура проекта

> Автономный desktop-ассистент на PyQt6 + Groq API (Qwen2.5-7B-Instruct)  
> Windows 10/11 · Python 3.11+ · Язык интерфейса: русский

---

## Дерево файлов

```
nevada/
├── main.py
├── build.py
├── config.py
├── .env
├── .env.example
├── requirements.txt
│
├── assets/
│   ├── nevada.ico
│   └── nevada.png
│
├── app/
│   ├── __init__.py
│   ├── nevada_app.py
│   ├── tray.py
│   ├── hotkey.py
│   └── autostart.py
│
├── ui/
│   ├── __init__.py
│   ├── chat_window.py
│   ├── dashboard.py
│   ├── floating.py
│   └── settings_dialog.py
│
├── agent/
│   ├── __init__.py
│   ├── loop.py
│   ├── prompt.py
│   ├── parser.py
│   └── worker.py
│
├── memory/
│   ├── __init__.py
│   └── manager.py
│
├── tools/
│   ├── __init__.py
│   ├── registry.py
│   ├── shell.py
│   ├── file_tool.py
│   └── system_tool.py
│
├── voice/
│   ├── __init__.py
│   └── engine.py
│
└── scheduler/
    ├── __init__.py
    └── planner.py
```

---

## Описание каждого файла

### Корень

| Файл | Что делает |
|------|-----------|
| `main.py` | Точка входа. Создаёт `QApplication`, запускает `NevadaApp`, устанавливает `app.setQuitOnLastWindowClosed(False)` чтобы приложение жило в трее после закрытия окна |
| `build.py` | Скрипт сборки проекта в `Nevada.exe`. Поддерживает два режима: `python build.py` (PyInstaller) и `python build.py --nuitka` (Nuitka). Автоматически создаёт `.env.example` и `README.txt` рядом с `.exe` |
| `config.py` | Dataclass `Config` со всеми настройками: `groq_api_key`, `model`, `system_name = "Nevada"`, `language = "ru"`, `hotkey = "ctrl+shift+space"`, `autostart = True`, `db_path`. Читает значения из `.env` через `python-dotenv` |
| `.env` | Секреты: `GROQ_API_KEY`, `NEVADA_AUTOSTART`, `NEVADA_HOTKEY`. Не коммитить в git |
| `.env.example` | Шаблон `.env` без реальных значений. Коммитить в git |
| `requirements.txt` | Зависимости: `PyQt6`, `openai`, `python-dotenv`, `faster-whisper`, `sounddevice`, `keyboard`, `apscheduler`, `pyinstaller` |

---

### `app/` — ядро приложения

| Файл | Что делает |
|------|-----------|
| `nevada_app.py` | Класс `NevadaApp`. Создаёт все окна (`ChatWindow`, `Dashboard`, `FloatingWidget`), все менеджеры (`TrayManager`, `HotkeyManager`, `Autostart`), агента. Метод `start()` запускает трей, регистрирует горячую клавишу, включает автозапуск если нужно. Метод `_on_hotkey()` показывает/скрывает `FloatingWidget` |
| `tray.py` | Класс `TrayManager`. Иконка в системном трее с контекстным меню: «Открыть чат», «Дашборд», «Настройки», разделитель, «Выход». Одиночный клик по иконке показывает `FloatingWidget`. Двойной клик открывает `ChatWindow` |
| `hotkey.py` | Класс `HotkeyManager(QThread)`. Регистрирует глобальную горячую клавишу через библиотеку `keyboard`. Работает в отдельном потоке чтобы не блокировать UI. При срабатывании испускает сигнал `triggered` который подхватывает `NevadaApp._on_hotkey()` |
| `autostart.py` | Класс `Autostart`. Методы `enable()` и `disable()`. Пишет/удаляет запись в реестре Windows `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` с путём к `Nevada.exe` |

---

### `ui/` — интерфейс

| Файл | Что делает |
|------|-----------|
| `chat_window.py` | Главное окно чата `ChatWindow(QMainWindow)`. Frameless окно с кастомной шапкой (`TitleBar`) — drag, свернуть, развернуть, скрыть в трей. Лента сообщений в `QScrollArea` с пузырями `MessageBubble`. Поле ввода `AutoResizeEdit` (растёт до 140px, Enter отправляет, Shift+Enter — новая строка). Кнопка микрофона (удержание = запись). Анимированный индикатор `TypingDots` пока агент думает. Стриминг ответа токен-за-токеном через `append_text()`. Тёмная тема `#0d0f14`. Все тексты на русском |
| `dashboard.py` | Окно `Dashboard(QMainWindow)`. Три панели: (1) список задач на сегодня от планировщика, (2) история последних 10 диалогов из памяти, (3) статус системы (аптайм Nevada, использование API, количество выполненных команд). Обновляется каждые 30 секунд через `QTimer` |
| `floating.py` | Маленький виджет `FloatingWidget(QWidget)`. Появляется у курсора по горячей клавише. Одна строка ввода + кнопка отправки + кнопка микрофона. После отправки — разворачивается до мини-чата (последние 3 сообщения). Закрывается по `Escape` или клику вне виджета (`focusOutEvent`). Флаг `Qt.WindowType.Tool` — не появляется в taskbar |
| `settings_dialog.py` | Диалог `SettingsDialog(QDialog)`. Вкладки: «Основное» (имя, язык, автозапуск), «API» (поле для ввода Groq API ключа с кнопкой проверки), «Горячие клавиши» (изменить хоткей), «Голос» (выбор микрофона, язык распознавания). Сохраняет в `.env` через `dotenv.set_key()` |

---

### `agent/` — агентный loop

| Файл | Что делает |
|------|-----------|
| `loop.py` | Класс `AgentLoop`. Метод `stream(user_input)` — генератор, отдаёт токены по одному. Метод `run(user_input)` — ждёт полного ответа. Подключается к Groq через `openai.OpenAI(base_url="https://api.groq.com/openai/v1")`. Загружает историю из `MemoryManager`, строит системный промпт, парсит tool calls из ответа через `parser.py`, выполняет инструменты, сохраняет результат в память |
| `prompt.py` | Системный промпт на русском. Содержит: имя (Nevada), роль, список доступных инструментов (подставляется динамически), формат tool call (`<tool>название</tool><input>{json}</input>`), правила безопасности (спрашивать подтверждение перед деструктивными командами), инструкция отвечать на языке пользователя |
| `parser.py` | Функция `parse_tool_call(text)`. Ищет теги `<tool>` и `<input>` в ответе модели, возвращает `(tool_name, params_dict)` или `None` если tool call не найден |
| `worker.py` | Класс `AgentWorker(QThread)`. Принимает `agent` и `user_input`. В методе `run()` итерирует `agent.stream()` и испускает сигналы: `token_received(str)` на каждый токен, `response_ready(str)` по завершении. Используется в `ChatWindow` и `FloatingWidget` чтобы UI не замерзал |

---

### `memory/` — память

| Файл | Что делает |
|------|-----------|
| `manager.py` | Класс `MemoryManager`. SQLite база `nevada.db`. Таблица `messages`: `id, role, content, timestamp`. Методы: `save(user, assistant)` — сохранить пару сообщений, `get_recent(n)` — последние N пар в формате `[{"role": ..., "content": ...}]` для подстановки в API, `get_all()` — вся история для Dashboard, `clear()` — очистить историю |

---

### `tools/` — инструменты агента

| Файл | Что делает |
|------|-----------|
| `registry.py` | Класс `ToolRegistry`. Словарь зарегистрированных инструментов. Метод `register(name, tool)`. Метод `execute(name, params)` — вызывает нужный инструмент, оборачивает результат/ошибку. Метод `describe()` — возвращает строку с описанием всех инструментов для системного промпта |
| `shell.py` | Класс `ShellTool`. Метод `run(command, timeout=30)`. Выполняет bash/cmd команду через `subprocess.run()`. Возвращает `stdout + stderr`. Запрашивает подтверждение если команда содержит `rm`, `del`, `format`, `shutdown` и другие деструктивные паттерны. Описание для агента на русском |
| `file_tool.py` | Класс `FileTool`. Методы: `read(path)`, `write(path, content)`, `append(path, content)`, `list_dir(path)`, `delete(path)` — с подтверждением. Все пути нормализует через `pathlib.Path`. Описание для агента на русском |
| `system_tool.py` | Класс `SystemTool`. Методы: `get_info()` — имя ПК, ОС, CPU/RAM использование, `list_processes()` — список запущенных процессов, `get_time()` — текущее время и дата. Использует `psutil`. Описание для агента на русском |

---

### `voice/` — голосовой ввод

| Файл | Что делает |
|------|-----------|
| `engine.py` | Класс `VoiceEngine`. Метод `listen(seconds=5)` — записывает аудио через `sounddevice`, распознаёт через `faster-whisper` модель `tiny` на CPU. Возвращает строку с текстом. Метод `is_available()` — проверяет наличие микрофона. Язык распознавания берётся из `Config.language` |

---

### `scheduler/` — планировщик

| Файл | Что делает |
|------|-----------|
| `planner.py` | Класс `DayPlanner`. Использует `APScheduler`. Хранит задачи в SQLite таблице `tasks`: `id, title, time, repeat, done`. Методы: `add_task(title, time, repeat)`, `get_today()`, `mark_done(id)`. Напоминания через системный трей (`TrayManager.notify()`). При запуске Nevada — загружает задачи на сегодня и регистрирует их в scheduler |

---

## Стек зависимостей

```txt
# requirements.txt

PyQt6>=6.6.0          # UI фреймворк
openai>=1.0.0         # клиент Groq API (OpenAI-совместимый)
python-dotenv>=1.0.0  # чтение .env
faster-whisper>=1.0.0 # STT голосовой ввод (Whisper tiny на CPU)
sounddevice>=0.4.6    # захват аудио с микрофона
keyboard>=0.13.5      # глобальные горячие клавиши
apscheduler>=3.10.4   # планировщик задач
psutil>=5.9.0         # системная информация (CPU, RAM, процессы)
pyinstaller>=6.0.0    # сборка в .exe
```

---

## Переменные окружения (.env)

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
NEVADA_AUTOSTART=true
NEVADA_HOTKEY=ctrl+shift+space
NEVADA_LANGUAGE=ru
NEVADA_MODEL=qwen-qwq-32b
```

---

## Порядок разработки (фазы)

### Phase 1 — рабочий скелет
`config.py` → `memory/manager.py` → `agent/prompt.py` → `agent/parser.py` → `agent/loop.py` → `agent/worker.py` → `ui/chat_window.py` → `app/tray.py` → `app/nevada_app.py` → `main.py`

### Phase 2 — системные функции  
`tools/registry.py` → `tools/shell.py` → `tools/file_tool.py` → `tools/system_tool.py` → `app/hotkey.py` → `app/autostart.py` → `ui/floating.py`

### Phase 3 — расширенный UI  
`ui/dashboard.py` → `ui/settings_dialog.py` → `scheduler/planner.py`

### Phase 4 — голос  
`voice/engine.py` → интеграция в `chat_window.py` и `floating.py`

### Phase 5 — сборка  
`build.py` → тест `.exe` → финальная упаковка

---

## Промпт для AI агента в IDE

```
Ты опытный Python разработчик. Реализуй проект Nevada — 
автономный desktop-ассистент на PyQt6.

СТЕК:
- Python 3.11
- PyQt6 для UI (frameless окна, тёмная тема)
- Groq API через openai-клиент (base_url = https://api.groq.com/openai/v1)
- Модель: qwen-qwq-32b (или llama-3.3-70b как fallback)
- SQLite для памяти (без ORM, чистый sqlite3)
- faster-whisper tiny для голоса (CPU)
- keyboard для глобальных хоткеев
- APScheduler для планировщика
- python-dotenv для конфига

ПРАВИЛА КОДА:
1. Весь текст интерфейса и комментарии на русском языке
2. Каждый класс в отдельном файле согласно структуре
3. Агент работает в QThread (worker.py) — UI никогда не замерзает
4. Все инструменты агента (tools/) регистрируются через ToolRegistry
5. Tool calls агента в формате XML: <tool>имя</tool><input>{"param": "val"}</input>
6. Деструктивные shell-команды (rm, del, format, shutdown) требуют подтверждения
7. API ключ только из .env, никогда не хардкодить
8. Приложение живёт в трее: app.setQuitOnLastWindowClosed(False)
9. Стриминг ответов токен-за-токеном через сигнал token_received(str)
10. Тёмная тема: фон окна #0d0f14, акцент #3b82f6

ЦВЕТОВАЯ ПАЛИТРА:
BG_WINDOW    = "#0d0f14"
BG_INPUT     = "#1a1d26"  
BG_MSG_USER  = "#2563eb"
BG_MSG_NEV   = "#1a1d26"
TEXT_PRIMARY = "#e8eaf0"
ACCENT       = "#3b82f6"
BORDER       = "#1f2335"

СИСТЕМНЫЙ ПРОМПТ АГЕНТА (agent/prompt.py):
Ты Nevada — автономный ассистент управления компьютером.
Отвечай на русском языке если пользователь пишет по-русски.
Думай пошагово. Перед деструктивными действиями спрашивай подтверждение.
Доступные инструменты: {tools}
Формат вызова инструмента:
<tool>название_инструмента</tool>
<input>{"параметр": "значение"}</input>

СТРУКТУРА ПРОЕКТА: [вставь сюда содержимое NEVADA_PROJECT.md]

Реализуй файлы в порядке Phase 1 → Phase 2 → Phase 3 → Phase 4.
Начни с Phase 1. После каждого файла жди подтверждения перед следующим.
```

---

*Nevada Project · Phase 1-5 · PyQt6 + Groq API*
