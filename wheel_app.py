# -*- coding: utf-8 -*-
"""幸运大转盘 - 桌面版 (tkinter + PyInstaller) 高分屏优化版"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import json
import os
import math
import random
import threading
import sys
import time
from datetime import datetime

# ---------- 高分屏 DPI 支持（仅 Windows，必须在创建窗口前启用） ----------
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

if IS_WIN:
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 按显示器 DPI 感知
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass

if IS_WIN:
    try:
        import winsound
    except ImportError:
        winsound = None
else:
    winsound = None  # macOS / Linux 用系统提示音替代

# ---------- 常量 ----------
COLORS = ["#ff5f5f", "#ff9f43", "#3d8bfd", "#9b6bf3"]  # 红 橙 蓝 紫（更亮）
GREY = "#b3b3c2"
GREY_TEXT = "#6f6f84"
MAX_PRIZES = 20
if IS_WIN:
    FONT = "Microsoft YaHei"
    UI_FONT = "Segoe UI"
elif IS_MAC:
    FONT = "PingFang SC"
    UI_FONT = "Helvetica Neue"
else:
    FONT = "Noto Sans CJK SC"
    UI_FONT = "DejaVu Sans"

BG = "#150430"        # 背景深紫
BG2 = "#1d0840"       # 卡片底色
PANEL = "#26104e"     # 面板
PANEL_BORDER = "#4b2c85"
GOLD = "#ffd54a"
GOLD_DEEP = "#e8a91c"
TEXT = "#f7f0ff"
MUTED = "#a893c9"
ROW_ALT = "#221048"

DEFAULT_PRIZES = [
    {"name": "小CK", "weight": 10, "won": False},
    {"name": "写1000个我爱你", "weight": 10, "won": False},
    {"name": "无条件原谅", "weight": 10, "won": False},
    {"name": "夸我35个词不重样", "weight": 10, "won": False},
    {"name": "一顿火锅", "weight": 10, "won": False},
    {"name": "带我去美甲", "weight": 10, "won": False},
    {"name": "TF80", "weight": 10, "won": False},
    {"name": "带我吃饭", "weight": 10, "won": False},
    {"name": "Colourpop眼影", "weight": 10, "won": False},
    {"name": "阿玛尼红管201", "weight": 10, "won": False},
    {"name": "巴宝莉93", "weight": 10, "won": False},
    {"name": "跪搓衣板", "weight": 10, "won": False},
]


def app_dir():
    """返回配置/截图保存目录。

    Windows 打包版：exe 所在目录；
    macOS .app：~/Library/Application Support/LuckyWheel（不能写进 .app 包内）；
    脚本运行：脚本所在目录。
    """
    if getattr(sys, "frozen", False):
        if IS_MAC:
            base = os.path.expanduser(
                "~/Library/Application Support/LuckyWheel")
            try:
                os.makedirs(base, exist_ok=True)
            except Exception:
                pass
            return base
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    """返回打包资源（--add-data）或脚本旁资源的路径。"""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def load_data():
    path = os.path.join(app_dir(), "wheel_config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        prizes = data.get("prizes") or [dict(p) for p in DEFAULT_PRIZES]
        history = data.get("history", []) or []
        sound_on = data.get("sound_on", True)
    except Exception:
        prizes = [dict(p) for p in DEFAULT_PRIZES]
        history = []
        sound_on = True
    return prizes, history, sound_on


def save_data(prizes, history, sound_on):
    path = os.path.join(app_dir(), "wheel_config.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"prizes": prizes, "history": history[-50:], "sound_on": sound_on},
                f, ensure_ascii=False, indent=2,
            )
    except Exception:
        pass


def lerp_color(c1, c2, t):
    """十六进制颜色插值：t=0 返回 c1，t=1 返回 c2。"""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class WheelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("幸运大转盘")

        self.scale = self._detect_scale()
        S = self.scale
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(int(1280 * S), sw - 40)
        h = min(int(940 * S), sh - 50)
        self.win_w = w
        self.root.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2)}")
        self.root.minsize(int(980 * S), int(720 * S))
        self.root.configure(bg=BG)

        # 转盘尺寸：随窗口高度自适应（高分屏下更清晰更大）
        self.size = max(int(380 * S), min(int(560 * S), h - int(390 * S)))

        self.prizes, self.history, self.sound_on = load_data()
        self.rotation = 0.0  # 度，顺时针为正
        self.spinning = False
        self._spin_job = None
        self._last_idx = -1

        self._style_ttk()
        self._build_ui()
        self._draw_wheel()

        # 窗口/任务栏图标（Windows 用 ico；macOS 由 .app 的 icns 自动显示）
        if IS_WIN:
            try:
                self.root.iconbitmap(default=resource_path("icon-tile.ico"))
            except Exception:
                pass

        self.root.bind("<space>", self._on_space)
        self.root.bind("<F8>", lambda e: self._toggle_odds())

    def _detect_scale(self):
        try:
            dpi = self.root.winfo_fpixels("1i")
            return min(3.0, max(1.0, dpi / 96.0))
        except Exception:
            return 1.0

    def px(self, v):
        """逻辑像素 → 物理像素"""
        return int(v * self.scale)

    def _style_ttk(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("LW.Vertical.TScrollbar",
                        troughcolor="#180736", background=PANEL_BORDER,
                        bordercolor=PANEL, arrowcolor=MUTED, relief="flat")
        style.map("LW.Vertical.TScrollbar", background=[("active", GOLD_DEEP)])
        style.configure("LW.Horizontal.TScale",
                        troughcolor="#180736", background=GOLD,
                        bordercolor=PANEL, lightcolor=GOLD, darkcolor=GOLD_DEEP,
                        gripcount=0, relief="flat")

    # ---------------- UI ----------------
    def _build_ui(self):
        # 顶部栏：标题 + 右上角声音按钮
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=self.px(28), pady=(self.px(16), self.px(4)))

        tbox = tk.Frame(top, bg=BG)
        tbox.pack(side="left")
        tk.Label(tbox, text="幸 运 大 转 盘", font=(FONT, 28, "bold"),
                 bg=BG, fg=GOLD).pack(anchor="w")
        tk.Label(tbox, text="L U C K Y   W H E E L", font=(UI_FONT, 9, "bold"),
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(2, 0))

        self.sound_btn = self._make_topbtn(top, "🔊", self._toggle_sound)
        self.sound_btn.pack(side="right")

        # 中部：左侧转盘区 + 右侧操作栏
        mid = tk.Frame(self.root, bg=BG)
        mid.pack(fill="both", expand=True)

        right = tk.Frame(mid, bg=BG, width=self.px(268))
        right.pack(side="right", fill="y",
                   padx=(self.px(4), self.px(22)), pady=(self.px(10), self.px(4)))
        right.pack_propagate(False)

        left = tk.Frame(mid, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        # 结果显示卡片（转盘上方）
        card = tk.Frame(left, bg=BG2, highlightbackground=PANEL_BORDER,
                        highlightthickness=1)
        card.pack(pady=(self.px(8), self.px(4)), ipadx=self.px(34), ipady=self.px(6))
        self.result_label = tk.Label(card, text="本轮结果", font=(FONT, 11),
                                     bg=BG2, fg=MUTED)
        self.result_label.pack()
        self.result_name = tk.Label(card, text="？？？", font=(FONT, 34, "bold"),
                                    bg=BG2, fg="white")
        self.result_name.pack()

        # 转盘
        wrap = tk.Frame(left, bg=BG)
        wrap.pack(expand=True)
        self.canvas = tk.Canvas(wrap, width=self.size, height=self.size,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.tag_bind("hub", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("hub", "<Leave>", lambda e: self.canvas.config(cursor=""))

        # 右侧操作按钮：奖项设置 → 清除中奖记录（重置奖项+清空记录）→ 保存中奖记录截图
        for text, cmd in (("⚙ 奖项设置", self._open_settings),
                          ("🗑 清除中奖记录", self._clear_all),
                          ("📷 保存中奖记录截图", self._save_history_shot)):
            b = self._make_topbtn(right, text, cmd)
            b.pack(fill="x", pady=(0, self.px(10)))

        # 中奖利率面板（默认隐藏，按 F8 切换）
        self.odds_visible = False
        self.odds_panel = self._make_panel(right, "中奖利率")
        odds_list = tk.Frame(self.odds_panel.body, bg=PANEL)
        odds_list.pack(fill="both", expand=True)
        odds_canvas = tk.Canvas(odds_list, bg=PANEL, highlightthickness=0,
                                height=self.px(300))
        sb = ttk.Scrollbar(odds_list, orient="vertical", command=odds_canvas.yview,
                           style="LW.Vertical.TScrollbar")
        self._odds_inner = tk.Frame(odds_canvas, bg=PANEL)
        self._odds_inner.bind(
            "<Configure>",
            lambda e: odds_canvas.configure(scrollregion=odds_canvas.bbox("all")))
        odds_canvas.create_window((0, 0), window=self._odds_inner, anchor="nw",
                                  width=self.px(226))
        odds_canvas.configure(yscrollcommand=sb.set)
        odds_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 中奖记录（右侧栏底部）
        self.hist_panel = self._make_panel(right, "中奖记录")
        self.hist_panel.pack(side="bottom", fill="x")
        self.history_list = tk.Frame(self.hist_panel.body, bg=PANEL, height=self.px(240))
        self.history_list.pack(fill="x")
        self.history_list.pack_propagate(False)
        self._render_history_into(self.history_list)

    def _make_topbtn(self, parent, text, cmd):
        b = tk.Button(parent, text=text, font=(FONT, 11), bg=PANEL, fg=TEXT,
                      activebackground="#3a1c6e", activeforeground=GOLD,
                      relief="flat", bd=0, padx=self.px(16), pady=self.px(8),
                      cursor="hand2", command=cmd, highlightthickness=0)
        b.bind("<Enter>", lambda e: b.config(bg="#3a1c6e"))
        b.bind("<Leave>", lambda e: b.config(bg=PANEL))
        return b

    def _make_panel(self, parent, title):
        outer = tk.Frame(parent, bg=PANEL_BORDER, bd=0)
        inner = tk.Frame(outer, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        head = tk.Frame(inner, bg=PANEL)
        head.pack(fill="x", padx=12, pady=(10, 6))
        tk.Frame(head, bg=GOLD, width=4).pack(side="left", fill="y", padx=(0, 8))
        tk.Label(head, text=title, font=(FONT, 13, "bold"),
                 bg=PANEL, fg=TEXT).pack(side="left")
        body = tk.Frame(inner, bg=PANEL)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        outer.body = body
        return outer

    def _make_btn(self, parent, text, cmd):
        b = tk.Button(parent, text=text, font=(FONT, 10), bg=BG2, fg=TEXT,
                      activebackground=PANEL_BORDER, activeforeground=GOLD,
                      relief="flat", bd=0, cursor="hand2", command=cmd,
                      highlightthickness=0, pady=self.px(5))
        b.bind("<Enter>", lambda e: b.config(bg=PANEL_BORDER))
        b.bind("<Leave>", lambda e: b.config(bg=BG2))
        return b

    # ---------------- 转盘绘制 ----------------
    def _draw_wheel(self):
        c = self.canvas
        c.delete("all")
        size = self.size
        cx = cy = size / 2
        outer_r = size / 2 - self.px(6)
        ring = self.px(22)
        wheel_r = outer_r - ring
        hub_r = size * 0.155

        # 背景光晕（同心圆渐变，外圈融入背景）
        glow_max = size / 2 + self.px(26)
        steps = 14
        for k in range(steps, 0, -1):
            t = k / steps
            r = wheel_r + (glow_max - wheel_r) * t
            col = lerp_color("#3d2380", BG, t)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")

        # 底座环
        c.create_oval(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r,
                      fill="#2b1a52", outline=GOLD_DEEP, width=self.px(2))

        # 灯泡圈（旋转时交替闪烁）
        n_bulbs = 28
        bulb_orbit = wheel_r + ring / 2
        bulb_r = max(3, ring * 0.24)
        phase = int(time.time() * 8) % 2 if self.spinning else 0
        for b in range(n_bulbs):
            a = math.radians(360.0 * b / n_bulbs)
            bx = cx + bulb_orbit * math.cos(a)
            by = cy + bulb_orbit * math.sin(a)
            col = "#ffe9a3" if (b + phase) % 2 == 0 else "#6e5a40"
            c.create_oval(bx - bulb_r, by - bulb_r, bx + bulb_r, by + bulb_r,
                          fill=col, outline="")

        n = max(2, len(self.prizes))
        seg = 360.0 / n

        for i in range(n):
            item = self.prizes[i]
            # 扇区中心线方向 = 90 - i*seg - rotation（文字、指针、中奖判定共用此公式）
            center = 90 - i * seg - self.rotation
            start = center + seg / 2  # create_arc 自 start 顺时针扫过 seg
            extent = -seg

            bbox = (cx - wheel_r, cy - wheel_r, cx + wheel_r, cy + wheel_r)
            color = GREY if item["won"] else COLORS[i % len(COLORS)]
            c.create_arc(bbox, start=start, extent=extent, style="pieslice",
                         fill=color, outline="white", width=self.px(2))

            # 扇区文字
            self._draw_sector_text(cx, cy, wheel_r, center, item, hub_r)

        # 中心白色轴 + 金环
        c.create_oval(cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r,
                      fill="#ffffff", outline=GOLD_DEEP, width=self.px(3), tags="hub")
        inner = hub_r * 0.62
        c.create_oval(cx - inner, cy - inner, cx + inner, cy + inner,
                      outline="#e6e1ef", width=self.px(4), tags="hub")
        c.create_text(cx, cy, text="GO", font=(UI_FONT, int(size * 0.045), "bold"),
                      fill="#8a8a9c", tags="hub")

        # 顶部指针（金色 + 阴影）
        tip_y = cy - wheel_r - self.px(2)
        base_y = tip_y - self.px(30)
        hw = self.px(15)
        d = self.px(3)
        c.create_polygon([cx + d, tip_y + d, cx - hw + d, base_y + d, cx + hw + d, base_y + d],
                         fill="#1a0b33", outline="")
        c.create_polygon([cx, tip_y, cx - hw, base_y, cx + hw, base_y],
                         fill=GOLD, outline=GOLD_DEEP, width=self.px(1))

    def _draw_sector_text(self, cx, cy, radius, center_deg, item, hub_r):
        alpha = center_deg  # 扇区中心线方向（0=东 90=上，逆时针为正）
        alpha_rad = math.radians(alpha)

        n = len(self.prizes)
        max_chars = 6 if n <= 6 else 5 if n <= 12 else 4 if n <= 14 else 3 if n <= 18 else 2
        s = str(item["name"])
        lines = [s[k:k + max_chars] for k in range(0, len(s), max_chars)][:4]
        if item["won"]:
            lines.append("✓ 已中奖")
        text = "\n".join(lines)

        nl = len(lines)
        fs = max(10, min(18, int(radius * 0.046)))
        if nl > 1:
            fs = min(fs, 15)
        if nl > 3:
            fs = min(fs, 12)

        fnt = tkfont.Font(family=FONT, size=fs, weight="bold")
        max_half = max(fnt.measure(line) for line in lines) / 2

        # 右半圈朝外读、左半圈朝内读，保证所有文字直立可读
        alpha_mod = alpha % 360  # 0=右 90=上 180=左 270=下
        inward = 90 <= alpha_mod <= 270
        angle = (alpha_mod + 180) % 360 if inward else alpha_mod

        # 锚点半径：整段文字保持在轴心与轮缘之间
        inner_lim = hub_r + max_half + self.px(8)
        outer_lim = radius * 0.96 - max_half
        base_r = radius * 0.72
        if inner_lim >= outer_lim:
            base_r = (inner_lim + outer_lim) / 2
        else:
            base_r = min(max(base_r, inner_lim), outer_lim)

        color = GREY_TEXT if item["won"] else "white"
        tx = cx + base_r * math.cos(alpha_rad)
        ty = cy - base_r * math.sin(alpha_rad)
        self.canvas.create_text(tx, ty, text=text, fill=color, angle=angle,
                                font=(FONT, fs, "bold"), justify="center")

    # ---------------- 点击中心 ----------------
    def _on_canvas_click(self, event):
        if self.spinning:
            return
        cx = cy = self.size / 2
        hub_r = self.size * 0.155 + self.px(10)
        dx = event.x - cx
        dy = event.y - cy
        if dx * dx + dy * dy <= hub_r * hub_r:
            self.spin()

    def _on_space(self, e):
        w = self.root.focus_get()
        if isinstance(w, tk.Entry):
            return
        self.spin()

    # ---------------- 抽奖逻辑 ----------------
    def _active_indices(self):
        return [i for i, p in enumerate(self.prizes) if not p["won"] and p["weight"] > 0]

    def _pick_winner(self):
        ids = self._active_indices()
        if not ids:
            return -1
        total = sum(self.prizes[i]["weight"] for i in ids)
        r = random.random() * total
        for i in ids:
            r -= self.prizes[i]["weight"]
            if r < 0:
                return i
        return ids[-1]

    def _pointer_index(self, rot):
        n = len(self.prizes)
        seg = 360.0 / n
        # 顶部(90°)对应扇区 i 满足 90 - i*seg - rot ≈ 90 → i ≈ -rot/seg
        idx = int(((-rot) % 360) // seg) % n
        return idx

    def spin(self):
        if self.spinning:
            return
        winner = self._pick_winner()
        if winner < 0:
            self._set_result("全部抽完啦，点重置再来", win=False, label="提示")
            return

        self.spinning = True
        self._last_idx = self._pointer_index(self.rotation)
        self._set_result(self.prizes[winner]["name"], win=False, label="转动中")

        n = len(self.prizes)
        seg = 360.0 / n
        jitter = (random.random() - 0.5) * seg * 0.6
        # 让 winner 停在顶部：rotation ≡ -winner*seg (mod 360)
        target_mod = ((-winner * seg - jitter) % 360 + 360) % 360
        current_mod = ((self.rotation % 360) + 360) % 360
        delta = (target_mod - current_mod + 360) % 360
        total_rot = 6 * 360 + delta  # 转 6 圈 + 偏移

        start_rot = self.rotation
        end_rot = start_rot + total_rot
        duration = 5200
        t0 = time.time() * 1000

        def ease(t):
            return 1 - (1 - t) ** 4

        def tick_anim():
            now = time.time() * 1000
            t = min(1.0, (now - t0) / duration)
            self.rotation = start_rot + total_rot * ease(t)
            self._draw_wheel()

            idx = self._pointer_index(self.rotation)
            if idx != self._last_idx:
                self._tick_sound()
                self._last_idx = idx

            if t < 1.0:
                self._spin_job = self.root.after(16, tick_anim)
            else:
                self.rotation = end_rot
                self._draw_wheel()
                self._finish_spin(winner)

        self._spin_job = self.root.after(16, tick_anim)

    def _finish_spin(self, winner):
        self.spinning = False
        self.prizes[winner]["won"] = True
        save_data(self.prizes, self.history, self.sound_on)
        if getattr(self, "_prize_inner", None) is not None:
            try:
                self._render_prizes_into(self._prize_inner)
            except tk.TclError:
                self._prize_inner = None
        self._refresh_odds()
        self._draw_wheel()
        name = self.prizes[winner]["name"]
        self._set_result(name, win=True, label="🎉 恭喜抽中")
        self._win_sound()
        self._pulse_result()
        self._confetti()

        t = datetime.now().strftime("%H:%M:%S")
        self.history.insert(0, {"name": name, "time": t})
        if len(self.history) > 50:
            self.history = self.history[:50]
        save_data(self.prizes, self.history, self.sound_on)
        self._render_history_into(self.history_list)

    # ---------------- 结果显示 ----------------
    def _set_result(self, text, win=False, label=None):
        self.result_name.config(text=text)
        self.result_name.config(fg=(GOLD if win else "white"))
        if label:
            self.result_label.config(text=label)

    def _pulse_result(self):
        """中奖后结果文字金色闪烁"""
        def blink(i):
            if i >= 6:
                self.result_name.config(fg=GOLD)
                return
            self.result_name.config(fg=(GOLD if i % 2 == 0 else "#fff3c4"))
            self.root.after(170, lambda: blink(i + 1))
        blink(0)

    def _confetti(self):
        """中奖彩带粒子动画"""
        c = self.canvas
        size = self.size
        colors = COLORS + [GOLD, "#ffffff", "#ff8ab5", "#7dffb8"]
        parts = []
        for _ in range(46):
            parts.append({
                "x": size / 2 + random.uniform(-0.12, 0.12) * size,
                "y": size * 0.16 + random.uniform(-0.03, 0.03) * size,
                "vx": random.uniform(-2.6, 2.6) * self.scale,
                "vy": random.uniform(-7.5, -3.0) * self.scale,
                "r": random.uniform(2.5, 5.5) * self.scale,
                "col": random.choice(colors),
                "shape": random.choice(["o", "r"]),
            })
        ids = []
        for p in parts:
            if p["shape"] == "o":
                ids.append(c.create_oval(p["x"] - p["r"], p["y"] - p["r"],
                                         p["x"] + p["r"], p["y"] + p["r"],
                                         fill=p["col"], outline="", tags="confetti"))
            else:
                ids.append(c.create_rectangle(p["x"] - p["r"], p["y"] - p["r"] * 0.6,
                                              p["x"] + p["r"], p["y"] + p["r"] * 0.6,
                                              fill=p["col"], outline="", tags="confetti"))
        g = 0.22 * self.scale

        def step(t=0):
            if t >= 110:
                c.delete("confetti")
                return
            try:
                for p in parts:
                    p["vy"] += g
                    p["x"] += p["vx"]
                    p["y"] += p["vy"]
                for pid, p in zip(ids, parts):
                    if p["shape"] == "o":
                        c.coords(pid, p["x"] - p["r"], p["y"] - p["r"],
                                 p["x"] + p["r"], p["y"] + p["r"])
                    else:
                        c.coords(pid, p["x"] - p["r"], p["y"] - p["r"] * 0.6,
                                 p["x"] + p["r"], p["y"] + p["r"] * 0.6)
            except tk.TclError:
                return
            self.root.after(16, lambda: step(t + 1))

        step()

    # ---------------- 音效 ----------------
    def _beep(self, freq, dur):
        if not self.sound_on:
            return
        if IS_WIN and winsound is not None:
            try:
                threading.Thread(target=winsound.Beep, args=(freq, dur), daemon=True).start()
            except Exception:
                pass
        else:
            # macOS / Linux：系统提示音
            try:
                self.root.bell()
            except Exception:
                pass

    def _tick_sound(self):
        # Windows 转动滴答声；macOS 系统提示音较长，转动时不播放避免堆叠噪音
        if IS_WIN:
            self._beep(880, 40)

    def _win_sound(self):
        if not self.sound_on:
            return
        if IS_WIN:
            seq = [523, 659, 784, 1047]
            for i, f in enumerate(seq):
                self.root.after(i * 130, lambda f=f: self._beep(f, 180))
        else:
            self.root.after(80, lambda: self._beep(0, 0))

    def _toggle_sound(self):
        self.sound_on = not self.sound_on
        self.sound_btn.config(text="🔊" if self.sound_on else "🔇")
        save_data(self.prizes, self.history, self.sound_on)

    # ---------------- 设置弹窗 ----------------
    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("奖项设置")
        w, h = int(440 * self.scale), int(620 * self.scale)
        win.minsize(int(400 * self.scale), int(500 * self.scale))
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()
        # 弹窗居中于主窗口
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        container = tk.Frame(win, bg=BG)
        container.pack(fill="both", expand=True, padx=self.px(14), pady=self.px(14))

        # 奖项设置面板
        prize_panel = self._make_panel(container, "奖项设置（最多 20 个）")
        prize_panel.pack(fill="both", expand=True)

        prize_list = tk.Frame(prize_panel.body, bg=PANEL)
        prize_list.pack(fill="both", expand=True)

        prize_canvas = tk.Canvas(prize_list, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(prize_list, orient="vertical", command=prize_canvas.yview,
                           style="LW.Vertical.TScrollbar")
        prize_inner = tk.Frame(prize_canvas, bg=PANEL)
        prize_inner.bind("<Configure>",
                         lambda e: prize_canvas.configure(scrollregion=prize_canvas.bbox("all")))
        prize_canvas.create_window((0, 0), window=prize_inner, anchor="nw",
                                   width=int(392 * self.scale))
        prize_canvas.configure(yscrollcommand=sb.set)
        prize_canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def _on_wheel(e):
            prize_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        prize_canvas.bind_all("<MouseWheel>", _on_wheel)

        def _cleanup(e):
            if e.widget is win:
                self._prize_inner = None  # 弹窗已销毁，清除引用
                try:
                    prize_canvas.unbind_all("<MouseWheel>")
                except Exception:
                    pass
        win.bind("<Destroy>", _cleanup)

        # 保存引用供 render_prizes 使用
        self._prize_inner = prize_inner
        self._render_prizes_into(prize_inner)

        pbtn = tk.Frame(prize_panel.body, bg=PANEL)
        pbtn.pack(fill="x", pady=(self.px(8), 0))
        self._make_btn(pbtn, "＋ 添加奖项", self._add_prize).pack(
            side="left", fill="x", expand=True, padx=(0, self.px(3)))
        self._make_btn(pbtn, "↺ 重置中奖", self._reset_won).pack(
            side="left", fill="x", expand=True, padx=(self.px(3), 0))
        tk.Label(prize_panel.body, bg=PANEL, fg=MUTED, font=(FONT, 9),
                 text="抽中后自动变灰且不会重复。",
                 wraplength=self.px(380), justify="left").pack(anchor="w", pady=(self.px(6), 0))

    # ---------------- 奖项编辑 ----------------
    def _render_prizes_into(self, container):
        for w in container.winfo_children():
            w.destroy()

        for i, item in enumerate(self.prizes):
            row = tk.Frame(container, bg=PANEL, highlightthickness=1,
                           highlightbackground=PANEL_BORDER)
            row.pack(fill="x", pady=self.px(3), padx=self.px(2))

            top = tk.Frame(row, bg=PANEL)
            top.pack(fill="x", padx=self.px(6), pady=self.px(4))

            dot = tk.Label(top, width=2, bg=GREY if item["won"] else COLORS[i % len(COLORS)])
            dot.pack(side="left", padx=(0, self.px(6)))

            ent = tk.Entry(top, font=(FONT, 11), bg="#180736", fg=TEXT,
                           insertbackground=TEXT, relief="flat",
                           highlightthickness=1, highlightbackground=PANEL_BORDER,
                           highlightcolor=GOLD_DEEP)
            ent.insert(0, item["name"])
            ent.pack(side="left", fill="x", expand=True)

            def on_edit(e, idx=i, e2=ent):
                self.prizes[idx]["name"] = e2.get().strip() or "未命名"
                save_data(self.prizes, self.history, self.sound_on)
                self._draw_wheel()
                self._refresh_odds()
            ent.bind("<KeyRelease>", on_edit)
            ent.bind("<FocusOut>", on_edit)

            del_btn = tk.Button(top, text="✕", font=(UI_FONT, 10), bg=PANEL,
                                fg="#ff8aa0", activebackground=PANEL,
                                activeforeground="#ff4d6d",
                                relief="flat", bd=0, cursor="hand2",
                                command=lambda idx=i: self._del_prize(idx))
            del_btn.pack(side="right", padx=(self.px(4), 0))
            del_btn.bind("<Enter>", lambda e, b=del_btn: b.config(fg="#ff4d6d"))
            del_btn.bind("<Leave>", lambda e, b=del_btn: b.config(fg="#ff8aa0"))

            if item["won"]:
                tk.Label(row, text="✓ 已中奖，不再参与抽奖", font=(FONT, 9),
                         bg=PANEL, fg="#74dca0").pack(anchor="w", padx=self.px(8),
                                                      pady=(0, self.px(4)))

    def _update_pct(self, val_lbl, pct_lbl, weight, total):
        if val_lbl is not None:
            val_lbl.config(text=str(weight))
        pct = (weight / total * 100) if total > 0 else 0
        if pct_lbl is not None:
            pct_lbl.config(text=f"{pct:.1f}%")

    def _on_weight(self, idx, val):
        try:
            v = max(0, min(100, int(round(float(val)))))
        except Exception:
            return
        self.prizes[idx]["weight"] = v
        # 防抖：拖动结束后再写盘
        if getattr(self, "_wsave_job", None):
            try:
                self.root.after_cancel(self._wsave_job)
            except Exception:
                pass
        self._wsave_job = self.root.after(
            400, lambda: save_data(self.prizes, self.history, self.sound_on))
        self._refresh_pct_labels()

    def _refresh_pct_labels(self):
        total = sum(p["weight"] for p in self.prizes if not p["won"])
        for inner in (getattr(self, "_odds_inner", None),
                      getattr(self, "_prize_inner", None)):
            if inner is None:
                continue
            try:
                children = inner.winfo_children()
            except tk.TclError:
                continue
            for i, row in enumerate(children):
                vl = getattr(row, "_val_lbl", None)
                pl = getattr(row, "_pct_lbl", None)
                if vl is not None and pl is not None and i < len(self.prizes) \
                        and not self.prizes[i]["won"]:
                    self._update_pct(vl, pl, self.prizes[i]["weight"], total)

    # ---------------- 中奖利率面板（F8 切换） ----------------
    def _toggle_odds(self):
        if self.odds_visible:
            self.odds_panel.pack_forget()
            self.odds_visible = False
        else:
            self._refresh_odds()
            self.odds_panel.pack(fill="both", expand=True)
            self.odds_visible = True

    def _refresh_odds(self):
        inner = getattr(self, "_odds_inner", None)
        if inner is None:
            return
        try:
            self._render_odds_into(inner)
        except tk.TclError:
            pass

    def _render_odds_into(self, container):
        for w in container.winfo_children():
            w.destroy()
        total = sum(p["weight"] for p in self.prizes if not p["won"])

        for i, item in enumerate(self.prizes):
            row = tk.Frame(container, bg=PANEL, highlightthickness=1,
                           highlightbackground=PANEL_BORDER)
            row.pack(fill="x", pady=self.px(2), padx=self.px(1))

            dot = tk.Label(row, width=1, bg=GREY if item["won"] else COLORS[i % len(COLORS)])
            dot.pack(side="left", padx=(self.px(4), 0), pady=self.px(4))

            if item["won"]:
                tk.Label(row, text="✓已中", font=(FONT, 8), bg=PANEL,
                         fg="#74dca0").pack(side="right", padx=self.px(6), pady=self.px(4))
            else:
                pl = tk.Label(row, text="", font=(FONT, 8, "bold"),
                              bg=PANEL, fg=GOLD, width=6)
                pl.pack(side="right", padx=(0, self.px(6)), pady=self.px(4))
                vl = tk.Label(row, text=str(item["weight"]), font=(FONT, 8),
                              bg=PANEL, fg=MUTED, width=2)
                vl.pack(side="right", pady=self.px(4))
                sc = ttk.Scale(row, from_=0, to=100, orient="horizontal",
                               style="LW.Horizontal.TScale", length=self.px(58),
                               command=lambda v, idx=i: self._on_weight(idx, v))
                sc.set(item["weight"])
                sc.pack(side="right", padx=self.px(2), pady=self.px(4))
                self._update_pct(vl, pl, item["weight"], total)
                row._val_lbl = vl
                row._pct_lbl = pl

            nm = tk.Label(row, text=item["name"], font=(FONT, 9), bg=PANEL,
                          fg=GREY_TEXT if item["won"] else TEXT, anchor="w")
            nm.pack(side="left", fill="x", expand=True, padx=self.px(4), pady=self.px(4))

    # ---------------- 保存中奖记录截图 ----------------
    def _save_history_shot(self):
        try:
            from PIL import ImageGrab
        except ImportError:
            messagebox.showerror("无法截图", "缺少 Pillow 组件，无法保存截图。")
            return
        try:
            self.root.update_idletasks()
            w = self.hist_panel
            x, y = w.winfo_rootx(), w.winfo_rooty()
            bbox = (x, y, x + w.winfo_width(), y + w.winfo_height())
            img = ImageGrab.grab(bbox=bbox)
            name = "中奖记录_%s.png" % datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(app_dir(), name)
            img.save(path)
            messagebox.showinfo("已保存", "中奖记录截图已保存到：\n" + path)
        except Exception as e:
            messagebox.showerror("截图失败", str(e))

    def _add_prize(self):
        if len(self.prizes) >= MAX_PRIZES:
            messagebox.showinfo("提示", f"最多只能设置 {MAX_PRIZES} 个奖项")
            return
        self.prizes.append({"name": "新奖项", "weight": 10, "won": False})
        save_data(self.prizes, self.history, self.sound_on)
        if getattr(self, "_prize_inner", None) is not None:
            self._render_prizes_into(self._prize_inner)
        self._refresh_odds()
        self._draw_wheel()

    def _del_prize(self, idx):
        if len(self.prizes) <= 2:
            messagebox.showinfo("提示", "至少保留 2 个奖项")
            return
        del self.prizes[idx]
        save_data(self.prizes, self.history, self.sound_on)
        if getattr(self, "_prize_inner", None) is not None:
            self._render_prizes_into(self._prize_inner)
        self._refresh_odds()
        self._draw_wheel()

    def _reset_won(self):
        if not any(p["won"] for p in self.prizes):
            messagebox.showinfo("提示", "当前还没有已中奖的奖项")
            return
        if not messagebox.askyesno("确认", "重置后所有奖项恢复可抽，确定继续？"):
            return
        for p in self.prizes:
            p["won"] = False
        save_data(self.prizes, self.history, self.sound_on)
        if getattr(self, "_prize_inner", None) is not None:
            self._render_prizes_into(self._prize_inner)
        self._refresh_odds()
        self._draw_wheel()
        self._set_result("？？？", win=False, label="本轮结果")

    # ---------------- 记录 ----------------
    def _render_history_into(self, container):
        for w in container.winfo_children():
            w.destroy()
        if not self.history:
            tk.Label(container, text="还没有抽奖记录，点击转盘中心 GO 开始",
                     font=(FONT, 10), bg=PANEL, fg=MUTED).pack(expand=True)
            return
        color_map = {}
        for i, p in enumerate(self.prizes):
            color_map.setdefault(p["name"], COLORS[i % len(COLORS)])
        n_show = max(2, int(self.px(240) / self.px(24)))
        for ri, h in enumerate(self.history[:n_show]):
            line = tk.Frame(container, bg=(PANEL if ri % 2 == 0 else ROW_ALT))
            line.pack(fill="x")
            tk.Label(line, text="●", font=(UI_FONT, 8),
                     bg=line["bg"], fg=color_map.get(h["name"], GOLD)).pack(
                side="left", padx=(10, 6))
            tk.Label(line, text=h["name"], font=(FONT, 10, "bold"),
                     bg=line["bg"], fg=GOLD, anchor="w").pack(side="left")
            tk.Label(line, text=h["time"], font=(FONT, 9),
                     bg=line["bg"], fg=MUTED).pack(side="right", padx=10)

    def _clear_all(self):
        """清除中奖记录：同时重置所有奖项为可抽并清空记录。"""
        has_won = any(p["won"] for p in self.prizes)
        if not has_won and not self.history:
            messagebox.showinfo("提示", "当前没有中奖记录")
            return
        if not messagebox.askyesno("确认", "将清除全部中奖记录，并重置所有奖项为可抽，确定继续？"):
            return
        for p in self.prizes:
            p["won"] = False
        self.history = []
        save_data(self.prizes, self.history, self.sound_on)
        if getattr(self, "_prize_inner", None) is not None:
            self._render_prizes_into(self._prize_inner)
        self._refresh_odds()
        self._draw_wheel()
        self._render_history_into(self.history_list)
        self._set_result("？？？", win=False, label="本轮结果")


def main():
    root = tk.Tk()
    app = WheelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
