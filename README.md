# EPUB Translator

A lightweight, modern Python tool to translate EPUB files using LLMs (OpenAI, Gemini, DeepSeek, etc.) directly in your browser.

## Features
- **Extremely fast and lightweight**: Uses a modern FastAPI + AsyncIO backend, avoiding slow Tkinter GUIs.
- **Deduplication Engine**: Caches paragraphs and removes duplicates before sending to LLMs, reducing token costs and translation time by up to 50%.
- **Live Translation Preview**: A WYSIWYG (What You See Is What You Get) reader directly in the browser. See translations appear block-by-block.
- **Dynamic Bilingual Mode**: Switch between Bilingual and Translation Only modes instantly, without re-translating.
- **One-Click Startup**: Auto-creates virtual environments and installs dependencies automatically.

## Quick Start (Windows)
1. Double click `start.bat`.
2. It will automatically download dependencies and open the translation web UI in your browser.

## Supported Providers
- **Google Web** (Free, no API key required)
- **OpenAI Compatible** (ChatGPT, Claude, etc)
- **Gemini** (Google API)
- **DeepSeek**
- **Ollama** (Local models)
- **Custom API**

## Cache Management
- Translations are cached locally to `.translation_cache.json` so you never pay twice for the same sentence.
- You can Export/Import caches to share translation progress across devices.
