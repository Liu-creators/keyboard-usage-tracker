# Keyboard Usage Tracker

A macOS menu bar app that counts physical key presses and visualizes usage on a MacBook keyboard heatmap.

## Features

- Counts each press once and suppresses key-repeat events while a key is held.
- Tracks key names and counts only; it does not record typed text.
- Pause/resume and reset controls in the menu bar.
- Stores counts in SQLite at `~/Library/Application Support/KeyboardUsageTracker/keyboard_usage.sqlite3`.
- Shows or hides the heatmap from the menu bar.

## Run from source

Requires macOS, Python 3.12, and Tk. In the project directory:

```sh
python -m pip install -r requirements.txt
python keyboard_menu_app.py
```

macOS may require granting Accessibility permission to the terminal or packaged app under **System Settings → Privacy & Security → Accessibility**.

## Build the app

```sh
conda activate py312
./build_app.sh
```

The app bundle is created at `dist/KeyboardUsageTracker.app`.

## Legacy UI

`keyboard_counter.py` is the original standalone heatmap app. It keeps its original in-memory counting behavior and is separate from the menu bar app.
