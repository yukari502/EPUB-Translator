@echo off
setlocal EnableDelayedExpansion
echo ==============================================
echo EPUB Translator - One-Click Launcher
echo ==============================================

set "PYTHON_EXE=python"
set "USE_PORTABLE=0"

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] System Python is not installed or not in PATH.
    
    if exist "python-portable\python.exe" (
        echo [INFO] Found local portable Python.
        set "PYTHON_EXE=%CD%\python-portable\python.exe"
        set "USE_PORTABLE=1"
    ) else (
        echo ==========================================================
        echo Do you want to automatically download a local portable Python environment?
        echo This will take ~20MB of disk space and won't affect your system.
        echo ==========================================================
        set /p DL_CHOICE="Download now? (Y/N): "
        if /i "!DL_CHOICE!"=="Y" (
            echo [1/4] Downloading Python portable 3.11.8...
            curl -L -o python-portable.zip https://www.python.org/ftp/python/3.11.8/python-3.11.8-embed-amd64.zip
            if not exist "python-portable.zip" (
                echo [ERROR] Download failed. Please check your internet connection.
                pause
                exit /b 1
            )
            echo [2/4] Extracting Python...
            powershell -command "Expand-Archive -Path python-portable.zip -DestinationPath python-portable -Force"
            del python-portable.zip
            
            echo [3/4] Configuring Python environment ^(enabling pip support^)...
            :: The python311._pth file needs '#import site' replaced with 'import site'
            powershell -command "(Get-Content python-portable\python311._pth) -replace '#import site', 'import site' | Set-Content python-portable\python311._pth"
            
            echo [4/4] Installing pip...
            curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
            python-portable\python.exe get-pip.py
            del get-pip.py
            
            set "PYTHON_EXE=%CD%\python-portable\python.exe"
            set "USE_PORTABLE=1"
        ) else (
            echo [ERROR] Cannot proceed without Python.
            pause
            exit /b 1
        )
    )
) else (
    echo [INFO] System Python detected.
)

if "!USE_PORTABLE!"=="1" (
    echo [INFO] Using portable Python environment.
    echo Checking dependencies...
    "!PYTHON_EXE!" -m pip install --upgrade pip
    "!PYTHON_EXE!" -m pip install -e .
    "!PYTHON_EXE!" -m pip install fastapi uvicorn httpx python-multipart websockets bs4 pydantic pydantic-core
) else (
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
)

echo ==============================================
echo [INFO] Starting EPUB Translator Web UI...
echo ==============================================
if "!USE_PORTABLE!"=="1" (
    "!PYTHON_EXE!" -m epub_translator.web_server
) else (
    python -m epub_translator.web_server
)

pause
