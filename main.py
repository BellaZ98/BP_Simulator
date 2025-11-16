import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from tkinter import simpledialog, messagebox
import json
import random
import os
import platform

try:
    import ctypes
except ImportError:
    ctypes = None

from PIL import Image, ImageTk, ImageDraw, ImageFont

# --- 常量 (全局非缩放) ---
PLACEHOLDER_COLOR = "#a0a0a0"
BG_COLOR = "#f0f0f0"


# --- 新增: 卡组选择器弹出窗口 ---
class DeckSelector(simpledialog.Dialog):
    """一个用于从卡组池中选择卡组的弹出对话框"""

    def __init__(self, parent, title, deck_pool, min_select, max_select, icon_size, font):
        self.deck_pool = deck_pool
        self.min_select = min_select
        self.max_select = max_select
        self.icon_size = icon_size
        self.font = font
        self.selected_decks_info = []
        self.selected_widgets = []
        self.widgets = {}
        self.ok_button = None

        # 修复PIL在Toplevel中的ImageTk.PhotoImage问题
        self.icon_cache = []
        self.max_cols_per_row = 5  # 每行最多5个

        super().__init__(parent, title)

    def body(self, master):
        master.config(bg=BG_COLOR)

        # 提示标签
        self.status_label = tk.Label(master, text=self.get_status_text(), font=self.font, bg=BG_COLOR)
        self.status_label.pack(pady=5)

        # 可滚动的Canvas
        canvas_frame = tk.Frame(master, bd=1, relief="sunken")

        # 【修复1】: 计算合理的Canvas宽度
        canvas_width = (self.icon_size[0] + 10) * self.max_cols_per_row + 10  # 5个图标宽度 + 间距
        canvas_height = self.icon_size[1] * 2.5  # 约2.5行

        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, width=canvas_width, height=canvas_height)

        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        # 【修复1】: 添加水平滚动条
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)

        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", on_configure)

        # 布局
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")  # 【修复1】
        canvas.pack(side="left", fill="both", expand=True)

        # 填充卡组
        col_count = 0
        row = 0
        for deck in self.deck_pool:
            widget = self.create_mini_deck_widget(scrollable_frame, deck)
            widget.grid(row=row, column=col_count, padx=5, pady=5)

            self.widgets[widget] = deck

            handler = lambda e, w=widget: self.toggle_select(w)
            widget.bind("<Button-1>", handler)
            widget.icon_label.bind("<Button-1>", handler)
            widget.name_label.bind("<Button-1>", handler)

            col_count += 1
            if col_count >= self.max_cols_per_row:
                col_count = 0
                row += 1

        return scrollable_frame

    def buttonbox(self):
        box = tk.Frame(self, bg=BG_COLOR)

        self.ok_button = tk.Button(box, text="确认", width=10, command=self.ok, state="disabled", font=self.font)
        self.ok_button.pack(side="left", padx=5, pady=10)
        cancel_button = tk.Button(box, text="取消", width=10, command=self.cancel, font=self.font)
        cancel_button.pack(side="left", padx=5, pady=10)

        box.pack()

        self.bind("<Escape>", self.cancel)

    def toggle_select(self, widget):
        """切换卡组的选择状态"""
        if widget in self.selected_widgets:
            self.selected_widgets.remove(widget)
            widget.config(bg=BG_COLOR, relief="solid", bd=1)
        else:
            if len(self.selected_widgets) < self.max_select:
                self.selected_widgets.append(widget)
                widget.config(bg="#2ECC71", relief="solid", bd=3)
            else:
                self.bell()

        self.update_status()

    def get_status_text(self):
        count = len(self.selected_widgets)
        if self.min_select == self.max_select:
            return f"请选择 {self.min_select} 套卡组 ({count}/{self.min_select})"
        else:
            return f"请选择 {self.min_select} 到 {self.max_select} 套卡组 ({count})"

    def update_status(self):
        self.status_label.config(text=self.get_status_text())

        count = len(self.selected_widgets)
        if self.min_select <= count <= self.max_select:
            self.ok_button.config(state="normal")
        else:
            self.ok_button.config(state="disabled")

    def apply(self):
        """当点击OK时"""
        self.selected_decks_info = [self.widgets[w] for w in self.selected_widgets]

    # --- 迷你卡组创建 (用于弹窗) ---
    def load_mini_icon(self, path):
        try:
            img = Image.open(path).resize(self.icon_size, Image.Resampling.LANCZOS)
        except Exception:
            img = Image.new("RGB", self.icon_size, color=PLACEHOLDER_COLOR)
            draw = ImageDraw.Draw(img)
            draw.text((self.icon_size[0] / 2, self.icon_size[1] / 2), "N/A", fill="white", anchor="mm")

        img_tk = ImageTk.PhotoImage(img)
        self.icon_cache.append(img_tk)
        return img_tk

    def create_mini_deck_widget(self, parent_frame, deck_info):
        widget = tk.Frame(parent_frame, bg=BG_COLOR, relief="solid", bd=1, width=self.icon_size[0],
                          height=self.icon_size[1])
        widget.pack_propagate(False)

        icon_img = self.load_mini_icon(deck_info["icon_path"])
        icon_label = tk.Label(widget, image=icon_img, bd=0)
        icon_label.place(x=0, y=0)

        name_bg = tk.Label(widget, text=deck_info["name"], bg="black", fg="white", font=self.font, padx=5)
        name_bg.place(relx=0.5, rely=1.0, anchor="s", y=-5)

        widget.icon_label = icon_label
        widget.name_label = name_bg
        return widget


