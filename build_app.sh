#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
export PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller-config"
if [[ ! -f KeyboardUsageTracker.icns && -f assets/KeyboardUsageTracker.icns.b64 ]]; then
  base64 -D assets/KeyboardUsageTracker.icns.b64 > KeyboardUsageTracker.icns
fi
python -m PyInstaller --noconfirm KeyboardUsageTracker.spec
echo "Built: $(pwd)/dist/KeyboardUsageTracker.app"
