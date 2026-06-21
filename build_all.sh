#!/bin/bash
#=============================================================================
# CenSoloLTR-Search — Master Build Script
#
# Builds installers for all platforms supported on this machine.
#
# Usage:
#   bash build_all.sh [VERSION]            # Auto-detect platform, build what's possible
#   bash build_all.sh 1.0.0 linux          # Build Linux only
#   bash build_all.sh 1.0.0 windows        # Build Windows only (needs Wine)
#   bash build_all.sh 1.0.0 macos          # Build macOS only (needs Mac)
#=============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="${SCRIPT_DIR}"
VERSION="${1:-1.0.0}"
TARGET="${2:-auto}"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║                                              ║"
echo "║       CenSoloLTR-Search v${VERSION}            ║"
echo "║       Cross-Platform Package Builder         ║"
echo "║                                              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Make scripts executable ──
chmod +x "${PKG_DIR}/scripts/platforms/"*.sh 2>/dev/null || true
chmod +x "${PKG_DIR}/scripts/prepare_wine.sh" 2>/dev/null || true

# ── Build by platform ──
build_linux() {
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  BUILDING: Linux AppImage"
    echo "═══════════════════════════════════════════════"
    bash "${PKG_DIR}/scripts/platforms/build_linux.sh" "${VERSION}"
}

build_windows() {
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  BUILDING: Windows NSIS Installer"
    echo "═══════════════════════════════════════════════"

    # Check if Wine environment exists
    WINEPREFIX="${WINEPREFIX:-$HOME/.wine-censololtr}"
    if [ ! -f "${WINEPREFIX}/drive_c/Python311/python.exe" ]; then
        echo ""
        echo ">>> Wine environment not found."
        echo ">>> Running prepare_wine.sh first..."
        bash "${PKG_DIR}/scripts/prepare_wine.sh"
    fi

    bash "${PKG_DIR}/scripts/platforms/build_windows.sh" "${VERSION}"
}

build_macos() {
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  BUILDING: macOS DMG"
    echo "═══════════════════════════════════════════════"

    if [ "$(uname)" != "Darwin" ]; then
        echo ""
        echo "!!! macOS builds must run on a Mac."
        echo "!!! Copy this entire directory to a Mac and run:"
        echo "!!!   bash build_all.sh ${VERSION} macos"
        echo "!!! OR:"
        echo "!!!   bash scripts/platforms/build_macos.sh ${VERSION}"
        echo ""
        return 1
    fi

    bash "${PKG_DIR}/scripts/platforms/build_macos.sh" "${VERSION}"
}

# ── Main dispatch ──
case "${TARGET}" in
    linux)
        build_linux
        ;;
    windows)
        build_windows
        ;;
    macos)
        build_macos
        ;;
    auto)
        # Build whatever this platform supports
        build_linux

        if command -v wine &>/dev/null; then
            build_windows
        else
            echo ""
            echo "=== Skipping Windows build (Wine not available) ==="
            echo "    Install Wine and run:  bash build_all.sh ${VERSION} windows"
        fi

        if [ "$(uname)" = "Darwin" ]; then
            build_macos
        else
            echo ""
            echo "=== Skipping macOS build (requires macOS) ==="
            echo "    Copy this directory to a Mac and run:"
            echo "    bash build_all.sh ${VERSION} macos"
        fi
        ;;
    *)
        echo "Unknown target: ${TARGET}"
        echo "Usage: bash build_all.sh [VERSION] [linux|windows|macos|auto]"
        exit 1
        ;;
esac

# ── Summary ──
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  BUILD COMPLETE                               ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Output directory: output/                    ║"
for f in "${PKG_DIR}/output/"*; do
    [ -f "$f" ] && echo "║    $(basename "$f")  ($(du -h "$f" | cut -f1))"
done
echo "╚══════════════════════════════════════════════╝"