# --- 主应用 ---
class DeckBPSimulator(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- 缩放与字体处理 ---
        try:
            self.scaling = self.tk.call('tk', 'scaling')
            if self.scaling > 4: self.scaling = self.scaling / 96.0  # 适配Linux/X11
        except Exception:
            self.scaling = 1.0

        if self.scaling == 1.0 and platform.system() == "Windows" and ctypes:
            try:
                scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
                self.scaling = scale_factor / 100.0
            except Exception:
                self.scaling = 1.0

        self.ICON_WIDTH = int(100 * self.scaling)
        self.ICON_HEIGHT = int(140 * self.scaling)
        self.ICON_SIZE = (self.ICON_WIDTH, self.ICON_HEIGHT)

        self.MATCHUP_ICON_WIDTH = int(30 * self.scaling)
        self.MATCHUP_ICON_HEIGHT = int(42 * self.scaling)
        self.MATCHUP_ICON_SIZE = (self.MATCHUP_ICON_WIDTH, self.MATCHUP_ICON_HEIGHT)

        self.FONT_NAME = "Microsoft YaHei UI"
        self.FONT_FALLBACK = "Arial"

        # 字体缩小
        self.font_size_default = int(5 * self.scaling)  # 6 -> 5
        self.font_size_overlay = int(5 * self.scaling)  # 6 -> 5
        self.font_size_status = int(6 * self.scaling)  # 7 -> 6
        self.font_size_group = int(5 * self.scaling)  # 6 -> 5
        self.font_size_ban_x = int(15 * self.scaling)  # 18 -> 15

        self.DEFAULT_FONT = self.check_font((self.FONT_NAME, self.font_size_default),
                                            (self.FONT_FALLBACK, self.font_size_default))
        self.OVERLAY_FONT = self.check_font((self.FONT_NAME, self.font_size_overlay, "bold"),
                                            (self.FONT_FALLBACK, self.font_size_overlay, "bold"))
        self.STATUS_FONT = self.check_font((self.FONT_NAME, self.font_size_status, "bold"),
                                           (self.FONT_FALLBACK, self.font_size_status, "bold"))
        self.GROUP_FONT = self.check_font((self.FONT_NAME, self.font_size_group, "bold"),
                                          (self.FONT_FALLBACK, self.font_size_group, "bold"))

        self.title("卡组B/P对局模拟器 (v2.2)")  # 版本更新
        self.geometry(f"{int(1300 * self.scaling)}x{int(900 * self.scaling)}")
        self.configure(bg=BG_COLOR)

        # 1. 加载配置
        self.deck_pool = self.load_json("deck_pool.json", "卡组资源池")
        self.my_fixed_decks_info_from_file = self.load_json("my_decks.json", "我方卡组")

        if not self.deck_pool or not self.my_fixed_decks_info_from_file:
            self.quit();
            return

        # 2. 初始化状态变量
        self.matchup_icon_cache = []

        self.opponent_deck_mode = tk.StringVar(value="random")
        self.my_deck_mode = tk.StringVar(value="file")
        self.custom_opponent_ban = tk.BooleanVar(value=False)
        self.custom_opponent_pick = tk.BooleanVar(value=False)
        self.my_decks_changed = tk.BooleanVar(value=False)

        self.game_state = "SETUP"
        self.my_decks_widgets = []
        self.opponent_decks_widgets = []
        self.my_decks_data_current = []
        self.opponent_decks_data = []
        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_widgets = []
        self.opponent_picked_decks_data = []

        # 3. 创建UI
        self.create_widgets()
        self.reset_game()

    def check_font(self, preferred_font, fallback_font):
        try:
            f = tkfont.Font(font=preferred_font)
            if f.actual()["family"].lower() in preferred_font[0].lower():
                return preferred_font
            else:
                return fallback_font
        except:
            return fallback_font

    def load_json(self, filepath, name):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error(f"错误: 未找到配置文件 '{filepath}'。")
            return None
        except json.JSONDecodeError:
            self.show_error(f"错误: 配置文件 '{filepath}' 格式错误。")
            return None

    def show_error(self, message):
        try:
            if self.status_label:
                self.status_label.config(text=message, fg="red")
        except AttributeError:
            error_label = tk.Label(self, text=message, fg="red", bg=BG_COLOR, font=self.STATUS_FONT)
            error_label.pack(pady=50)

    # --- UI 创建 ---
    def create_widgets(self):
        """创建所有UI组件"""

        # 【布局修复】: 随机生成对战按钮移至窗口顶部
        self.generate_matchup_button = tk.Button(self, text="随机生成对战", font=self.DEFAULT_FONT,
                                                 command=self.display_random_matchups, state="disabled")
        # 初始打包 (稍后隐藏)
        self.generate_matchup_button.pack(pady=(int(10 * self.scaling), 0), fill="x", padx=int(20 * self.scaling))
        self.generate_matchup_button.pack_forget()  # 默认隐藏

        # --- 顶部控制面板 (重构) ---
        # 【布局修复】: 保存 control_frame 引用
        self.control_frame = tk.Frame(self, bg=BG_COLOR)
        self.control_frame.pack(pady=int(10 * self.scaling), fill="x", padx=int(20 * self.scaling))

        # 对方卡组选择
        opp_frame = tk.Frame(self.control_frame, bg=BG_COLOR)
        tk.Label(opp_frame, text="对方卡组:", font=self.DEFAULT_FONT, bg=BG_COLOR).pack(side="left", padx=5)
        ttk.Radiobutton(opp_frame, text="随机", variable=self.opponent_deck_mode, value="random",
                        command=self.toggle_opponent_mode).pack(side="left")
        ttk.Radiobutton(opp_frame, text="自定义", variable=self.opponent_deck_mode, value="custom",
                        command=self.toggle_opponent_mode).pack(side="left")

        self.count_slider = ttk.Scale(opp_frame, from_=4, to=6, orient="horizontal", variable=tk.DoubleVar(value=4),
                                      length=100 * self.scaling,
                                      command=lambda v: self.opponent_count_var.set(int(float(v))))
        self.opponent_count_var = tk.IntVar(value=4)
        self.count_slider.config(variable=self.opponent_count_var)
        self.count_slider.pack(side="left", padx=5)

        opp_frame.pack(side="left")

        # 我方卡组选择
        my_frame = tk.Frame(self.control_frame, bg=BG_COLOR)
        tk.Label(my_frame, text="我方卡组:", font=self.DEFAULT_FONT, bg=BG_COLOR).pack(side="left", padx=5)
        ttk.Radiobutton(my_frame, text="默认", variable=self.my_deck_mode, value="file",
                        command=self.toggle_my_deck_mode).pack(side="left")
        ttk.Radiobutton(my_frame, text="自定义", variable=self.my_deck_mode, value="custom",
                        command=self.toggle_my_deck_mode).pack(side="left")

        self.save_my_decks_button = tk.Button(my_frame, text="保存卡组", font=self.DEFAULT_FONT,
                                              command=self.save_my_decks, state="disabled")
        self.save_my_decks_button.pack(side="left", padx=10)

        my_frame.pack(side="left", padx=20)

        # 游戏控制
        game_control_frame = tk.Frame(self.control_frame, bg=BG_COLOR)
        self.generate_button = tk.Button(game_control_frame, text="生成对局", font=self.DEFAULT_FONT,
                                         command=self.start_game_flow)
        self.generate_button.pack(side="left", padx=10)

        # 【新增4】: 撤回按钮
        self.undo_button = tk.Button(game_control_frame, text="撤回", font=self.DEFAULT_FONT, command=self.process_undo,
                                     state="disabled")
        self.undo_button.pack(side="left", padx=5)

        self.reset_button = tk.Button(game_control_frame, text="重置", font=self.DEFAULT_FONT, command=self.reset_game)
        self.reset_button.pack(side="left", padx=5)
        game_control_frame.pack(side="left")

        # 状态/提示信息
        self.status_label = tk.Label(self, text="请设置卡组，然后点击'生成对局'", font=self.STATUS_FONT, bg=BG_COLOR)
        self.status_label.pack(pady=int(10 * self.scaling))

        # 卡组显示区
        decks_frame = tk.Frame(self, bg=BG_COLOR)
        decks_frame.pack(fill="both", expand=True, padx=int(20 * self.scaling))

        # 对方卡组
        self.opponent_frame = tk.LabelFrame(decks_frame, text="对方卡组 (待生成)", font=self.GROUP_FONT, bg=BG_COLOR,
                                            bd=2, relief="groove")
        self.opponent_frame.pack(side="top", fill="x", pady=int(10 * self.scaling))

        self.custom_opponent_pick_check = ttk.Checkbutton(self.opponent_frame, text="手动选择对方出战卡组",
                                                          variable=self.custom_opponent_pick, onvalue=True,
                                                          offvalue=False)
        self.custom_opponent_pick_check.pack(anchor="ne", padx=10)

        self.opponent_decks_container = tk.Frame(self.opponent_frame, bg=BG_COLOR)
        self.opponent_decks_container.pack(pady=int(15 * self.scaling))

        # 我方卡组
        self.my_frame = tk.LabelFrame(decks_frame, text="我方卡组", font=self.GROUP_FONT, bg=BG_COLOR, bd=2,
                                      relief="groove")
        self.my_frame.pack(side="top", fill="x", pady=int(10 * self.scaling))

        self.custom_opponent_ban_check = ttk.Checkbutton(self.my_frame, text="手动选择对方Ban",
                                                         variable=self.custom_opponent_ban, onvalue=True,
                                                         offvalue=False)
        self.custom_opponent_ban_check.pack(anchor="ne", padx=10)

        self.my_decks_container = tk.Frame(self.my_frame, bg=BG_COLOR)
        self.my_decks_container.pack(pady=int(15 * self.scaling))

        # 最终对战表
        self.matchup_frame = tk.LabelFrame(decks_frame, text="最终对战", font=self.GROUP_FONT, bg=BG_COLOR, bd=2,
                                           relief="groove")
        self.matchup_frame.pack(side="top", fill="x", pady=int(10 * self.scaling))

        self.matchup_container = tk.Frame(self.matchup_frame, bg=BG_COLOR)
        self.matchup_container.pack(pady=int(15 * self.scaling), fill="x", expand=True)

    # --- 新增: UI 模式切换 ---
    def toggle_opponent_mode(self):
        if self.opponent_deck_mode.get() == "random":
            self.count_slider.config(state="normal")
            self.status_label.config(text="请设置卡组，然后点击'生成对局'")
        else:  # custom
            self.count_slider.config(state="disabled")
            self.status_label.config(text="请点击'生成对局'按钮以 [自定义] 对方卡组")

    def toggle_my_deck_mode(self):
        if self.my_deck_mode.get() == "file":
            self.my_decks_data_current = list(self.my_fixed_decks_info_from_file)
            self.my_decks_changed.set(False)
            self.save_my_decks_button.config(state="disabled")
            self.reload_my_decks_ui()
            self.status_label.config(text="我方卡组已重置为 [默认]")
        else:  # custom
            selected = self.open_deck_selector(
                "my",
                "请选择6套 [我方] 卡组",
                6, 6
            )
            if selected:
                self.my_decks_data_current = selected
                self.my_decks_changed.set(True)
                self.save_my_decks_button.config(state="normal")
                self.reload_my_decks_ui()
                self.status_label.config(text="我方卡组已 [自定义]")
            else:
                self.my_deck_mode.set("file")

    def save_my_decks(self):
        """保存当前自定义的我方卡组到 my_decks.json"""
        if not self.my_decks_changed.get():
            return

        try:
            with open("my_decks.json", 'w', encoding='utf-8') as f:
                json.dump(self.my_decks_data_current, f, indent=4, ensure_ascii=False)

            self.my_fixed_decks_info_from_file = list(self.my_decks_data_current)
            self.my_decks_changed.set(False)
            self.save_my_decks_button.config(state="disabled")
            self.status_label.config(text="成功保存 [我方卡组] 到 my_decks.json", fg="green")
        except Exception as e:
            self.show_error(f"保存失败: {e}")

    def open_deck_selector(self, team, title, min_sel, max_sel):
        """打开模态对话框"""
        dialog = DeckSelector(self,
                              title,
                              self.deck_pool,
                              min_sel, max_sel,
                              self.ICON_SIZE,
                              self.DEFAULT_FONT)

        return dialog.selected_decks_info

    # --- 卡组图标加载 ---
    def load_deck_icon(self, path, size):
        """加载卡组图标，如果失败则创建占位符"""
        try:
            img = Image.open(path).resize(size, Image.Resampling.LANCZOS)
        except Exception:
            img = Image.new("RGB", size, color=PLACEHOLDER_COLOR)
            draw = ImageDraw.Draw(img)
            try:
                # 尝试加载中文字体
                font = ImageFont.truetype("simhei.ttf", self.font_size_default)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", self.font_size_default)
                except IOError:
                    font = ImageFont.load_default()
            draw.text((size[0] / 2, size[1] / 2), "图标缺失", fill="white", anchor="mm", font=font)

        return ImageTk.PhotoImage(img)

    def create_deck_widget(self, parent_frame, deck_info):
        """创建单个卡组的可视化组件 (图标+名称)"""

        widget = tk.Frame(parent_frame, bg=BG_COLOR, relief="solid", bd=1, width=self.ICON_SIZE[0],
                          height=self.ICON_SIZE[1])
        widget.pack_propagate(False)

        icon_img = self.load_deck_icon(deck_info["icon_path"], self.ICON_SIZE)

        icon_label = tk.Label(widget, image=icon_img, bd=0)
        icon_label.image = icon_img
        icon_label.place(x=0, y=0)

        name_bg = tk.Label(widget, text=deck_info["name"], bg="black", fg="white", font=self.OVERLAY_FONT,
                           padx=int(5 * self.scaling))
        name_bg.place(relx=0.5, rely=1.0, anchor="s", y=int(-5 * self.scaling))

        ban_font = self.check_font((self.FONT_NAME, self.font_size_ban_x, "bold"),
                                   (self.FONT_FALLBACK, self.font_size_ban_x, "bold"))
        widget.ban_overlay = tk.Label(widget, text="❌", fg="#E74C3C", bg=BG_COLOR, font=ban_font)

        widget.pack(side="left", padx=int(10 * self.scaling))

        widget.deck_info = deck_info
        widget.icon_label = icon_label
        widget.name_label = name_bg

        return widget

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    # --- 游戏流程 ---

    def reload_my_decks_ui(self):
        """仅刷新我方卡组UI (用于自定义)"""
        self.clear_frame(self.my_decks_container)
        self.my_decks_container.pack(pady=int(15 * self.scaling))

        self.my_decks_widgets = []
        for deck in self.my_decks_data_current:
            widget = self.create_deck_widget(self.my_decks_container, deck)
            self.my_decks_widgets.append(widget)

    def reset_game(self):
        """重置整个游戏状态和UI"""
        self.game_state = "SETUP"
        self.status_label.config(text="请设置卡组，然后点击'生成对局'", fg="black")

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_widgets = []
        self.opponent_picked_decks_data = []

        self.my_decks_data_current = list(self.my_fixed_decks_info_from_file)
        self.opponent_decks_data = []

        self.clear_frame(self.opponent_decks_container)
        self.clear_frame(self.my_decks_container)
        self.clear_frame(self.matchup_container)

        self.opponent_decks_container.pack(pady=int(15 * self.scaling))
        self.my_decks_container.pack(pady=int(15 * self.scaling))
        self.matchup_container.pack(pady=int(15 * self.scaling), fill="x", expand=True)

        self.opponent_frame.config(text="对方卡组 (待生成)")
        self.reload_my_decks_ui()

        self.opponent_deck_mode.set("random")
        self.my_deck_mode.set("file")
        self.custom_opponent_ban.set(False)
        self.custom_opponent_pick.set(False)
        self.my_decks_changed.set(False)

        self.count_slider.config(state="normal")
        self.generate_button.config(state="normal")
        self.save_my_decks_button.config(state="disabled")
        self.undo_button.config(state="disabled")  # 【撤回】

        self.generate_matchup_button.pack_forget()

        for w in self.opponent_frame.winfo_children():
            if isinstance(w, ttk.Radiobutton): w.config(state="normal")
        for w in self.my_frame.winfo_children():
            if isinstance(w, ttk.Radiobutton): w.config(state="normal")

        self.custom_opponent_ban_check.config(state="normal")
        self.custom_opponent_pick_check.config(state="normal")
        self.matchup_icon_cache = []

    def set_controls_locked(self, locked):
        """锁定/解锁顶部的控制"""
        state = "disabled" if locked else "normal"
        self.count_slider.config(state="disabled" if locked or self.opponent_deck_mode.get() == "custom" else "normal")
        self.generate_button.config(state=state)
        self.save_my_decks_button.config(state="disabled" if locked or not self.my_decks_changed.get() else "normal")

        # 【撤回】: 撤回按钮在锁定时也禁用
        if locked:
            self.undo_button.config(state="disabled")

        self.custom_opponent_ban_check.config(state=state)
        self.custom_opponent_pick_check.config(state=state)

        for w in self.winfo_children():
            if isinstance(w, tk.Frame):
                for child in w.winfo_children():
                    if isinstance(child, tk.Frame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Radiobutton):
                                grandchild.config(state=state)

    def start_game_flow(self):
        """点击“生成”按钮，开始B/P流程"""
        self.set_controls_locked(True)

        self.game_state = "BAN"
        self.clear_frame(self.opponent_decks_container)
        self.clear_frame(self.matchup_container)
        self.generate_matchup_button.pack_forget()

        for widget in self.my_decks_widgets:
            self.set_widget_visual(widget, "normal")
            self.unbind_widget_clicks(widget)

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_widgets = []
        self.opponent_picked_decks_data = []

        if self.opponent_deck_mode.get() == "random":
            count = self.opponent_count_var.get()
            if len(self.deck_pool) < count:
                self.show_error("卡组资源池中的卡组数量不足。")
                self.reset_game()
                return
            self.opponent_decks_data = random.sample(self.deck_pool, count)
        else:  # custom
            selected = self.open_deck_selector(
                "opponent",
                "请选择 4 到 6 套 [对方] 卡组",
                4, 6
            )
            if not selected:
                self.reset_game()
                return
            self.opponent_decks_data = selected

        count = len(self.opponent_decks_data)
        self.opponent_frame.config(text=f"对方卡组 ({count}套)")

        self.opponent_decks_widgets = []
        for deck in self.opponent_decks_data:
            widget = self.create_deck_widget(self.opponent_decks_container, deck)
            self.opponent_decks_widgets.append(widget)

            handler = lambda e, w=widget: self.handle_deck_click(w, "opponent")
            self.bind_widget_clicks(widget, handler)

        self.status_label.config(text="[Ban阶段] 请点击一套 [对方卡组] 进行Ban (1/1)", fg="blue")

    def bind_widget_clicks(self, widget, handler):
        """绑定点击事件到卡组的所有子组件"""
        widget.bind("<Button-1>", handler)
        widget.icon_label.bind("<Button-1>", handler)
        widget.name_label.bind("<Button-1>", handler)
        if hasattr(widget, 'ban_overlay'):
            widget.ban_overlay.bind("<Button-1>", handler)

    def unbind_widget_clicks(self, widget):
        """解绑卡组的所有点击事件"""
        widget.unbind("<Button-1>")
        widget.icon_label.unbind("<Button-1>")
        widget.name_label.unbind("<Button-1>")
        if hasattr(widget, 'ban_overlay'):
            widget.ban_overlay.unbind("<Button-1>")

    def handle_deck_click(self, widget, target_team):
        """处理卡组点击事件 (Ban 和 Pick)"""

        if self.game_state == "BAN":
            if target_team == "opponent":
                if self.opponent_banned_widget: return

                self.opponent_banned_widget = widget
                self.set_widget_visual(widget, "banned")

                for w in self.opponent_decks_widgets:
                    self.unbind_widget_clicks(w)

                # 【撤回】: 激活撤回按钮
                self.undo_button.config(state="normal")

                self.process_ai_ban()

        elif self.game_state == "CUSTOM_OPPONENT_BAN":
            if target_team == "my":
                if self.my_banned_widget: return

                self.my_banned_widget = widget
                self.set_widget_visual(widget, "banned")

                for w in self.my_decks_widgets:
                    self.unbind_widget_clicks(w)

                # 【撤回】: 激活撤回按钮 (在手动Ban时也激活)
                self.undo_button.config(state="normal")

                self.start_player_pick_phase()

        elif self.game_state == "PICK":
            if target_team == "my":
                if widget in self.my_picked_widgets:
                    self.my_picked_widgets.remove(widget)
                    self.set_widget_visual(widget, "normal")
                elif len(self.my_picked_widgets) < 3:
                    self.my_picked_widgets.append(widget)
                    self.set_widget_visual(widget, "picked")

                count = len(self.my_picked_widgets)
                self.status_label.config(text=f"[Pick阶段] 请选择 3 套 [我方卡组] 出战 ({count}/3)")

                if len(self.my_picked_widgets) == 3:
                    self.game_state = "PENDING_OPPONENT_PICK"
                    self.status_label.config(text="我方阵容确定！等待对方选择...", fg="green")

                    for w in self.my_decks_widgets:
                        self.unbind_widget_clicks(w)

                    # 【撤回】: 我方Pick完毕，撤回按钮依然可用
                    self.undo_button.config(state="normal")
                    self.process_ai_pick()

        elif self.game_state == "CUSTOM_OPPONENT_PICK":
            if target_team == "opponent":
                if widget in self.opponent_picked_widgets:
                    self.opponent_picked_widgets.remove(widget)
                    self.set_widget_visual(widget, "normal")
                elif len(self.opponent_picked_widgets) < 3:
                    self.opponent_picked_widgets.append(widget)
                    self.set_widget_visual(widget, "picked")

                count = len(self.opponent_picked_widgets)
                self.status_label.config(text=f"[对方Pick阶段] 请选择 3 套 [对方卡组] 出战 ({count}/3)")

                if len(self.opponent_picked_widgets) == 3:
                    self.game_state = "DONE"
                    self.status_label.config(text="双方阵容确定！", fg="green")

                    self.opponent_picked_decks_data = [w.deck_info for w in self.opponent_picked_widgets]

                    for w in self.opponent_decks_widgets:
                        self.unbind_widget_clicks(w)

                    # 【撤回】: 双方Pick完毕，撤回按钮依然可用
                    self.undo_button.config(state="normal")
                    self.show_final_matchup_button()

    def set_widget_visual(self, widget, state):
        """设置卡组的视觉状态 (高亮)"""
        if hasattr(widget, 'ban_overlay'):
            widget.ban_overlay.place_forget()

        if state == "normal":
            widget.config(bg=BG_COLOR, relief="solid", bd=1)
        elif state == "banned":
            widget.config(bg="#E74C3C", relief="solid", bd=int(3 * self.scaling))
            if hasattr(widget, 'ban_overlay'):
                widget.ban_overlay.place(relx=0.5, rely=0.5, anchor="center")
        elif state == "picked":
            widget.config(bg="#2ECC71", relief="solid", bd=int(3 * self.scaling))

    def start_player_pick_phase(self):
        """(辅助函数) 进入玩家Pick阶段"""
        # 【撤回】: 进入Pick阶段，撤回按钮依然可用
        self.undo_button.config(state="normal")

        self.game_state = "PICK"
        self.status_label.config(text="[Pick阶段] 请选择 3 套 [我方卡组] 出战 (0/3)", fg="blue")

        for w in self.my_decks_widgets:
            if w != self.my_banned_widget:
                handler = lambda e, w=w: self.handle_deck_click(w, "my")
                self.bind_widget_clicks(w, handler)

    # --- AI 逻辑 (入口) ---

    def process_ai_ban(self):
        """处理对方(AI或手动)的Ban选择"""
        if self.custom_opponent_ban.get():
            self.game_state = "CUSTOM_OPPONENT_BAN"
            self.status_label.config(text="[对方Ban阶段] 请点击一套 [我方卡组] 进行Ban", fg="red")

            for w in self.my_decks_widgets:
                handler = lambda e, w=w: self.handle_deck_click(w, "my")
                self.bind_widget_clicks(w, handler)
        else:
            available_to_ban = [w for w in self.my_decks_widgets]
            self.my_banned_widget = self.ai_logic_ban(available_to_ban)

            if self.my_banned_widget:
                self.set_widget_visual(self.my_banned_widget, "banned")
                self.unbind_widget_clicks(self.my_banned_widget)

            self.start_player_pick_phase()

    def process_ai_pick(self):
        """处理对方(AI或手动)的Pick选择"""
        # 【撤回】: 进入Pick阶段，撤回按钮依然可用
        self.undo_button.config(state="normal")

        if self.custom_opponent_pick.get():
            self.game_state = "CUSTOM_OPPONENT_PICK"
            self.status_label.config(text="[对方Pick阶段] 请选择 3 套 [对方卡组] 出战 (0/3)", fg="red")

            for w in self.opponent_decks_widgets:
                if w != self.opponent_banned_widget:
                    handler = lambda e, w=w: self.handle_deck_click(w, "opponent")
                    self.bind_widget_clicks(w, handler)
        else:
            available_to_pick = [w for w in self.opponent_decks_widgets if w != self.opponent_banned_widget]
            picked_widgets = self.ai_logic_pick(available_to_pick, 3)

            self.opponent_picked_decks_data = []
            self.opponent_picked_widgets = []  # 记录AI Pick的widget
            for widget in picked_widgets:
                self.set_widget_visual(widget, "picked")
                self.opponent_picked_decks_data.append(widget.deck_info)
                self.opponent_picked_widgets.append(widget)  # AI Pick
                self.unbind_widget_clicks(widget)

            self.game_state = "DONE"
            self.status_label.config(text="双方阵容确定！", fg="green")
            self.show_final_matchup_button()

    # --- 撤回逻辑 (重构) ---
    def process_undo(self):
        """
        多级撤回操作。
        1. (DONE, 已生成对战) -> (DONE, 未生成对战)
        2. (DONE, 未生成对战) -> (PICK / CUSTOM_OPPONENT_PICK)
        3. (PENDING_OPPONENT_PICK) -> (PICK)
        4. (PICK / CUSTOM_OPPONENT_PICK) -> (BAN)
        """

        # 1. 撤销对战表 (如果已生成)
        if self.game_state == "DONE" and self.matchup_container.winfo_children():
            self.status_label.config(text="[撤销] 已清空对战表。您可以重新生成。", fg="black")
            self.clear_frame(self.matchup_container)
            # 按钮留在原处，保持 "DONE" 状态
            return

        # 2. 撤销双方Pick (返回Pick阶段)
        if self.game_state == "DONE":
            # 撤销我方Pick
            for w in self.my_picked_widgets:
                self.set_widget_visual(w, "normal")
            self.my_picked_widgets = []

            # 撤销对方Pick (手动或AI)
            for w in self.opponent_picked_widgets:
                self.set_widget_visual(w, "normal")
            self.opponent_picked_widgets = []
            self.opponent_picked_decks_data = []

            self.generate_matchup_button.pack_forget()

            # 检查是返回AI Pick还是手动Pick
            if self.custom_opponent_pick.get():
                self.game_state = "CUSTOM_OPPONENT_PICK"
                self.status_label.config(text="[撤销] 返回 [对方Pick阶段]", fg="red")
                # 重新绑定对方卡组点击
                for w in self.opponent_decks_widgets:
                    if w != self.opponent_banned_widget:
                        handler = lambda e, w=w: self.handle_deck_click(w, "opponent")
                        self.bind_widget_clicks(w, handler)
            else:
                self.game_state = "PENDING_OPPONENT_PICK"  # 将由下一步撤销

            # 重新绑定我方卡组点击
            self.start_player_pick_phase()  # 这会将状态设置为 PICK
            self.status_label.config(text="[撤销] 返回 [我方Pick阶段]", fg="blue")
            return

        # 3. 撤销我方Pick (如果对方是AI且我方刚选完)
        if self.game_state == "PENDING_OPPONENT_PICK":
            # 撤销我方Pick
            for w in self.my_picked_widgets:
                self.set_widget_visual(w, "normal")
            self.my_picked_widgets = []

            # 撤销AI Pick (如果AI已经选了)
            for w in self.opponent_picked_widgets:
                self.set_widget_visual(w, "normal")
            self.opponent_picked_widgets = []
            self.opponent_picked_decks_data = []

            self.start_player_pick_phase()  # 返回我方Pick
            self.status_label.config(text="[撤销] 返回 [我方Pick阶段]", fg="blue")
            return

        # 4. 撤销Ban (返回Ban阶段)
        if self.game_state == "PICK" or self.game_state == "CUSTOM_OPPONENT_PICK":
            self.game_state = "BAN"
            self.status_label.config(text="[撤销] 返回 [Ban阶段]。请重新Ban [对方卡组]", fg="blue")
            self.undo_button.config(state="disabled")  # 这是撤回链的末端

            # 清除Pick阶段的绑定
            for w in self.my_decks_widgets:
                self.unbind_widget_clicks(w)

            # 恢复我方被Ban卡组
            if self.my_banned_widget:
                self.set_widget_visual(self.my_banned_widget, "normal")
                self.my_banned_widget = None

            # 恢复对方被Ban卡组，并重新绑定所有对方卡组的点击
            if self.opponent_banned_widget:
                self.set_widget_visual(self.opponent_banned_widget, "normal")
                self.opponent_banned_widget = None

            for w in self.opponent_decks_widgets:
                handler = lambda e, w=w: self.handle_deck_click(w, "opponent")
                self.bind_widget_clicks(w, handler)

            return

    def show_final_matchup_button(self):
        """显示"生成对战"按钮"""
        self.matchup_frame.config(text="最终对战")
        self.clear_frame(self.matchup_container)

        # 【布局修复】: 强制按钮在 control_frame 之前显示
        self.generate_matchup_button.pack(
            before=self.control_frame,  # <-- 关键修复
            pady=(int(10 * self.scaling), 0),
            fill="x",
            padx=int(20 * self.scaling)
        )
        self.generate_matchup_button.config(state="normal")

    def display_random_matchups(self):
        """(按钮触发) 显示最终的1v1随机匹配"""
        self.clear_frame(self.matchup_container)

        my_final_picks = [w.deck_info for w in self.my_picked_widgets]
        opp_final_picks = list(self.opponent_picked_decks_data)

        if len(my_final_picks) != 3 or len(opp_final_picks) != 3:
            self.show_error("错误：双方出战卡组不为3。")
            return

        random.shuffle(my_final_picks)
        random.shuffle(opp_final_picks)

        self.matchup_frame.config(text="最终对战 (1v1 随机匹配)")
        self.matchup_icon_cache = []

        for i in range(3):
            my_deck = my_final_picks[i]
            opp_deck = opp_final_picks[i]

            match_row = tk.Frame(self.matchup_container, bg=BG_COLOR)
            match_row.pack(pady=int(5 * self.scaling), fill='x')

            # --- 【修复3】: 使用Grid布局重构对战显示 ---

            # 配置Grid: 1(我方) - 2(VS) - 3(对方)
            match_row.columnconfigure(0, weight=3, uniform="team")
            match_row.columnconfigure(1, weight=1, uniform="vs")
            match_row.columnconfigure(2, weight=3, uniform="team")

            # 我方 (图标 + 名称)
            my_team_frame = tk.Frame(match_row, bg=BG_COLOR)

            my_icon_img = self.load_deck_icon(my_deck['icon_path'], self.MATCHUP_ICON_SIZE)
            self.matchup_icon_cache.append(my_icon_img)
            my_icon_label = tk.Label(my_team_frame, image=my_icon_img, bd=0, bg=BG_COLOR)
            my_icon_label.image = my_icon_img
            my_icon_label.pack(side="right", padx=(0, 5))  # 图标在右

            tk.Label(my_team_frame, text=my_deck['name'], font=self.OVERLAY_FONT, fg="blue", bg=BG_COLOR,
                     anchor="e").pack(side="right", fill="x", expand=True)

            my_team_frame.grid(row=0, column=0, sticky="e")  # 整体右对齐

            # VS
            tk.Label(match_row, text=" VS ", font=(self.FONT_NAME, self.font_size_status, "bold"), bg=BG_COLOR).grid(
                row=0, column=1)

            # 对方 (图标 + 名称)
            opp_team_frame = tk.Frame(match_row, bg=BG_COLOR)

            opp_icon_img = self.load_deck_icon(opp_deck['icon_path'], self.MATCHUP_ICON_SIZE)
            self.matchup_icon_cache.append(opp_icon_img)
            opp_icon_label = tk.Label(opp_team_frame, image=opp_icon_img, bd=0, bg=BG_COLOR)
            opp_icon_label.image = opp_icon_img
            opp_icon_label.pack(side="left", padx=(5, 0))  # 图标在左

            tk.Label(opp_team_frame, text=opp_deck['name'], font=self.OVERLAY_FONT, fg="red", bg=BG_COLOR,
                     anchor="w").pack(side="left", fill="x", expand=True)

            opp_team_frame.grid(row=0, column=2, sticky="w")  # 整体左对齐

    # --- 可替换的 AI 逻辑 ---

    def ai_logic_ban(self, available_decks):
        if not available_decks: return None
        return random.choice(available_decks)

    def ai_logic_pick(self, available_decks, num_to_pick):
        if len(available_decks) < num_to_pick:
            return available_decks
        return random.sample(available_decks, num_to_pick)


def set_dpi_awareness():
    if platform.system() == "Windows" and ctypes:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except (AttributeError, OSError):
                print("Warning: Could not set DPI awareness. Scaling might be incorrect.")


# --- DPI 运行 ---
if __name__ == "__main__":
    if not os.path.exists("icons"):
        os.makedirs("icons")
        print("已创建 'icons' 文件夹。请放入卡组图标。")

    set_dpi_awareness()

    app = DeckBPSimulator()
    app.mainloop()