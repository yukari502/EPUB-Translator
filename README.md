# EPUB Python Translator

A compact and dependency-free Python tool for translating EPUB files. It preserves the core workflow of the original Electron-based application, while completely removing the heavy Node/Electron stack.

## ✨ Features

- **Direct EPUB Processing**: Open and parse EPUB files natively using `zipfile` and OPF spine metadata.
- **Flexible Translation Scope**: Translate a single chapter or process the entire book automatically.
- **Preserve Formatting**: Exports a translated EPUB while keeping all original assets, CSS styles, images, and metadata completely untouched.
- **Translation Modes**: 
  - **Bilingual Mode (Default)**: The original text is visually dimmed and kept structurally intact, while the translation is cleanly inserted as a separate block below it.
  - **Translate-Only Mode**: Replaces the original text entirely with the translation.
- **Multiple API Providers**: Supports Google Translate Web, OpenAI-compatible APIs, DeepSeek, Ollama, Gemini, and custom endpoints.
- **Translation Cache**: Prevents duplicate API requests and saves costs by reusing translation results through a local `.translation_cache.json` file.
- **Local Config Encryption**: Sensitive API keys in your `config.json` are encrypted securely locally.
- **Intuitive GUI**: A lightweight Tkinter desktop interface that:
  - Supports live readable preview windows during translation.
  - Allows you to safely stop the translation after the current in-flight request.
  - Remembers your provider, API keys, endpoints, language targets, concurrency, and glossary settings automatically.
- **CLI Support**: Fully automatable via the command line interface.

---

## 🚀 Installation & Setup

1. Make sure you have Python 3.10+ installed.
2. Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

---

## 💻 Usage

### GUI App
Run the Tkinter-based desktop interface:

```bash
python gui_launcher.py
```

#### Previews

![Home preview](images/1.png)

![Translation in progress preview](images/2.png)

### CLI Tool
For automated or headless usage, use `epub_translator.cli`:

**Translate a whole EPUB (Default: Traditional Chinese, Bilingual):**
```bash
python -m epub_translator.cli input.epub output.epub --provider google-web
```

**OpenAI-compatible example:**
```bash
python -m epub_translator.cli input.epub output.epub ^
  --provider openai ^
  --api-key YOUR_KEY ^
  --model gpt-4o-mini ^
  --target "Simplified Chinese" ^
  --mode bilingual
```

**Ollama example:**
```bash
python -m epub_translator.cli input.epub output.epub --provider ollama --model llama3
```

> **Note:** For OpenAI-compatible providers, `--api-url` may be either the service root or the full chat-completions URL.
> For example, `http://localhost:11434` is automatically normalized to `http://localhost:11434/v1/chat/completions`.

---

## 📦 Building the Executable

You can compile the app into a single, portable Windows executable (`.exe`) that doesn't require users to have Python installed.

1. Install PyInstaller:
```bash
python -m pip install pyinstaller
```

2. Build the app (the output will be saved to the `release` folder):
```bash
pyinstaller --noconfirm --onefile --windowed --name "EPUB-Translator" --distpath release gui_launcher.py
```

Once the build finishes, you will find `EPUB-Translator.exe` inside the `release` folder. You can move this `.exe` file anywhere—your configuration and caches will be generated securely in the same directory as the executable.

---

## 📝 Notes

- **Google Web Provider**: This translation is free but unofficial and heavily throttled. For full-length books, using an API-backed provider (like DeepSeek, Gemini, or OpenAI) is highly recommended for stability.
- **Config Storage**: GUI settings are securely encrypted and saved locally in `config.json` next to your executable or script.
