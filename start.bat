@echo off
setlocal
echo ==============================================
echo EPUB Translator - One-Click Launcher
echo ==============================================

if not exist .venv (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/3] Virtual environment already exists.
)

echo [2/3] Activating virtual environment and checking dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .
pip install fastapi uvicorn httpx python-multipart websockets bs4 pydantic pydantic-core

echo [3/3] Starting EPUB Translator Web UI...
python -m epub_translator.web_server

pause
