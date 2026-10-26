@echo off
REM One-click start for Windows: sets up everything and opens the app.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10+ from python.org and tick "Add Python to PATH".
    pause
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing packages (first run can take a minute)...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo Package install failed. Check your internet connection and try again.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env >nul
    echo.
    echo A .env file was created. Notepad will open it now.
    echo Paste your OpenAI API key after OPENAI_API_KEY=, save, close Notepad,
    echo then double-click start.bat again.
    notepad .env
    pause
    exit /b 0
)

echo.
echo Starting the app at http://127.0.0.1:8000 ...
python app.py
pause
