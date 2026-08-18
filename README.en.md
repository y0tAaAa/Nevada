# Nevada

[Русский](README.md) · **English**

An autonomous desktop assistant for Windows. Lives in the system tray, understands
voice, controls applications, and answers **from your computer's real data** —
not from guesswork.

> PyQt6 · Python 3.11+ · Windows 10/11 · any OpenAI-compatible model provider

The interface and built-in skills are in Russian — this is a Russian-language
assistant. This file documents the project in English.

---

## What it does

**An agent with real tools.** Nevada doesn't just chat: it queries the system,
launches programs and reads web pages — then answers from what it actually got back.

| Tool | What it does |
|------|-------------|
| `system` | Hardware (CPU, GPUs, RAM modules, motherboard, drives), load, disks, processes, time |
| `app` | List open windows, launch programs, type into windows, send hotkeys, search in browser |
| `research` | Web search that **actually reads** pages and cites sources |
| `file` | Read, write, list, delete files |
| `shell` | Windows commands |
| `skill` | Ready-made scenarios from the `skills/` folder |

**Skills are plain markdown files.** Drop a file into `skills/` and Nevada starts
using it — no code changes, no restart. Included: morning digest, note to Notepad,
PC check-up, web search, research a topic.

**Voice.** Local speech recognition (faster-whisper) and offline speech synthesis
(pyttsx3). A separate **Jarvis HUD** mode: a ring near your cursor — click, speak,
get a spoken answer.

**Interface.** Frameless window with sidebar navigation, dark indigo theme, and a
"Commands" page listing what Nevada can do with clickable examples.

---

## The core design goal: why it doesn't make things up

An assistant that invents your computer's specs is worse than useless. Nevada has
four independent defenses against this — each closes a different way of lying, and
every one of them exists because of an actual incident.

1. **A real agent loop.** Model → tool call → execution → **the real output goes
   back into the model** → answer grounded in facts. Previously the result was just
   appended to the end of the text: the model never saw it and invented
   plausible-looking numbers instead.

2. **A stop sequence on the tool call.** Generation halts right after `<input>…`,
   so fabricating a "result" in the same reply is physically impossible.

3. **Clean memory.** Only the model's own prose is stored. When tool-output blocks
   ended up in history, the model treated them as its own words and started forging
   such blocks on its own.

4. **A fabrication guard.** If a reply contains concrete metrics (time, uptime,
   CPU/RAM load, hardware) while no tool was called, the loop stops the model, tells
   the user, and forces it to verify the data.

**Confirmation of dangerous actions is real.** The gate lives in the agent loop, not
inside the tools: the model can set `"confirm": true` itself, but execution still
waits for your click in a dialog. Gated actions: typing into windows, hotkeys,
writing and deleting files, destructive shell commands.

**Typing into other windows is verified.** Windows won't hand focus to a background
process, so keystrokes used to silently land in whatever app was active. Focus is
now checked via `GetForegroundWindow`, and if the target window didn't activate,
no keystrokes are sent at all.

---

## Installation

```bash
git clone https://github.com/y0tAaAa/Nevada.git
cd Nevada
pip install -r requirements.txt
```

## Configuration

Copy the template and add your key:

```bash
copy .env.example .env
```

Switching providers is a one-line change — no code edits.

**Groq** — [console.groq.com/keys](https://console.groq.com/keys):

```env
NEVADA_PROVIDER=groq
GROQ_API_KEY=gsk_your_key
NEVADA_MODEL=llama-3.3-70b-versatile
```

**NVIDIA NIM** — [build.nvidia.com](https://build.nvidia.com), free credits available:

```env
NEVADA_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your_key
NEVADA_MODEL=meta/llama-3.3-70b-instruct
```

**Your own endpoint** (a local Ollama, for example):

```env
NEVADA_API_BASE=http://localhost:11434/v1
NEVADA_MODEL=qwen2.5:7b
```

> **On choosing a model.** Use regular instruct models. Reasoning models were tested
> and don't fit this agent: under a long system prompt they start thinking out loud
> in the reply itself and never reach the tool call. Providers also retire models —
> if the model name doesn't match the provider, Nevada warns you at startup.

## Running

```bash
python main.py
```

The app lives in the tray: chat, dashboard, settings, Jarvis HUD, exit.
Default global hotkey — `Ctrl+Shift+Space`.

## Building an .exe

```bash
python build.py
```

The build appears in `dist/Nevada/`. Put your `.env` next to `Nevada.exe` — that's
where the app looks for it.

> Your working `.env` is deliberately **not** copied into the build: otherwise your
> API key would travel with the folder every time you share it.

---

## Tests

```bash
python tests/run_tests.py          # 11 offline tests: no network, keys or windows
python tests/run_tests.py --live   # live: network, provider tokens, real windows
```

Tests are plain scripts printing `[OK ]` / `[FAIL]` and a final `ИТОГ:` line.
The runner requires that line: a truncated or silently crashed file also exits with
code 0, and without this check it would report a false green.

Details in [tests/README.md](tests/README.md).

---

## Layout

```
agent/     loop, prompt, tool-call parser, QThread worker
tools/     agent tools + registry
skills/    skill scenarios (.md) and their loader
ui/        windows: main, HUD, floating, commands, confirmation
voice/     speech recognition, synthesis, lazy-loading manager
memory/    conversation history in SQLite
scheduler/ task planner
tests/     tests and runner
```

A per-file breakdown lives in [NEVADA_PROJECT.md](NEVADA_PROJECT.md) (in Russian).

## Dependencies

PyQt6, openai, python-dotenv, faster-whisper, sounddevice, pyttsx3, keyboard,
pywin32, requests, apscheduler, psutil, pyinstaller.

## License

Not specified.
