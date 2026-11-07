"""A small macOS global keyboard counter with a visual keyboard heatmap."""

from __future__ import annotations

import tkinter as tk
from collections import Counter
from threading import Lock
from typing import Any

try:
    from pynput import keyboard
except ImportError as exc:
    raise SystemExit("缺少依赖，请运行：python3 -m pip install pynput") from exc


BG = "#f3f5f8"
KEY_BG = "#ffffff"
INK = "#263244"
MUTED = "#718096"
ACCENT = "#3978f6"


class KeyboardCounterApp:
    # Each key is (display name, x position, width), in keyboard key units.
    ROWS = [
        [("Esc", 0, 1), ("1", 1.25, 1), ("2", 2.25, 1), ("3", 3.25, 1), ("4", 4.25, 1), ("5", 5.25, 1), ("6", 6.25, 1), ("7", 7.25, 1), ("8", 8.25, 1), ("9", 9.25, 1), ("0", 10.25, 1), ("-", 11.25, 1), ("=", 12.25, 1), ("删除", 13.25, 1.75)],
        [("Tab", 0, 1.5), ("Q", 1.75, 1), ("W", 2.75, 1), ("E", 3.75, 1), ("R", 4.75, 1), ("T", 5.75, 1), ("Y", 6.75, 1), ("U", 7.75, 1), ("I", 8.75, 1), ("O", 9.75, 1), ("P", 10.75, 1), ("[", 11.75, 1), ("]", 12.75, 1), ("\\", 13.75, 1.25)],
        [("Caps Lock", 0, 1.85), ("A", 2.1, 1), ("S", 3.1, 1), ("D", 4.1, 1), ("F", 5.1, 1), ("G", 6.1, 1), ("H", 7.1, 1), ("J", 8.1, 1), ("K", 9.1, 1), ("L", 10.1, 1), (";", 11.1, 1), ("'", 12.1, 1), ("回车", 13.1, 1.9)],
        [("左 Shift", 0, 2.35), ("Z", 2.6, 1), ("X", 3.6, 1), ("C", 4.6, 1), ("V", 5.6, 1), ("B", 6.6, 1), ("N", 7.6, 1), ("M", 8.6, 1), (",", 9.6, 1), (".", 10.6, 1), ("/", 11.6, 1), ("右 Shift", 12.6, 2.4)],
        [("fn", 0, 1), ("左 Control", 1, 1), ("左 Option", 2, 1), ("左 Command", 3, 1.25), ("空格", 4.3, 5.7), ("右 Command", 10.1, 1.25), ("右 Option", 11.35, 1), ("←", 12.45, 1), ("↑", 13.45, 1), ("↓", 14.45, 1)],
    ]

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("键盘统计")
        self.root.geometry("1040x720")
        self.root.minsize(860, 650)
        self.root.configure(bg=BG)
        self.counts: Counter[str] = Counter()
        self.down: set[Any] = set()
        self.lock = Lock()
        self.running = True
        self.key_widgets: dict[str, tuple[tk.Frame, tk.Label, tk.Label]] = {}

        header = tk.Frame(root, bg=BG)
        header.pack(fill=tk.X, padx=32, pady=(24, 10))
        tk.Label(header, text="键盘使用热力图", bg=BG, fg=INK, font=("Helvetica Neue", 25, "bold")).pack(anchor="w")
        tk.Label(header, text="每次按下计一次 · 长按不重复 · 仅在本次运行中统计", bg=BG, fg=MUTED, font=("Helvetica Neue", 11)).pack(anchor="w", pady=(4, 0))

        toolbar = tk.Frame(root, bg=BG)
        toolbar.pack(fill=tk.X, padx=32, pady=(8, 14))
        self.total_var = tk.StringVar(value="0")
        tk.Label(toolbar, textvariable=self.total_var, bg=BG, fg=INK, font=("Helvetica Neue", 27, "bold")).pack(side=tk.LEFT)
        tk.Label(toolbar, text="次按键", bg=BG, fg=MUTED, font=("Helvetica Neue", 12)).pack(side=tk.LEFT, padx=(8, 0), pady=(10, 0))
        self.toggle_button = tk.Button(toolbar, text="暂停统计", command=self.toggle, relief=tk.FLAT, bg="#e7edf7", fg=INK, activebackground="#dbe5f3", padx=16, pady=8, font=("Helvetica Neue", 11, "bold"), cursor="hand2")
        self.toggle_button.pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(toolbar, text="清零", command=self.reset, relief=tk.FLAT, bg="#ffffff", fg=INK, activebackground="#edf1f7", padx=18, pady=8, font=("Helvetica Neue", 11), cursor="hand2").pack(side=tk.RIGHT)

        card = tk.Frame(root, bg="#e8edf4", padx=18, pady=20)
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 14))
        self.keyboard_area = tk.Frame(card, bg="#e8edf4")
        self.keyboard_area.pack(expand=True)
        self._build_keyboard()

        footer = tk.Frame(root, bg=BG)
        footer.pack(fill=tk.X, padx=32, pady=(0, 18))
        self.status_var = tk.StringVar(value="正在监听键盘")
        tk.Label(footer, textvariable=self.status_var, bg=BG, fg=MUTED, font=("Helvetica Neue", 10)).pack(side=tk.LEFT)
        tk.Label(footer, text="少  ·  ·  ·  多", bg=BG, fg=MUTED, font=("Helvetica Neue", 10)).pack(side=tk.RIGHT)
        for i, color in enumerate(("#ffffff", "#e8f0ff", "#b7d0ff", "#75a2ff", "#3978f6")):
            tk.Label(footer, bg=color, width=2, height=1, relief=tk.FLAT).pack(side=tk.RIGHT, padx=2)
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        self.root.after(100, self.refresh)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_keyboard(self) -> None:
        for row_index, row in enumerate(self.ROWS):
            for name, x, width in row:
                frame = tk.Frame(self.keyboard_area, bg=KEY_BG, highlightthickness=1, highlightbackground="#d8dee8")
                frame.place(x=x * 51, y=row_index * 76, width=width * 49, height=66)
                title = tk.Label(frame, text=name, bg=KEY_BG, fg=INK, font=("Helvetica Neue", 9, "bold"), anchor="nw")
                title.place(x=7, y=6)
                count = tk.Label(frame, text="", bg=KEY_BG, fg="#2454ad", font=("Helvetica Neue", 10, "bold"), anchor="se")
                count.place(relx=1, rely=1, x=-6, y=-5, anchor="se")
                self.key_widgets[name] = (frame, title, count)
        self.keyboard_area.configure(width=790, height=440)

    @staticmethod
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

    def on_press(self, key: Any) -> None:
        with self.lock:
            if key in self.down:
                return
            self.down.add(key)
            if self.running:
                self.counts[self.key_name(key)] += 1

    def on_release(self, key: Any) -> None:
        with self.lock:
            self.down.discard(key)

    def toggle(self) -> None:
        with self.lock:
            self.running = not self.running
            enabled = self.running
        self.toggle_button.configure(text="暂停统计" if enabled else "继续统计")
        self.status_var.set("正在监听键盘" if enabled else "统计已暂停")

    def reset(self) -> None:
        with self.lock:
            self.counts.clear()
        self.refresh()

    @staticmethod
    def heat_color(count: int, maximum: int) -> str:
        if count == 0 or maximum == 0:
            return KEY_BG
        ratio = count / maximum
        stops = [(0.0, (232, 240, 255)), (0.35, (183, 208, 255)), (0.7, (117, 162, 255)), (1.0, (57, 120, 246))]
        for i in range(1, len(stops)):
            if ratio <= stops[i][0]:
                left, right = stops[i - 1], stops[i]
                t = (ratio - left[0]) / (right[0] - left[0])
                rgb = tuple(round(a + (b - a) * t) for a, b in zip(left[1], right[1]))
                return "#%02x%02x%02x" % rgb
        return "#3978f6"

    def refresh(self) -> None:
        with self.lock:
            counts = self.counts.copy()
        self.total_var.set(f"{sum(counts.values()):,}")
        maximum = max(counts.values(), default=0)
        for name, (frame, title, value) in self.key_widgets.items():
            count = counts.get(name, 0)
            color = self.heat_color(count, maximum)
            foreground = "#ffffff" if count and count / maximum > 0.72 else INK
            frame.configure(bg=color)
            title.configure(bg=color, fg=foreground)
            value.configure(bg=color, fg=foreground, text=f"{count:,}" if count else "")
        if self.root.winfo_exists():
            self.root.after(250, self.refresh)

    def close(self) -> None:
        self.listener.stop()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    KeyboardCounterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
