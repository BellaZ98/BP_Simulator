import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
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


# --- 主应用 ---
class DeckBPSimulator(tk.Tk):
    def __init__(self):
        super().__init__()

        # --- 缩放与字体处理 ---
        try:
            # 获取Tk的缩放因子 (适配Windows缩放)
            self.scaling = self.tk.call('tk', 'scaling')
            if self.scaling > 4:  # 异常值处理
                self.scaling = self.scaling / 96.0
        except Exception:
            self.scaling = 1.0

        # 强制DPI感知 (备用方案)
        if self.scaling == 1.0 and platform.system() == "Windows" and ctypes:
            try:
                scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
                self.scaling = scale_factor / 100.0
            except Exception:
                self.scaling = 1.0

        # 定义可缩放的常量
        self.ICON_WIDTH = int(100 * self.scaling)
        self.ICON_HEIGHT = int(140 * self.scaling)
        self.ICON_SIZE = (self.ICON_WIDTH, self.ICON_HEIGHT)

        self.FONT_NAME = "Microsoft YaHei UI"  # 微软雅黑
        self.FONT_FALLBACK = "Arial"

        # 字体大小 (已调低基础值)
        self.font_size_default = int(5 * self.scaling)
        self.font_size_overlay = int(5 * self.scaling)
        self.font_size_status = int(6 * self.scaling)
        self.font_size_group = int(5 * self.scaling)
        self.font_size_ban_x = int(18 * self.scaling)  # 调低 "X" 大小

        # 定义字体元组
        self.DEFAULT_FONT = (self.FONT_NAME, self.font_size_default)
        self.OVERLAY_FONT = (self.FONT_NAME, self.font_size_overlay, "bold")
        self.STATUS_FONT = (self.FONT_NAME, self.font_size_status)
        self.GROUP_FONT = (self.FONT_NAME, self.font_size_group, "bold")

        # 检查字体是否存在，如果不存在则回退
        self.DEFAULT_FONT = self.check_font(self.DEFAULT_FONT, (self.FONT_FALLBACK, self.font_size_default))
        self.OVERLAY_FONT = self.check_font(self.OVERLAY_FONT, (self.FONT_FALLBACK, self.font_size_overlay, "bold"))
        self.STATUS_FONT = self.check_font(self.STATUS_FONT, (self.FONT_FALLBACK, self.font_size_status))
        self.GROUP_FONT = self.check_font(self.GROUP_FONT, (self.FONT_FALLBACK, self.font_size_group, "bold"))
        # --- 结束 缩放与字体 ---

        self.title("卡组B/P对局模拟器")
        self.geometry(f"{int(1200 * self.scaling)}x{int(800 * self.scaling)}")
        self.configure(bg=BG_COLOR)

        # 1. 加载配置
        self.deck_pool = self.load_json("deck_pool.json", "卡组资源池")
        self.my_fixed_decks_info = self.load_json("my_decks.json", "我方卡组")

        if not self.deck_pool or not self.my_fixed_decks_info:
            self.quit()
            return

        # 2. 初始化状态变量
        self.game_state = "SETUP"
        self.my_decks_widgets = []
        self.opponent_decks_widgets = []
        self.my_decks_data = []
        self.opponent_decks_data = []
        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_decks_data = []

        # 3. 创建UI
        self.create_widgets()
        self.reset_game()

    def check_font(self, preferred_font, fallback_font):
        """检查首选字体是否存在，不存在则返回备用字体"""
        try:
            f = tkfont.Font(font=preferred_font)
            # 检查字体族是否按预期回退
            if f.actual()["family"].lower() in preferred_font[0].lower():
                return preferred_font
            else:
                return fallback_font
        except:
            return fallback_font

    def load_json(self, filepath, name):
        """加载JSON配置文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error(f"错误: 未找到配置文件 '{filepath}'。\n请确保 {name} 配置文件存在。")
            return None
        except json.JSONDecodeError:
            self.show_error(f"错误: 配置文件 '{filepath}' 格式错误。")
            return None

    def show_error(self, message):
        """显示错误信息"""
        try:
            if self.status_label:
                self.status_label.config(text=message, fg="red")
        except AttributeError:
            # 在 status_label 创建前出错
            error_label = tk.Label(self, text=message, fg="red", bg=BG_COLOR,
                                   font=(self.FONT_NAME, self.font_size_status))
            error_label.pack(pady=50)

    # --- UI 创建 ---
    def create_widgets(self):
        """创建所有UI组件"""

        # 顶部控制面板
        control_frame = tk.Frame(self, bg=BG_COLOR)
        control_frame.pack(pady=int(10 * self.scaling), fill="x")

        tk.Label(control_frame, text="对方卡组数量:", bg=BG_COLOR, font=self.DEFAULT_FONT).pack(side="left", padx=(
        int(20 * self.scaling), int(10 * self.scaling)))

        self.opponent_count_var = tk.IntVar(value=4)
        self.count_slider = ttk.Scale(control_frame, from_=4, to=6, orient="horizontal",
                                      variable=self.opponent_count_var, length=150 * self.scaling,
                                      command=lambda v: self.opponent_count_var.set(int(float(v))))
        self.count_slider.pack(side="left", padx=int(5 * self.scaling))

        self.generate_button = tk.Button(control_frame, text="生成对局", font=self.DEFAULT_FONT,
                                         command=self.start_game_flow)
        self.generate_button.pack(side="left", padx=int(20 * self.scaling))

        self.reset_button = tk.Button(control_frame, text="重置", font=self.DEFAULT_FONT, command=self.reset_game)
        self.reset_button.pack(side="left", padx=int(5 * self.scaling))

        # 状态/提示信息
        self.status_label = tk.Label(self, text="请滑动选择对方卡组数量，然后点击'生成对局'", font=self.STATUS_FONT,
                                     bg=BG_COLOR)
        self.status_label.pack(pady=int(10 * self.scaling))

        # 卡组显示区
        decks_frame = tk.Frame(self, bg=BG_COLOR)
        decks_frame.pack(fill="both", expand=True, padx=int(20 * self.scaling))

        # 对方卡组
        self.opponent_frame = tk.LabelFrame(decks_frame, text="对方卡组 (待生成)", font=self.GROUP_FONT, bg=BG_COLOR,
                                            bd=2, relief="groove")
        self.opponent_frame.pack(side="top", fill="x", pady=int(10 * self.scaling))
        self.opponent_decks_container = tk.Frame(self.opponent_frame, bg=BG_COLOR)
        self.opponent_decks_container.pack(pady=int(15 * self.scaling))

        # 我方卡组
        self.my_frame = tk.LabelFrame(decks_frame, text="我方卡组", font=self.GROUP_FONT, bg=BG_COLOR, bd=2,
                                      relief="groove")
        self.my_frame.pack(side="top", fill="x", pady=int(10 * self.scaling))
        self.my_decks_container = tk.Frame(self.my_frame, bg=BG_COLOR)
        self.my_decks_container.pack(pady=int(15 * self.scaling))

        # 最终对战表
        self.matchup_frame = tk.LabelFrame(decks_frame, text="最终对战", font=self.GROUP_FONT, bg=BG_COLOR, bd=2,
                                           relief="groove")
        self.matchup_frame.pack(side="top", fill="x", pady=int(10 * self.scaling))
        self.matchup_container = tk.Frame(self.matchup_frame, bg=BG_COLOR)
        self.matchup_container.pack(pady=int(15 * self.scaling))

    def load_deck_icon(self, path):
        """加载卡组图标，如果失败则创建占位符"""
        try:
            img = Image.open(path).resize(self.ICON_SIZE, Image.Resampling.LANCZOS)
        except Exception:
            # 文件未找到或非图片格式，创建占位符
            img = Image.new("RGB", self.ICON_SIZE, color=PLACEHOLDER_COLOR)
            draw = ImageDraw.Draw(img)

            # 尝试加载一个通用字体，如果失败也没关系
            try:
                # 尝试使用一个常见的中文兼容字体
                font = ImageFont.truetype("simhei.ttf", self.font_size_default)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", self.font_size_default)
                except IOError:
                    font = ImageFont.load_default()

            draw.text((self.ICON_SIZE[0] / 2, self.ICON_SIZE[1] / 2), "图标缺失", fill="white", anchor="mm", font=font)

        return ImageTk.PhotoImage(img)

    def create_deck_widget(self, parent_frame, deck_info):
        """创建单个卡组的可视化组件 (图标+名称)"""

        widget = tk.Frame(parent_frame, bg=BG_COLOR, relief="solid", bd=1, width=self.ICON_SIZE[0],
                          height=self.ICON_SIZE[1])
        widget.pack_propagate(False)  # 固定大小

        # 加载图标
        icon_img = self.load_deck_icon(deck_info["icon_path"])

        icon_label = tk.Label(widget, image=icon_img, bd=0)
        icon_label.image = icon_img  # 保持引用
        icon_label.place(x=0, y=0)

        # 覆盖名称
        name_bg = tk.Label(widget, text=deck_info["name"], bg="black", fg="white", font=self.OVERLAY_FONT,
                           padx=int(5 * self.scaling))
        # 使用 place 在图标上叠加名称
        name_bg.place(relx=0.5, rely=1.0, anchor="s", y=int(-5 * self.scaling))

        # --- 新增: 创建隐藏的 "X" 标识 ---
        ban_font = self.check_font((self.FONT_NAME, self.font_size_ban_x, "bold"),
                                   (self.FONT_FALLBACK, self.font_size_ban_x, "bold"))
        widget.ban_overlay = tk.Label(widget, text="❌", fg="#E74C3C", bg=BG_COLOR,
                                      font=ban_font)
        # 注意: 此时不 .place() 它，保持隐藏

        widget.pack(side="left", padx=int(10 * self.scaling))

        # 附加数据和引用
        widget.deck_info = deck_info
        widget.icon_label = icon_label  # 用于灰度化
        widget.name_label = name_bg  # <-- 【修复-1】: 存储对 name_label 的引用

        return widget

    def clear_frame(self, frame):
        """清除Frame中的所有子组件"""
        for widget in frame.winfo_children():
            widget.destroy()

    # --- 游戏流程 ---

    def reset_game(self):
        """重置整个游戏状态和UI"""
        self.game_state = "SETUP"
        self.status_label.config(text="请滑动选择对方卡组数量，然后点击'生成对局'", fg="black")

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_decks_data = []

        self.my_decks_data = list(self.my_fixed_decks_info)  # 深拷贝
        self.opponent_decks_data = []

        self.clear_frame(self.opponent_decks_container)
        self.clear_frame(self.my_decks_container)
        self.clear_frame(self.matchup_container)

        # 确保容器在清空后仍有内边距
        self.opponent_decks_container.pack(pady=int(15 * self.scaling))
        self.my_decks_container.pack(pady=int(15 * self.scaling))
        self.matchup_container.pack(pady=int(15 * self.scaling))

        self.opponent_frame.config(text="对方卡组 (待生成)")

        # 重新加载我方卡组UI
        self.my_decks_widgets = []
        for deck in self.my_decks_data:
            widget = self.create_deck_widget(self.my_decks_container, deck)
            self.my_decks_widgets.append(widget)

        self.count_slider.config(state="normal")
        self.generate_button.config(state="normal")

    def start_game_flow(self):
        """点击“生成”按钮，开始B/P流程"""
        # 1. 重置(部分重置，保留我方UI)
        self.game_state = "BAN"
        self.count_slider.config(state="disabled")
        self.generate_button.config(state="disabled")
        self.clear_frame(self.opponent_decks_container)
        self.clear_frame(self.matchup_container)

        # 重置我方卡组状态
        for widget in self.my_decks_widgets:
            self.set_widget_visual(widget, "normal")
            widget.unbind("<Button-1>")
            widget.icon_label.unbind("<Button-1>")
            widget.name_label.unbind("<Button-1>")
            if hasattr(widget, 'ban_overlay'):
                widget.ban_overlay.unbind("<Button-1>")

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_decks_data = []

        # 2. 生成对方卡组
        count = self.opponent_count_var.get()
        if len(self.deck_pool) < count:
            self.show_error("卡组资源池中的卡组数量不足。")
            self.reset_game()
            return

        self.opponent_decks_data = random.sample(self.deck_pool, count)
        self.opponent_frame.config(text=f"对方卡组 ({count}套)")

        self.opponent_decks_widgets = []
        for deck in self.opponent_decks_data:
            widget = self.create_deck_widget(self.opponent_decks_container, deck)
            self.opponent_decks_widgets.append(widget)

            # 【修复-2】: 必须绑定到所有子组件，因为它们会遮挡父Frame
            handler = lambda e, w=widget: self.handle_deck_click(w, "opponent")
            widget.bind("<Button-1>", handler)
            widget.icon_label.bind("<Button-1>", handler)
            widget.name_label.bind("<Button-1>", handler)
            widget.ban_overlay.bind("<Button-1>", handler)  # <-- 新增

        # 3. 更新状态
        self.status_label.config(text="[Ban阶段] 请点击一套 [对方卡组] 进行Ban (1/1)", fg="blue")

    def handle_deck_click(self, widget, target_team):
        """处理卡组点击事件 (Ban 和 Pick)"""

        if self.game_state == "BAN":
            # 玩家Ban对方
            if target_team == "opponent":
                if self.opponent_banned_widget:
                    return  # 已经Ban过了

                self.opponent_banned_widget = widget
                self.set_widget_visual(widget, "banned")

                # 【修复-3】: Ban了之后，移除所有组件的点击事件
                widget.unbind("<Button-1>")
                widget.icon_label.unbind("<Button-1>")
                widget.name_label.unbind("<Button-1>")
                widget.ban_overlay.unbind("<Button-1>")  # <-- 新增

                # 玩家Ban完后，触发对方(AI)Ban
                self.process_ai_ban()

                # 进入Pick阶段
                self.game_state = "PICK"
                self.status_label.config(text="[Pick阶段] 请选择 3 套 [我方卡组] 出战 (0/3)", fg="blue")

                # 为我方卡组绑定Pick事件
                for w in self.my_decks_widgets:
                    if w != self.my_banned_widget:  # 不能选被Ban的
                        # 【修复-4】: 同样，为我方卡组绑定所有子组件的点击
                        handler = lambda e, w=w: self.handle_deck_click(w, "my")
                        w.bind("<Button-1>", handler)
                        w.icon_label.bind("<Button-1>", handler)
                        w.name_label.bind("<Button-1>", handler)
                        w.ban_overlay.bind("<Button-1>", handler)  # <-- 新增

        elif self.game_state == "PICK":
            # 玩家Pick己方
            if target_team == "my":
                if widget in self.my_picked_widgets:
                    # 取消选择
                    self.my_picked_widgets.remove(widget)
                    self.set_widget_visual(widget, "normal")
                elif len(self.my_picked_widgets) < 3:
                    # 选择
                    self.my_picked_widgets.append(widget)
                    self.set_widget_visual(widget, "picked")

                # 更新状态
                count = len(self.my_picked_widgets)
                self.status_label.config(text=f"[Pick阶段] 请选择 3 套 [我方卡组] 出战 ({count}/3)")

                # 如果选满了3套
                if len(self.my_picked_widgets) == 3:
                    self.game_state = "DONE"
                    self.status_label.config(text="阵容确定！正在生成对战...", fg="green")

                    # 触发对方(AI)Pick
                    self.process_ai_pick()

                    # 显示最终对战
                    self.show_final_matchup()

    def set_widget_visual(self, widget, state):
        """设置卡组的视觉状态 (高亮)"""

        # --- 新增: "X" 标识管理 ---
        # 1. 首先，总是尝试隐藏 "X"
        if hasattr(widget, 'ban_overlay'):
            widget.ban_overlay.place_forget()

        # 2. 根据状态设置边框和 "X"
        if state == "normal":
            widget.config(bg=BG_COLOR, relief="solid", bd=1)
        elif state == "banned":
            widget.config(bg="#E74C3C", relief="solid", bd=int(3 * self.scaling))  # 红色高亮
            # 2a. 显示 "X"
            if hasattr(widget, 'ban_overlay'):
                widget.ban_overlay.place(relx=0.5, rely=0.5, anchor="center")
        elif state == "picked":
            widget.config(bg="#2ECC71", relief="solid", bd=int(3 * self.scaling))  # 绿色高亮

    # --- AI 逻辑 (入口) ---

    def process_ai_ban(self):
        """处理对方(AI)的Ban选择"""
        available_to_ban = [w for w in self.my_decks_widgets]

        # --- AI Ban 逻辑入口 ---
        # (未来在这里替换更复杂的逻辑)
        self.my_banned_widget = self.ai_logic_ban(available_to_ban)
        # --- 结束 ---

        if self.my_banned_widget:
            self.set_widget_visual(self.my_banned_widget, "banned")

            # 【修复-5】: AI Ban我方卡组后，同样移除所有子组件的点击
            self.my_banned_widget.unbind("<Button-1>")
            self.my_banned_widget.icon_label.unbind("<Button-1>")
            self.my_banned_widget.name_label.unbind("<Button-1>")
            self.my_banned_widget.ban_overlay.unbind("<Button-1>")  # <-- 新增

    def process_ai_pick(self):
        """处理对方(AI)的Pick选择"""
        available_to_pick = [w for w in self.opponent_decks_widgets if w != self.opponent_banned_widget]

        # --- AI Pick 逻辑入口 ---
        # (未来在这里替换更复杂的逻辑)
        picked_widgets = self.ai_logic_pick(available_to_pick, 3)
        # --- 结束 ---

        self.opponent_picked_decks_data = []
        for widget in picked_widgets:
            # 【!! 错误修复 !!】
            # 之前: widget.set_visual_state("picked") (这是PyQt的函数名)
            # 之后:
            self.set_widget_visual(widget, "picked")

            self.opponent_picked_decks_data.append(widget.deck_info)

            # 移除点击事件
            widget.unbind("<Button-1>")
            widget.icon_label.unbind("<Button-1>")
            widget.name_label.unbind("<Button-1>")
            if hasattr(widget, 'ban_overlay'):
                widget.ban_overlay.unbind("<Button-1>")

    def show_final_matchup(self):
        """显示最终的1v1随机匹配"""
        self.clear_frame(self.matchup_container)

        my_final_picks = [w.deck_info for w in self.my_picked_widgets]
        opp_final_picks = list(self.opponent_picked_decks_data)  # 确保是拷贝

        random.shuffle(my_final_picks)
        random.shuffle(opp_final_picks)

        self.matchup_frame.config(text="最终对战 (1v1 随机匹配)")

        for i in range(3):
            # 检查列表是否为空，防止索引错误
            if i >= len(my_final_picks) or i >= len(opp_final_picks):
                break

            my_deck = my_final_picks[i]
            opp_deck = opp_final_picks[i]

            match_row = tk.Frame(self.matchup_container, bg=BG_COLOR)
            match_row.pack(pady=int(5 * self.scaling))

            # (我方)
            tk.Label(match_row, text=my_deck['name'], font=self.OVERLAY_FONT, fg="blue", bg=BG_COLOR,
                     width=int(20 * self.scaling), anchor="e").pack(side="left")

            tk.Label(match_row, text=" VS ", font=(self.FONT_NAME, self.font_size_status, "bold"), bg=BG_COLOR).pack(
                side="left", padx=int(20 * self.scaling))

            # (对方)
            tk.Label(match_row, text=opp_deck['name'], font=self.OVERLAY_FONT, fg="red", bg=BG_COLOR,
                     width=int(20 * self.scaling), anchor="w").pack(side="left")

    # --- 可替换的 AI 逻辑 ---

    def ai_logic_ban(self, available_decks):
        """
        AI Ban 逻辑 (可替换)
        目前: 随机选择
        """
        if not available_decks:
            return None
        return random.choice(available_decks)

    def ai_logic_pick(self, available_decks, num_to_pick):
        """
        AI Pick 逻辑 (可替换)
        目前: 随机选择
        """
        if len(available_decks) < num_to_pick:
            return available_decks  # 如果不够选，全选

        return random.sample(available_decks, num_to_pick)


def set_dpi_awareness():
    """设置Windows DPI感知，以实现高分屏缩放"""
    if platform.system() == "Windows" and ctypes:
        try:
            # GDI-Scaling (GDI缩放)
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            try:
                # Per-Monitor DPI Awareness V2 (Win 10+)
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except (AttributeError, OSError):
                print("Warning: Could not set DPI awareness. Scaling might be incorrect.")


# --- DPI 运行 ---
if __name__ == "__main__":
    # 检查 icons 文件夹是否存在
    if not os.path.exists("icons"):
        print("未检测到 'icons' 文件夹，正在创建...")
        os.makedirs("icons")
        print("请将您的卡组图标文件 (如 deck_a.png) 放入 'icons' 文件夹中。")

    # --- 新增: 在启动App前设置DPI感知 ---
    set_dpi_awareness()

    app = DeckBPSimulator()
    app.mainloop()