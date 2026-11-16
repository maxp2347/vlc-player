#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

ARGS=(--noconfirm --windowed --onefile --name VLCPlayer main.py)

case "$(uname -s)" in
  Darwin)
    VLC_LIB="/Applications/VLC.app/Contents/MacOS/lib"
    if [ -d "$VLC_LIB" ]; then
      ARGS+=(--add-binary "$VLC_LIB/libvlc.dylib:.")
      ARGS+=(--add-binary "$VLC_LIB/libvlccore.dylib:.")
    fi
    ;;
  Linux)
    if ls /usr/lib/x86_64-linux-gnu/libvlc.so* >/dev/null 2>&1; then
      ARGS+=(--add-binary "/usr/lib/x86_64-linux-gnu/libvlc.so*:.")
      ARGS+=(--add-binary "/usr/lib/x86_64-linux-gnu/libvlccore.so*:.")
    fi
    ;;
esac

pyinstaller "${ARGS[@]}"
echo "Exécutable : dist/VLCPlayer"
