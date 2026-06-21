#!/bin/bash
#=============================================================================
# CenSoloLTR-Search — macOS Build (self-contained .dmg with all data)
#
# MUST run on macOS. Unlike Windows (Wine), there is no mature macOS
# compatibility layer on Linux for building GUI app bundles.
#
# Prerequisites (macOS 12+):
#   1. Xcode CLI Tools:   xcode-select --install
#   2. Python 3.10+:      brew install python@3.11
#   3. PyInstaller:        pip3 install pyinstaller
#   4. BLAST+ binaries:    place in blast/macos/  or install via brew
#
# Usage: bash scripts/platforms/build_macos.sh [VERSION]
#
# Alternative — build on GitHub Actions (free macOS runner):
#   See .github/workflows/build_macos.yml
#=============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${PKG_DIR}/source"
OUTPUT_DIR="${PKG_DIR}/output"
BUILD_DIR="${PKG_DIR}/build/macos"
RESOURCES_DIR="${PKG_DIR}/resources"

VERSION="${1:-1.0.0}"
APP_NAME="CenSoloLTR-Search"
BUNDLE_NAME="${APP_NAME}.app"

echo "╔══════════════════════════════════════════════╗"
echo "║  CenSoloLTR-Search v${VERSION} — macOS Build   ║"
echo "╚══════════════════════════════════════════════╝"

# ── Platform check ──
if [ "$(uname)" != "Darwin" ]; then
    echo ""
    echo "ERROR: macOS builds must run on macOS."
    echo ""
    echo "  Option A — Copy to a Mac and run this script there."
    echo "  Option B — Use GitHub Actions (free):"
    echo "      git push && gh workflow run build-macos.yml"
    echo ""
    echo "  Why: no mature macOS ABI layer exists on Linux (Darling does"
    echo "  not support GUI apps). Cross-compiling PyInstaller + PyQt6 is"
    echo "  not practically feasible. Unlike Wine for Windows, there is no"
    echo "  equivalent compatibility layer for macOS GUI applications."
    exit 1
fi

# ── Prerequisites ──
command -v python3 &>/dev/null || { echo "ERROR: python3 required"; exit 1; }

if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo ">>> Installing PyInstaller..."
    pip3 install pyinstaller
fi

# ── Clean ──
echo ">>> Cleaning..."
rm -rf "${BUILD_DIR}" "${PKG_DIR}/build/tmp"
mkdir -p "${BUILD_DIR}" "${OUTPUT_DIR}"

# ── Update version ──
echo ">>> Setting version to ${VERSION}..."
python3 -c "
import re
f = '${SOURCE_DIR}/slb_suite/__init__.py'
c = open(f).read()
open(f,'w').write(re.sub(r'__version__ = .*', '__version__ = \"${VERSION}\"', c))
"

# ── Icon: PNG → ICNS (macOS requires .icns format) ──
echo ">>> Preparing icon..."
ICONSET_DIR="${BUILD_DIR}/${APP_NAME}.iconset"
mkdir -p "${ICONSET_DIR}"

SRC_PNG="${RESOURCES_DIR}/icon.png"

# Generate @1x sizes
for size in 16 32 128 256 512; do
    sips -z ${size} ${size} "${SRC_PNG}" --out "${ICONSET_DIR}/icon_${size}x${size}.png" &>/dev/null
done
# Generate @2x retina sizes
for size in 32 64 256 512 1024; do
    half=$((size / 2))
    sips -z ${size} ${size} "${SRC_PNG}" --out "${ICONSET_DIR}/icon_${half}x${half}@2x.png" &>/dev/null
done

iconutil -c icns "${ICONSET_DIR}" -o "${BUILD_DIR}/${APP_NAME}.icns"
echo "    Icon: OK"

# ── PyInstaller ──
echo ">>> Building with PyInstaller..."
cd "${SOURCE_DIR}"

