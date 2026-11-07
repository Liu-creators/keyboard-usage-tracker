#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
export PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller-config"
python -m PyInstaller --noconfirm KeyboardUsageTracker.spec
echo "Built: $(pwd)/dist/KeyboardUsageTracker.app"
