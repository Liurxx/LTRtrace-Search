#!/bin/bash
#=============================================================================
# CenSoloLTR-Search — Windows Build (EXE Installer with Wizard)
#
# Prerequisites:
#   1. Wine + Windows Python 3.11  →  bash scripts/prepare_wine.sh
#   2. NSIS (makensis)             →  sudo apt install nsis
#   3. BLAST+ Windows binaries     →  place in blast/windows/
#
# Usage: bash scripts/platforms/build_windows.sh [VERSION]
#=============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${PKG_DIR}/source"
OUTPUT_DIR="${PKG_DIR}/output"
BUILD_DIR="${PKG_DIR}/build/windows"
RESOURCES_DIR="${PKG_DIR}/resources"
STAGE_DIR="${BUILD_DIR}/stage"

export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-censololtr}"
export WINEARCH="win64"
export WINEDEBUG=-all

VERSION="${1:-1.0.0}"
APP_NAME="CenSoloLTR-Search"
PYTHON_WIN="C:\\Program Files\\Python311\\python.exe"

# Convert Linux path to Windows Z: path (double-backslash for Python string safety)
to_win() { echo "Z:${1//\//\\\\}"; }

echo "╔══════════════════════════════════════════════╗"
echo "║  CenSoloLTR-Search v${VERSION} — Windows Build║"
echo "╚══════════════════════════════════════════════╝"

# ── Check prerequisites ──
PYTHON_LINUX="${WINEPREFIX}/drive_c/Program Files/Python311/python.exe"
if [ ! -f "${PYTHON_LINUX}" ]; then
    echo ""
    echo "ERROR: Windows Python not found in Wine."
    echo "Run first:  bash scripts/prepare_wine.sh"
    exit 1
fi

if ! command -v makensis &>/dev/null; then
    echo "ERROR: makensis not found. Install: sudo apt install nsis"
    exit 1
fi

# ── Update version ──
python3 -c "
import re
f = '${SOURCE_DIR}/slb_suite/__init__.py'
c = open(f).read()
open(f,'w').write(re.sub(r'__version__ = .*', '__version__ = \"${VERSION}\"', c))
"

# ── Clean ──
echo ">>> Cleaning..."
rm -rf "${BUILD_DIR}" "${PKG_DIR}/build/tmp"
mkdir -p "${BUILD_DIR}" "${STAGE_DIR}" "${OUTPUT_DIR}"

# ── PyInstaller (Wine) ──
# NOTE: Wine's ucrtbase has stdio issues when running Python directly.
# We use a wrapper script that redirects stdout/stderr to files first.
echo ">>> Building EXE with PyInstaller (Wine)..."
cat > "${WINEPREFIX}/drive_c/build_exe.py" << PYEOF
import sys, os
sys.stdout = open('C:\\\\pyi_stdout.txt', 'w')
sys.stderr = open('C:\\\\pyi_stderr.txt', 'w')
sys.stdin = open('NUL', 'r')

os.chdir('$(to_win "${SOURCE_DIR}")')

import PyInstaller.__main__
PyInstaller.__main__.run([
    '--name=${APP_NAME}',
    '--windowed',
    '--onefile',
    '--distpath=$(to_win "${BUILD_DIR}/dist")',
    '--workpath=$(to_win "${PKG_DIR}/build/tmp")',
    '--specpath=$(to_win "${PKG_DIR}/build/tmp")',
    '--icon=$(to_win "${RESOURCES_DIR}/icon.ico")',
    '--add-data=$(to_win "${SOURCE_DIR}/slb_suite");slb_suite',
    '--hidden-import=PyQt6.QtCore',
    '--hidden-import=PyQt6.QtGui',
    '--hidden-import=PyQt6.QtWidgets',
    '--hidden-import=matplotlib.backends.backend_qtagg',
    '--hidden-import=numpy',
    '--hidden-import=sqlite3',
    '--exclude-module=tkinter',
    '--exclude-module=test',
    '--exclude-module=pytest',
    '--exclude-module=pip',
    '--clean',
    'main.py',
])
PYEOF

wine "${PYTHON_WIN}" "C:\\build_exe.py" 2>&1 | grep -v "^[0-9a-f]*:err:" || true

