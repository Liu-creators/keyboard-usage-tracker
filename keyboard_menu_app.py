"""Menu bar keyboard tracker using the existing pynput counting rules."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from pathlib import Path
from threading import Lock
from typing import Any

import rumps
from pynput import keyboard


DB_PATH = Path.home() / "Library/Application Support/KeyboardUsageTracker/keyboard_usage.sqlite3"


def key_name(key: Any) -> str:
    if isinstance(key, keyboard.KeyCode):
        value = key.char
        if value is None:
            return "未知"
        if value == " ":
            return "空格"
        return value.upper() if value.isalpha() else value
    names = {
        keyboard.Key.ctrl: "Control", keyboard.Key.ctrl_l: "左 Control", keyboard.Key.ctrl_r: "右 Control",
        keyboard.Key.shift: "Shift", keyboard.Key.shift_l: "左 Shift", keyboard.Key.shift_r: "右 Shift",
        keyboard.Key.alt: "Option", keyboard.Key.alt_l: "左 Option", keyboard.Key.alt_r: "右 Option",
        keyboard.Key.cmd: "Command", keyboard.Key.cmd_l: "左 Command", keyboard.Key.cmd_r: "右 Command",
        keyboard.Key.enter: "回车", keyboard.Key.tab: "Tab", keyboard.Key.space: "空格",
        keyboard.Key.backspace: "删除", keyboard.Key.delete: "向前删除", keyboard.Key.esc: "Esc",
        keyboard.Key.up: "↑", keyboard.Key.down: "↓", keyboard.Key.left: "←", keyboard.Key.right: "→",
        keyboard.Key.caps_lock: "Caps Lock", keyboard.Key.home: "Home", keyboard.Key.end: "End",
        keyboard.Key.page_up: "Page Up", keyboard.Key.page_down: "Page Down",
    }
    return names.get(key, str(key).replace("Key.", "").replace("_", " ").title())


class KeyboardTrackerApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("KeyboardUsageTracker", title="⌨️", quit_button=None)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS key_counts (key_name TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        self.db.commit()
        self.lock = Lock()
        self.down: set[Any] = set()
        self.running = True
        self.status_item = rumps.MenuItem("统计状态：运行中")
        self.total_item = rumps.MenuItem("累计按键次数：0")
        self.pause_item = rumps.MenuItem("暂停统计", callback=self.toggle_pause)
        self.menu = [self.status_item, self.total_item, None, self.pause_item, None,
                     rumps.MenuItem("查看统计数据", callback=self.toggle_window), None,
                     rumps.MenuItem("重置统计", callback=self.reset_counts), None,
                     rumps.MenuItem("退出程序", callback=self.quit_app)]
        self.window = None
        self.key_labels = {}
        self.key_titles = {}
        self._build_window()
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        self.refresh_timer = rumps.Timer(self.refresh, 1)
        self.refresh_timer.start()
        self.refresh(None)

    def _build_window(self) -> None:
        self.window = tk.Tk()
        self.window.title("键盘统计")
        self.window.geometry("780x550")
        self.window.minsize(760, 540)
        self.window.configure(bg="#f3f5f8")
        self.window.withdraw()
        # The heatmap is a child window of the menu bar app; closing it should
        # only hide it and leave the listener and menu bar process running.
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        # MacBook Pro layout: dedicated function row and Touch ID key above
        # the compact ANSI typing block with a separate inverted-T arrow cluster.
        rows = [
            [("Esc", 1), ("F1", 1), ("F2", 1), ("F3", 1), ("F4", 1), ("F5", 1), ("F6", 1), ("F7", 1), ("F8", 1), ("F9", 1), ("F10", 1), ("F11", 1), ("F12", 1), ("Touch ID", 1.3)],
            [("`", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1), ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("删除", 1.8)],
            [("Tab", 1.5), ("Q", 1), ("W", 1), ("E", 1), ("R", 1), ("T", 1), ("Y", 1), ("U", 1), ("I", 1), ("O", 1), ("P", 1), ("[", 1), ("]", 1), ("\\", 1.5)],
            [("Caps Lock", 1.8), ("A", 1), ("S", 1), ("D", 1), ("F", 1), ("G", 1), ("H", 1), ("J", 1), ("K", 1), ("L", 1), (";", 1), ("'", 1), ("回车", 2.2)],
            [("左 Shift", 2.3), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("N", 1), ("M", 1), (",", 1), (".", 1), ("/", 1), ("右 Shift", 2.7)],
            [("fn", 1), ("左 Control", 1.2), ("左 Option", 1.2), ("左 Command", 1.5), ("空格", 6), ("右 Command", 1.5), ("右 Option", 1.2)],
        ]
        unit, gap, key_h = 41, 6, 62
        arrow_w = unit * 3 + gap * 2
        row_widths = [sum(w for _, w in row) * unit + (len(row) - 1) * gap for row in rows]
        layout_w = max(row_widths[:-1] + [row_widths[-1] + arrow_w + gap])
        layout_h = len(rows) * key_h + (len(rows) - 1) * gap
        area = tk.Frame(self.window, bg="#e8edf4", width=layout_w + 20, height=layout_h + 20)
        area.pack(expand=True, padx=10, pady=8)
        area.pack_propagate(False)
        for row_i, keys in enumerate(rows):
            is_bottom = row_i == len(rows) - 1
            available_w = layout_w - (arrow_w + gap if is_bottom else 0)
            key_w_sum = sum(w for _, w in keys) * unit
            row_gap = (available_w - key_w_sum) / max(1, len(keys) - 1)
            x = 14
            y = row_i * (key_h + gap) + 14
            for name, width in keys:
                key_w = width * unit
                cell = tk.Frame(area, bg="#ffffff", highlightthickness=1, highlightbackground="#d5dce8")
                cell.place(x=int(x), y=y, width=int(key_w), height=key_h)
                title_font = 8 if len(name) > 7 else 9
                title = tk.Label(cell, text=name, bg="#ffffff", fg="#263244", font=("Helvetica Neue", title_font, "bold"))
                title.place(x=7, y=7, anchor="nw")
                value = tk.Label(cell, text="", bg="#ffffff", fg="#2454ad", font=("Helvetica Neue", 9, "bold"))
                value.place(relx=1, rely=1, x=-7, y=-6, anchor="se")
                self.key_labels[name] = (cell, value)
                self.key_titles[name] = title
                x += key_w + row_gap

        base = 14 + layout_w - arrow_w
        arrow_y = 14 + (len(rows) - 1) * (key_h + gap)
        for name, col in (("←", 0), ("→", 2)):
            x = base + col * (unit + gap)
            cell = tk.Frame(area, bg="#ffffff", highlightthickness=1, highlightbackground="#d5dce8")
            cell.place(x=int(x), y=arrow_y, width=unit, height=key_h)
            title = tk.Label(cell, text=name, bg="#ffffff", fg="#263244", font=("Helvetica Neue", 11, "bold"))
            title.place(relx=.5, rely=.5, anchor="center")
            value = tk.Label(cell, text="", bg="#ffffff", fg="#2454ad", font=("Helvetica Neue", 8, "bold"))
            value.place(relx=1, rely=1, x=-3, y=-3, anchor="se")
            self.key_labels[name] = (cell, value)
            self.key_titles[name] = title

        # Up/down share one standard keycap and retain separate counts.
        vertical_cell = tk.Frame(area, bg="#ffffff", highlightthickness=1, highlightbackground="#d5dce8")
        vertical_cell.place(x=int(base + unit + gap), y=arrow_y, width=unit, height=key_h)
        divider = tk.Frame(vertical_cell, bg="#d5dce8", height=1)
        divider.place(relx=.18, relwidth=.64, rely=.5, anchor="center")
        for name, rel_y in (("↑", .18), ("↓", .82)):
            title = tk.Label(vertical_cell, text=name, bg="#ffffff", fg="#263244", font=("Helvetica Neue", 9, "bold"))
            title.place(relx=.25, rely=rel_y, anchor="center")
            value = tk.Label(vertical_cell, text="", bg="#ffffff", fg="#2454ad", font=("Helvetica Neue", 7, "bold"))
            value.place(relx=.78, rely=rel_y, anchor="center")
            self.key_labels[name] = (vertical_cell, value)
            self.key_titles[name] = title

    def toggle_window(self, _sender: Any) -> None:
        if self.window.state() == "withdrawn":
            self.window.deiconify()
            self.window.lift()
        else:
            self.window.withdraw()

    def on_press(self, key: Any) -> None:
        with self.lock:
            if key in self.down:
                return
            self.down.add(key)
            if self.running:
                name = key_name(key)
                self.db.execute("INSERT INTO key_counts(key_name,count) VALUES (?,1) ON CONFLICT(key_name) DO UPDATE SET count=count+1", (name,))
                self.db.commit()

    def on_release(self, key: Any) -> None:
        with self.lock:
            self.down.discard(key)

    def refresh(self, _sender: Any) -> None:
        rows = self.db.execute("SELECT key_name,count FROM key_counts").fetchall()
        counts = dict(rows)
        total = sum(counts.values())
        self.total_item.title = f"累计按键次数：{total:,}"
        maximum = max(counts.values(), default=0)
        for name, (cell, value) in self.key_labels.items():
            count = counts.get(name, 0)
            shade_count = max(counts.get("↑", 0), counts.get("↓", 0)) if name in {"↑", "↓"} else count
            ratio = shade_count / maximum if maximum else 0
            color = self.heat_color(ratio)
            foreground = "#ffffff" if ratio >= .72 else "#263244"
            cell.configure(bg=color)
            self.key_titles[name].configure(bg=color, fg=foreground)
            value.configure(bg=color, fg=foreground if ratio >= .72 else "#2454ad", text=f"{count:,}" if count else "")
        try:
            self.window.update()
        except tk.TclError:
            pass

    @staticmethod
    def heat_color(ratio: float) -> str:
        stops = ((0.0, (255, 255, 255)), (0.18, (229, 239, 255)),
                 (0.42, (184, 210, 255)), (0.7, (112, 160, 250)),
                 (1.0, (48, 112, 238)))
        ratio = min(1.0, max(0.0, ratio))
        for index in range(1, len(stops)):
            right_pos, right_rgb = stops[index]
            if ratio <= right_pos:
                left_pos, left_rgb = stops[index - 1]
                t = (ratio - left_pos) / (right_pos - left_pos)
                rgb = tuple(round(a + (b - a) * t) for a, b in zip(left_rgb, right_rgb))
                return "#%02x%02x%02x" % rgb
        return "#3070ee"

    def toggle_pause(self, _sender: Any) -> None:
        self.running = not self.running
        self.status_item.title = "统计状态：已暂停" if not self.running else "统计状态：运行中"
        self.pause_item.title = "恢复统计" if not self.running else "暂停统计"

    def reset_counts(self, _sender: Any) -> None:
        with self.lock:
            self.db.execute("DELETE FROM key_counts")
            self.db.commit()
        self.refresh(None)
        rumps.notification("键盘统计", "统计已重置", "按键计数已清零。")

    def quit_app(self, _sender: Any) -> None:
        self.listener.stop()
        self.refresh_timer.stop()
        try:
            self.window.destroy()
        except tk.TclError:
            pass
        self.db.close()
        rumps.quit_application()


if __name__ == "__main__":
    KeyboardTrackerApp().run()
