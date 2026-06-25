#!/bin/bash
#=============================================================================
# LTRtrace-Search — Linux Build (AppImage, self-contained with data)
# Usage: bash scripts/platforms/build_linux.sh [VERSION]
#=============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${PKG_DIR}/source"
OUTPUT_DIR="${PKG_DIR}/output"
BUILD_DIR="${PKG_DIR}/build/linux"
RESOURCES_DIR="${PKG_DIR}/resources"

VERSION="${1:-1.0.0}"
APP_NAME="LTRtrace-Search"

echo "╔══════════════════════════════════════════════╗"
echo "║  LTRtrace-Search v${VERSION} — Linux Build  ║"
echo "╚══════════════════════════════════════════════╝"

# ── Prerequisites ──
command -v python3 &>/dev/null || { echo "ERROR: python3 required"; exit 1; }

if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo ">>> Installing PyInstaller..."
    pip install pyinstaller
fi

# ── Clean ──
echo ">>> Cleaning..."
rm -rf "${BUILD_DIR}" "${PKG_DIR}/build/tmp"
mkdir -p "${BUILD_DIR}" "${OUTPUT_DIR}"

# ── Update version ──
python3 -c "
import re
f = '${SOURCE_DIR}/slb_suite/__init__.py'
c = open(f).read()
open(f,'w').write(re.sub(r'__version__ = .*', '__version__ = \"${VERSION}\"', c))
"

# ── PyInstaller ──
echo ">>> Building with PyInstaller..."
cd "${SOURCE_DIR}"

python3 -m PyInstaller \
    --name="${APP_NAME}" \
    --windowed \
    --onefile \
    --distpath="${BUILD_DIR}/dist" \
    --workpath="${PKG_DIR}/build/tmp" \
    --specpath="${PKG_DIR}/build/tmp" \
    --add-data="${SOURCE_DIR}/slb_suite:slb_suite" \
    --hidden-import="PyQt6.QtCore" \
    --hidden-import="PyQt6.QtGui" \
    --hidden-import="PyQt6.QtWidgets" \
    --hidden-import="matplotlib.backends.backend_qtagg" \
    --hidden-import="numpy" \
    --hidden-import="sqlite3" \
    --exclude-module="tkinter" \
    --exclude-module="test" \
    --exclude-module="pytest" \
    --exclude-module="pip" \
    --clean \
    main.py

if [ ! -f "${BUILD_DIR}/dist/${APP_NAME}" ]; then
    echo "ERROR: PyInstaller failed."
    exit 1
fi
chmod +x "${BUILD_DIR}/dist/${APP_NAME}"
echo ">>> Binary: $(du -h "${BUILD_DIR}/dist/${APP_NAME}" | cut -f1)"

# ── AppDir ──
echo ">>> Preparing AppDir..."
APPDIR="${BUILD_DIR}/AppDir"
mkdir -p "${APPDIR}/usr/bin/blast"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${APPDIR}/usr/share/applications"

cp "${BUILD_DIR}/dist/${APP_NAME}" "${APPDIR}/usr/bin/"

# ── BLAST+ (Linux binaries) ──
echo ">>> Staging BLAST+..."
BLAST_COUNT=0
for blast_bin in makeblastdb blastn blastp blastx tblastn tblastx blastdbcmd; do
    for prefix in /usr/bin /usr/local/bin /opt/conda/bin; do
        if [ -f "${prefix}/${blast_bin}" ]; then
            cp "${prefix}/${blast_bin}" "${APPDIR}/usr/bin/blast/"
            ((BLAST_COUNT++)) || true
            break
        fi
    done
done
echo "    BLAST+ binaries: ${BLAST_COUNT} staged"

# ── Data staging ──
# Data is placed in usr/bin/data/ so that config.py resolves:
#   APP_DIR  = dirname(sys.executable) = usr/bin/
#   DATA_ROOT = <app_dir>/data/        = usr/bin/data/
echo ">>> Staging data files..."
DATA_DIR="${APPDIR}/usr/bin/data"
mkdir -p "${DATA_DIR}"

DB_ROOT="${PKG_DIR}/.."

# Required SQLite databases
cp "${DB_ROOT}/SLB_Suite/ltr.sqlite"       "${DATA_DIR}/" && echo "    ltr.sqlite: OK"          || echo "    WARN: ltr.sqlite not found"
cp "${DB_ROOT}/SLB_Suite/annotation.sqlite" "${DATA_DIR}/" && echo "    annotation.sqlite: OK" || echo "    WARN: annotation.sqlite not found"

# Data directories — must match config.py expectations
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
        cp -r "${DB_ROOT}/${dir}" "${DATA_DIR}/"
        echo "    + ${dir}: $(du -sh "${DB_ROOT}/${dir}" 2>/dev/null | cut -f1)"
    else
        echo "    - ${dir}: NOT FOUND"
    fi
done

echo "    Total data staged: $(du -sh "${DATA_DIR}" 2>/dev/null | cut -f1)"

# ── Desktop integration files ──
cp "${RESOURCES_DIR}/icon.png" \
    "${APPDIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png" 2>/dev/null || true
cp "${RESOURCES_DIR}/LTRtrace-Search.desktop" \
    "${APPDIR}/usr/share/applications/" 2>/dev/null || true

# AppImage requires .desktop + icon at AppDir root
cp "${RESOURCES_DIR}/LTRtrace-Search.desktop" "${APPDIR}/" 2>/dev/null || true
cp "${RESOURCES_DIR}/icon.png" "${APPDIR}/${APP_NAME}.png" 2>/dev/null || true

cat > "${APPDIR}/AppRun" << 'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="${HERE}/usr/bin:${HERE}/usr/bin/blast:${PATH}"
exec "${HERE}/usr/bin/LTRtrace-Search" "$@"
APPRUN
chmod +x "${APPDIR}/AppRun"

# ── AppImage ──
echo ">>> Building AppImage..."
APPIMAGETOOL=""

for candidate in \
    "${PKG_DIR}/scripts/appimagetool" \
    "${HOME}/.local/bin/appimagetool" \
    /usr/local/bin/appimagetool \
; do
    [ -f "$candidate" ] && [ -x "$candidate" ] && APPIMAGETOOL="$candidate" && break
done

if [ -z "${APPIMAGETOOL}" ]; then
    echo "    Downloading appimagetool..."
    wget -q -O "${PKG_DIR}/scripts/appimagetool" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" && \
        chmod +x "${PKG_DIR}/scripts/appimagetool" && \
        APPIMAGETOOL="${PKG_DIR}/scripts/appimagetool"
fi

if [ -n "${APPIMAGETOOL}" ] && [ -f "${APPIMAGETOOL}" ]; then
    export ARCH=x86_64
    "${APPIMAGETOOL}" "${APPDIR}" "${OUTPUT_DIR}/${APP_NAME}-${VERSION}-x86_64.AppImage"
    chmod +x "${OUTPUT_DIR}/${APP_NAME}-${VERSION}-x86_64.AppImage"
else
    # Fallback: just copy the raw binary
    cp "${BUILD_DIR}/dist/${APP_NAME}" "${OUTPUT_DIR}/${APP_NAME}-${VERSION}-linux"
    echo "    AppImage tool not available, raw binary copied."
fi

# ── Done ──
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Linux build complete                         ║"
for f in "${OUTPUT_DIR}/${APP_NAME}"*; do
    echo "║  $(basename "$f")  $(du -h "$f" | cut -f1)"
done
echo "╚══════════════════════════════════════════════╝"