python3 -m PyInstaller \
    --name="${APP_NAME}" \
    --windowed \
    --onefile \
    --osx-bundle-identifier="com.censololtr.search" \
    --icon="${BUILD_DIR}/${APP_NAME}.icns" \
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

# ── Assemble .app bundle ──
# Directory layout (designed to work with config.py):
#
#   CenSoloLTR-Search.app/
#   └── Contents/
#       ├── Info.plist
#       ├── MacOS/
#       │   ├── CenSoloLTR-Search      ← PyInstaller binary
#       │   └── blast/                 ← BLAST+ tools
#       ├── Resources/
#       │   └── CenSoloLTR-Search.icns ← app icon
#       └── data/                      ← all databases & annotation data
#           ├── ltr.sqlite
#           ├── annotation.sqlite
#           ├── 0.1.genome_information/
#           ├── 0.genome_data_index/
#           ├── 0.NonRedundant_LTR_Libraries/
#           ├── 2.CEN_region_Bed/
#           ├── 10.CEN_PeriCEN_Final_Annotations_1/
#           ├── 11.CEN_PeriCEN_SoloLTR_FASTA_1/
#           ├── 12.Arm_Final_Annotations_1/
#           └── 13.Arm_SoloLTR_FASTA_1/
#
# config.py resolution on macOS:
#   app_dir  = Contents/  (parent of MacOS/)
#   data_root = Contents/data/  ← first match

echo ">>> Assembling .app bundle..."
APP_DIR="${BUILD_DIR}/${BUNDLE_NAME}"
CONTENTS_DIR="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RES_DIR="${CONTENTS_DIR}/Resources"
DATA_DIR="${CONTENTS_DIR}/data"
BLAST_DIR="${MACOS_DIR}/blast"

mkdir -p "${MACOS_DIR}" "${RES_DIR}" "${DATA_DIR}" "${BLAST_DIR}"

# Binary
cp "${BUILD_DIR}/dist/${APP_NAME}" "${MACOS_DIR}/"

# Icon (icns format required by macOS)
cp "${BUILD_DIR}/${APP_NAME}.icns" "${RES_DIR}/"

# Info.plist — use the template file with version substitution
sed "s/__VERSION__/${VERSION}/g" "${RESOURCES_DIR}/Info.plist" > "${CONTENTS_DIR}/Info.plist"
echo "    Info.plist: OK"

# ── BLAST+ binaries ──
echo ">>> Staging BLAST+..."
BLAST_COUNT=0
BLAST_SRC=""
for d in "${PKG_DIR}/blast/macos" "${PKG_DIR}/../blast/macos"; do
    [ -f "${d}/makeblastdb" ] && BLAST_SRC="$d" && break
done

if [ -n "${BLAST_SRC}" ]; then
    for blast_bin in makeblastdb blastn blastp blastx tblastn tblastx blastdbcmd; do
        if [ -f "${BLAST_SRC}/${blast_bin}" ]; then
            cp "${BLAST_SRC}/${blast_bin}" "${BLAST_DIR}/"
            chmod +x "${BLAST_DIR}/${blast_bin}"
            ((BLAST_COUNT++)) || true
        fi
    done
else
    # Fallback: search system paths
    for blast_bin in makeblastdb blastn blastp blastx tblastn tblastx blastdbcmd; do
        for prefix in /usr/local/bin /opt/homebrew/bin /usr/bin; do
            if [ -f "${prefix}/${blast_bin}" ]; then
                cp "${prefix}/${blast_bin}" "${BLAST_DIR}/"
                chmod +x "${BLAST_DIR}/${blast_bin}"
                ((BLAST_COUNT++)) || true
                break
            fi
        done
    done
fi
echo "    BLAST+ binaries: ${BLAST_COUNT} staged"

# ── Data staging ──
echo ">>> Staging data files..."

DB_ROOT="${PKG_DIR}/.."

