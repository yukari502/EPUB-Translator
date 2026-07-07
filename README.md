# EPUB Translator

A lightweight, modern Python tool to translate EPUB files using LLMs (OpenAI, Gemini, DeepSeek, etc.) directly in your browser.

## Features
- **Extremely fast and lightweight**: Uses a modern FastAPI + AsyncIO backend, avoiding slow Tkinter GUIs.
- **Deduplication Engine**: Caches paragraphs and removes duplicates before sending to LLMs, reducing token costs and translation time by up to 50%.
- **Live Translation Preview**: A WYSIWYG (What You See Is What You Get) reader directly in the browser. See translations appear block-by-block.
- **Dynamic Bilingual Mode**: Switch between Bilingual and Translation Only modes instantly, without re-translating.
- **One-Click Startup**: Auto-creates virtual environments and installs dependencies automatically.

## Quick Start (Windows)
### Option A: Standalone Executable (Recommended for beginners)
1. Double click `EPUB-Translator.exe`.
2. A black console window will appear and the Web UI will automatically open in your default browser.
3. **To close the application:** Simply close the black console window.

### Option B: From Source / Batch script
1. Double click `start.bat`.
2. It will automatically download dependencies (if needed) and open the translation web UI in your browser.

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

## FAQ

### Does it support MOBI, AZW, or AZW3 formats?
This tool is specifically designed to be lightweight and focuses exclusively on the standard **EPUB** format. Kindle proprietary formats (MOBI/AZW3) are complex binary files that require heavy dependencies to repackage properly.

**Recommended Workflow for Kindle Users:**
1. Use [Calibre](https://calibre-ebook.com/) to convert your `.mobi` or `.azw3` files to `.epub`.
2. Translate the generated `.epub` file using this tool.
3. Use Amazon's **Send to Kindle** service to send the translated `.epub` to your device (Amazon now officially recommends EPUB and has deprecated MOBI).
4. *(Optional)* If you must transfer via USB, use Calibre to convert the translated EPUB back to AZW3.