# Check build output
EXE_PATH="${BUILD_DIR}/dist/${APP_NAME}.exe"
if [ ! -f "${EXE_PATH}" ]; then
    echo "ERROR: PyInstaller failed."
    echo "--- PyInstaller stderr ---"
    cat "${WINEPREFIX}/drive_c/pyi_stderr.txt" 2>/dev/null | tail -15
    echo "---"
    exit 1
fi
echo ">>> EXE: $(du -h "${EXE_PATH}" | cut -f1)"

# ── Stage files for NSIS ──
echo ">>> Staging installer files..."
cp "${EXE_PATH}" "${STAGE_DIR}/"

mkdir -p "${STAGE_DIR}/blast" "${STAGE_DIR}/data" "${STAGE_DIR}/docs" "${STAGE_DIR}/resources"
cp "${RESOURCES_DIR}/icon.ico" "${STAGE_DIR}/resources/" 2>/dev/null || true
cp "${RESOURCES_DIR}/LICENSE.txt" "${STAGE_DIR}/resources/" 2>/dev/null || true

# BLAST+
BLAST_DIR=""
for d in "${PKG_DIR}/blast/windows" "${PKG_DIR}/../blast/windows"; do
    [ -f "${d}/makeblastdb.exe" ] && BLAST_DIR="$d" && break
done
if [ -n "${BLAST_DIR}" ]; then
    cp -r "${BLAST_DIR}/"* "${STAGE_DIR}/blast/" 2>/dev/null || true
    echo "    BLAST+ binaries: OK ($(ls "${STAGE_DIR}/blast/"* 2>/dev/null | wc -l) files)"
else
    echo "    BLAST+ binaries: NOT FOUND (download https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/)"
fi

# Data files
DB_ROOT="${PKG_DIR}/.."
echo "    Database root: ${DB_ROOT}"

# Required SQLite databases
cp "${DB_ROOT}/SLB_Suite/ltr.sqlite"          "${STAGE_DIR}/data/" 2>/dev/null || echo "    WARN: ltr.sqlite not found"
cp "${DB_ROOT}/SLB_Suite/annotation.sqlite"    "${STAGE_DIR}/data/" 2>/dev/null || echo "    WARN: annotation.sqlite not found"

# Data directories — copy all that exist (NSIS uses /nonfatal for optional ones)
# The directory names match what slb_suite/utils/config.py expects
DATA_DIRS=(
    "0.1.genome_information"
    "0.genome_data_index"
    "0.NonRedundant_LTR_Libraries"
    "2.CEN_region_Bed"
    "10.CEN_PeriCEN_Final_Annotations_1"
    "11.CEN_PeriCEN_SoloLTR_FASTA_1"
    "12.Arm_Final_Annotations_1"
    "13.Arm_SoloLTR_FASTA_1"
)

for dir in "${DATA_DIRS[@]}"; do
    if [ -d "${DB_ROOT}/${dir}" ]; then
        cp -r "${DB_ROOT}/${dir}" "${STAGE_DIR}/data/"
        echo "    + ${dir}: $(du -sh "${DB_ROOT}/${dir}" 2>/dev/null | cut -f1)"
    else
        echo "    - ${dir}: NOT FOUND"
    fi
done

# Documentation
for doc in "${PKG_DIR}/../"*技术架构*.md "${PKG_DIR}/../"*打包*.md "${PKG_DIR}/../"*CenSoloLTR*.md; do
    [ -f "$doc" ] && cp "$doc" "${STAGE_DIR}/docs/" 2>/dev/null
done

# ── Build NSIS Installer ──
echo ">>> Building NSIS installer..."
makensis \
    -DPRODUCT_VERSION="${VERSION}" \
    -DSTAGE_DIR="${STAGE_DIR}" \
    -DRESOURCES_DIR="${RESOURCES_DIR}" \
    -DOUTPUT_DIR="${OUTPUT_DIR}" \
    "${PKG_DIR}/scripts/installer.nsi" 2>&1 | grep -E "warning|Error|Output:|Total size" || true

# ── Done ──
INSTALLER="${OUTPUT_DIR}/${APP_NAME}-Setup-${VERSION}.exe"
if [ -f "${INSTALLER}" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  Windows Installer Ready!                    ║"
    echo "╠══════════════════════════════════════════════╣"
    echo "║  ${INSTALLER}"
    echo "║  Size: $(du -h "${INSTALLER}" | cut -f1)"
    echo "╚══════════════════════════════════════════════╝"
else
    echo "ERROR: NSIS did not produce installer."
    exit 1
fi