# SQLite databases
cp "${DB_ROOT}/SLB_Suite/ltr.sqlite"       "${DATA_DIR}/" && echo "    ltr.sqlite: OK"          || echo "    WARN: ltr.sqlite not found"
cp "${DB_ROOT}/SLB_Suite/annotation.sqlite" "${DATA_DIR}/" && echo "    annotation.sqlite: OK" || echo "    WARN: annotation.sqlite not found"

# Data directories
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
        cp -R "${DB_ROOT}/${dir}" "${DATA_DIR}/"
        echo "    + ${dir}: $(du -sh "${DB_ROOT}/${dir}" 2>/dev/null | cut -f1)"
    else
        echo "    - ${dir}: NOT FOUND"
    fi
done

echo "    Total data staged: $(du -sh "${DATA_DIR}" 2>/dev/null | cut -f1)"

# ── Code sign (ad-hoc, removes "unidentified developer" warning in some cases) ──
echo ">>> Code signing (ad-hoc)..."
if command -v codesign &>/dev/null; then
    # Sign BLAST+ binaries first (they must be signed before the main bundle)
    if ls "${BLAST_DIR}/"* 2>/dev/null | grep -q .; then
        for b in "${BLAST_DIR}/"*; do
            codesign --force --sign - --timestamp=none "$b" 2>/dev/null || true
        done
    fi
    codesign --deep --force --sign - --timestamp=none "${APP_DIR}" 2>/dev/null && \
        echo "    Signed: OK" || echo "    Signing skipped (may need Xcode)"
else
    echo "    codesign not available — OK for local use"
fi

# ── Build .dmg ──
echo ">>> Building .dmg..."
DMG_STAGE="${BUILD_DIR}/dmg_stage"
rm -rf "${DMG_STAGE}"
mkdir -p "${DMG_STAGE}"

cp -R "${APP_DIR}" "${DMG_STAGE}/"
ln -s /Applications "${DMG_STAGE}/Applications" 2>/dev/null || true

DMG_PATH="${OUTPUT_DIR}/${APP_NAME}-${VERSION}.dmg"
rm -f "${DMG_PATH}"

hdiutil create \
    -volname "${APP_NAME}" \
    -srcfolder "${DMG_STAGE}" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "${DMG_PATH}"

echo "    DMG: $(du -h "${DMG_PATH}" | cut -f1)"

# ── Optional: Developer ID signing & notarization ──
if [ -n "${CODESIGN_IDENTITY}" ]; then
    echo ">>> Signing with Developer ID: ${CODESIGN_IDENTITY}..."
    codesign --deep --force --verify --verbose \
        --options runtime \
        --sign "${CODESIGN_IDENTITY}" \
        "${APP_DIR}"
    echo "    Signed: OK"
fi

if [ -n "${NOTARIZE_APPLE_ID}" ] && [ -n "${NOTARIZE_TEAM_ID}" ]; then
    echo ">>> Submitting for notarization (this may take several minutes)..."
    rm -f "${BUILD_DIR}/${APP_NAME}.zip"
    ditto -c -k --keepParent "${APP_DIR}" "${BUILD_DIR}/${APP_NAME}.zip"

    xcrun notarytool submit "${BUILD_DIR}/${APP_NAME}.zip" \
        --apple-id "${NOTARIZE_APPLE_ID}" \
        --team-id "${NOTARIZE_TEAM_ID}" \
        --password "${NOTARIZE_APP_PASSWORD}" \
        --wait && \
        echo "    Notarization: accepted" || \
        echo "    Notarization: check result with: xcrun notarytool log <submission-id>"

    # Staple the ticket to the app
    xcrun stapler staple "${APP_DIR}" 2>/dev/null && echo "    Ticket stapled: OK" || true
fi

# ── Done ──
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  macOS build complete                         ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  .app : ${APP_DIR}"
echo "║  .dmg : ${DMG_PATH}"
echo "║  Size : $(du -h "${DMG_PATH}" | cut -f1)"
echo "║                                              ║"
echo "║  Install: open .dmg → drag to /Applications  ║"
echo "╚══════════════════════════════════════════════╝"
