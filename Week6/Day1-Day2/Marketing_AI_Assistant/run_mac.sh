#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo " Marketing AI Assistant - macOS setup"
echo "=============================================="

# Prefer Python 3.12, then 3.11, then the system python3.
PYTHON=""
for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VERSION=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        MAJOR=${VERSION%%.*}
        MINOR=${VERSION#*.}
        if [ "$MAJOR" -gt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; }; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Python 3.10 or newer is required. Install Python 3.12 from https://www.python.org/downloads/"
    exit 1
fi

echo "Using $($PYTHON --version)"
if [ ! -d ".venv" ]; then
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "Starting the application..."
echo "When Streamlit starts, open http://localhost:8501"
python -m streamlit run app.py
