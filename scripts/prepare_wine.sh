#!/bin/bash
#=============================================================================
# LTRtrace-Search — Prepare Wine Build Environment (run once)
# Prerequisites: wine, wget
#=============================================================================
set -e

WINEPREFIX="${WINEPREFIX:-$HOME/.wine-censololtr}"
export WINEPREFIX
export WINEARCH="win64"

PYTHON_VER="3.11.9"
PYTHON_EXE="${WINEPREFIX}/drive_c/Program Files/Python311/python.exe"

echo "╔══════════════════════════════════════════════╗"
echo "║  Prepare Wine Environment for Windows Builds ║"
echo "╚══════════════════════════════════════════════╝"

# ── Wine prefix ──
if [ ! -d "${WINEPREFIX}" ]; then
    echo ">>> Creating Wine prefix..."
    wineboot -u 2>&1 | tail -1
else
    echo ">>> Wine prefix exists: ${WINEPREFIX}"
fi

# ── Windows Python ──
if [ -f "${PYTHON_EXE}" ]; then
    echo ">>> Python already installed: $("${PYTHON_EXE}" --version 2>/dev/null || echo '?')"
else
    echo ">>> Downloading Windows Python ${PYTHON_VER}..."
    PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VER}/python-${PYTHON_VER}-amd64.exe"
    wget --timeout=60 -q --show-progress -O /tmp/python-windows.exe "${PYTHON_URL}" || {
        echo "ERROR: Failed to download Python."
        exit 1
    }

    echo ">>> Installing Python in Wine..."
    wine /tmp/python-windows.exe /quiet InstallAllUsers=1 PrependPath=1 2>&1 | tail -3
    rm -f /tmp/python-windows.exe
    sleep 2
fi

# Note: Python installs to C:\Program Files\Python311\ with InstallAllUsers=1
PYTHON_EXE="${WINEPREFIX}/drive_c/Program Files/Python311/python.exe"

# ── Pip packages ──
echo ">>> Installing pip packages..."
wine "${PYTHON_EXE}" -m pip install --upgrade pip -q 2>&1 | tail -1

echo "    pyinstaller..."
wine "${PYTHON_EXE}" -m pip install pyinstaller -q 2>&1 | tail -1

echo "    PyQt6 (6.7.1 for Wine compat)..."
wine "${PYTHON_EXE}" -m pip install PyQt6==6.7.1 -q 2>&1 | tail -1

echo "    numpy (1.24.3 for Wine compat)..."
wine "${PYTHON_EXE}" -m pip install numpy==1.24.3 -q 2>&1 | tail -1

echo "    matplotlib (3.8.4 for numpy 1.24 compat)..."
wine "${PYTHON_EXE}" -m pip install matplotlib==3.8.4 -q 2>&1 | tail -1

echo "    PyPDF2..."
wine "${PYTHON_EXE}" -m pip install PyPDF2 -q 2>&1 | tail -1

# ── Verify ──
echo ""
echo "=== Verification ==="
wine "${PYTHON_EXE}" --version 2>&1

# Use a Python script with file output to avoid Wine stdio issues
cat > "${WINEPREFIX}/drive_c/verify.py" << 'PYEOF'
import sys
sys.stdout = open('C:\\verify_out.txt', 'w')
sys.stderr = sys.stdout
for mod in ['numpy', 'matplotlib', 'PyQt6.QtCore', 'PyQt6.QtGui',
            'PyQt6.QtWidgets', 'PyPDF2', 'PyInstaller', 'sqlite3']:
    try:
        m = __import__(mod)
        v = getattr(m, '__version__', '')
        print(f'  {mod}: OK {v}')
    except Exception as e:
        print(f'  {mod}: FAIL - {e}')
PYEOF

wine "${PYTHON_EXE}" "C:\\verify.py" 2>&1 | grep -v "^[0-9a-f]*:err:" | head -5
sleep 2
cat "${WINEPREFIX}/drive_c/verify_out.txt" 2>/dev/null

echo ""
echo "=== Environment ready ==="
echo "You can now run:  bash scripts/platforms/build_windows.sh"
