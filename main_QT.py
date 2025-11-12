# -*- coding: utf-8 -*-
"""
@Project    : Practice
@File       : main_QT.py
@Author     : Bella
@CreateTime : 2025/11/12 下午11:08
"""
import sys
import json
import random
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QGroupBox, QFrame
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QIcon
from PyQt6.QtCore import Qt, QSize, pyqtSignal

# --- 常量 ---
ICON_SIZE = QSize(100, 140)  # 卡组图标显示大小
PLACEHOLDER_COLOR = "#a0a0a0"
BG_COLOR = "#f0f0f0"
FONT_NAME = "Arial"  # 尝试一个通用字体


# --- 自定义卡组组件 ---

class DeckWidget(QWidget):
    """显示单个卡组的自定义组件"""

    # 定义一个点击信号
    clicked = pyqtSignal()

    def __init__(self, deck_info, parent=None):
        super().__init__(parent)
        self.deck_info = deck_info
        self.setFixedSize(ICON_SIZE)

        # 1. 底层图标
        self.icon_label = QLabel(self)
        self.icon_label.setGeometry(0, 0, ICON_SIZE.width(), ICON_SIZE.height())
        pixmap = self.load_deck_icon(deck_info["icon_path"])
        self.icon_label.setPixmap(pixmap.scaled(ICON_SIZE, Qt.AspectRatioMode.KeepAspectByExpanding,
                                                Qt.TransformationMode.SmoothTransformation))
        self.icon_label.setScaledContents(True)  # 确保填满

        # 2. 顶层名称 (使用样式表实现半透明)
        self.name_label = QLabel(deck_info["name"], self)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont(FONT_NAME, 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.7); 
            color: white;
            padding: 3px;
        """)
        # 自动调整大小并放置在底部
        self.name_label.adjustSize()
        self.name_label.resize(ICON_SIZE.width(), self.name_label.height())
        self.name_label.move(0, ICON_SIZE.height() - self.name_label.height() - 5)

        # 3. 边框 (用于高亮)
        self.set_visual_state("normal")

    def load_deck_icon(self, path):
        """加载卡组图标，如果失败则创建占位符"""
        if not os.path.exists(path):
            return self.create_placeholder()

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return self.create_placeholder()

        return pixmap

    def create_placeholder(self):
        """使用 QPainter 创建一个占位符 QPixmap"""
        pixmap = QPixmap(ICON_SIZE)
        pixmap.fill(QColor(PLACEHOLDER_COLOR))

        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.setFont(QFont(FONT_NAME, 12))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "图标缺失")
        painter.end()
        return pixmap

    def set_visual_state(self, state):
        """设置卡组的视觉状态 (高亮)"""
        if state == "normal":
            self.setStyleSheet("border: 1px solid #ccc;")
            self.icon_label.setGraphicsEffect(None)
        elif state == "banned":
            self.setStyleSheet("border: 3px solid red;")
            # 可以在这里添加灰度效果 (QGraphicsGrayscaleEffect)，但边框已足够
        elif state == "picked":
            self.setStyleSheet("border: 3px solid green;")

    def mousePressEvent(self, event):
        """覆盖鼠标点击事件，发送信号"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            event.ignore()


# --- 主应用 ---
class DeckBPSimulator(QWidget):
    def __init__(self):
        super().__init__()
        self.title = "卡组B/P对局模拟器 (PyQt6版)"
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(f"background-color: {BG_COLOR};")

        # 1. 加载配置
        self.deck_pool = self.load_json("deck_pool.json", "卡组资源池")
        self.my_fixed_decks_info = self.load_json("my_decks.json", "我方卡组")

        if not self.deck_pool or not self.my_fixed_decks_info:
            # 错误信息已在 load_json 中显示
            sys.exit(1)

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
        self.init_ui()
        self.reset_game()

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
        """在状态栏显示错误"""
        # PyQt的错误显示通常用QMessageBox，但为了简单，我们用状态标签
        try:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: red;")
        except AttributeError:
            # 如果 status_label 还没创建
            print(f"FATAL ERROR: {message}")

    def init_ui(self):
        """创建所有UI组件"""
        self.main_layout = QVBoxLayout(self)

        # 顶部控制面板
        control_frame = QFrame(self)
        control_layout = QHBoxLayout(control_frame)

        control_layout.addWidget(QLabel("对方卡组数量:", self))

        self.count_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.count_slider.setRange(4, 6)
        self.count_slider.setTickInterval(1)
        self.count_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.count_slider.setFixedWidth(150)
        self.count_slider_label = QLabel(f"{self.count_slider.value()}", self)
        self.count_slider.valueChanged.connect(lambda v: self.count_slider_label.setText(str(v)))

        control_layout.addWidget(self.count_slider)
        control_layout.addWidget(self.count_slider_label)
        control_layout.addSpacing(20)

        self.generate_button = QPushButton("生成对局", self)
        self.generate_button.clicked.connect(self.start_game_flow)
        control_layout.addWidget(self.generate_button)

        self.reset_button = QPushButton("重置", self)
        self.reset_button.clicked.connect(self.reset_game)
        control_layout.addWidget(self.reset_button)
        control_layout.addStretch(1)  # 推动所有东西到左边

        self.main_layout.addWidget(control_frame)

        # 状态/提示信息
        self.status_label = QLabel("请滑动选择对方卡组数量，然后点击'生成对局'", self)
        self.status_label.setFont(QFont(FONT_NAME, 14))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # 对方卡组
        self.opponent_frame = QGroupBox("对方卡组 (待生成)", self)
        self.opponent_frame.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        self.opponent_decks_container = QHBoxLayout()
        self.opponent_decks_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.opponent_frame.setLayout(self.opponent_decks_container)
        self.main_layout.addWidget(self.opponent_frame)

        # 我方卡组
        self.my_frame = QGroupBox("我方卡组", self)
        self.my_frame.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        self.my_decks_container = QHBoxLayout()
        self.my_decks_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.my_frame.setLayout(self.my_decks_container)
        self.main_layout.addWidget(self.my_frame)

        # 最终对战表
        self.matchup_frame = QGroupBox("最终对战", self)
        self.matchup_frame.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        self.matchup_container = QVBoxLayout()
        self.matchup_frame.setLayout(self.matchup_container)
        self.main_layout.addWidget(self.matchup_frame)

        self.main_layout.addStretch(1)  # 推动所有东西到顶部

    def clear_layout(self, layout):
        """清除Layout中的所有子组件"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    # --- 游戏流程 ---

    def reset_game(self):
        """重置整个游戏状态和UI"""
        self.game_state = "SETUP"
        self.status_label.setText("请滑动选择对方卡组数量，然后点击'生成对局'")
        self.status_label.setStyleSheet("color: black;")

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_decks_data = []

        self.my_decks_data = list(self.my_fixed_decks_info)  # 深拷贝
        self.opponent_decks_data = []

        self.clear_layout(self.opponent_decks_container)
        self.clear_layout(self.my_decks_container)
        self.clear_layout(self.matchup_container)

        self.opponent_frame.setTitle("对方卡组 (待生成)")

        # 重新加载我方卡组UI
        self.my_decks_widgets = []
        for deck in self.my_decks_data:
            widget = DeckWidget(deck)
            self.my_decks_container.addWidget(widget)
            self.my_decks_widgets.append(widget)

        self.count_slider.setEnabled(True)
        self.generate_button.setEnabled(True)

    def start_game_flow(self):
        """点击“生成”按钮，开始B/P流程"""
        # 1. 重置(部分重置，保留我方UI)
        self.game_state = "BAN"
        self.count_slider.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.clear_layout(self.opponent_decks_container)
        self.clear_layout(self.matchup_container)

        # 重置我方卡组状态
        for widget in self.my_decks_widgets:
            widget.set_visual_state("normal")
            widget.clicked.disconnect()  # 断开旧的连接

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_decks_data = []

        # 2. 生成对方卡组
        count = self.count_slider.value()
        if len(self.deck_pool) < count:
            self.show_error("卡组资源池中的卡组数量不足。")
            self.reset_game()
            return

        self.opponent_decks_data = random.sample(self.deck_pool, count)
        self.opponent_frame.setTitle(f"对方卡组 ({count}套)")

        self.opponent_decks_widgets = []
        for deck in self.opponent_decks_data:
            widget = DeckWidget(deck)
            self.opponent_decks_container.addWidget(widget)
            self.opponent_decks_widgets.append(widget)
            # 绑定点击事件 (用于Ban)
            widget.clicked.connect(lambda w=widget: self.handle_deck_click(w, "opponent"))

        # 3. 更新状态
        self.status_label.setText("[Ban阶段] 请点击一套 [对方卡组] 进行Ban (1/1)")
        self.status_label.setStyleSheet("color: blue;")

    def handle_deck_click(self, widget, target_team):
        """处理卡组点击事件 (Ban 和 Pick)"""

        if self.game_state == "BAN":
            # 玩家Ban对方
            if target_team == "opponent":
                if self.opponent_banned_widget:
                    return  # 已经Ban过了

                self.opponent_banned_widget = widget
                widget.set_visual_state("banned")
                widget.clicked.disconnect()  # Ban了就不能点了

                # 玩家Ban完后，触发对方(AI)Ban
                self.process_ai_ban()

                # 进入Pick阶段
                self.game_state = "PICK"
                self.status_label.setText("[Pick阶段] 请选择 3 套 [我方卡组] 出战 (0/3)")

                # 为我方卡组绑定Pick事件
                for w in self.my_decks_widgets:
                    if w != self.my_banned_widget:  # 不能选被Ban的
                        w.clicked.connect(lambda w=w: self.handle_deck_click(w, "my"))

        elif self.game_state == "PICK":
            # 玩家Pick己方
            if target_team == "my":
                if widget in self.my_picked_widgets:
                    # 取消选择
                    self.my_picked_widgets.remove(widget)
                    widget.set_visual_state("normal")
                elif len(self.my_picked_widgets) < 3:
                    # 选择
                    self.my_picked_widgets.append(widget)
                    widget.set_visual_state("picked")

                # 更新状态
                count = len(self.my_picked_widgets)
                self.status_label.setText(f"[Pick阶段] 请选择 3 套 [我方卡组] 出战 ({count}/3)")

                # 如果选满了3套
                if len(self.my_picked_widgets) == 3:
                    self.game_state = "DONE"
                    self.status_label.setText("阵容确定！正在生成对战...")
                    self.status_label.setStyleSheet("color: green;")

                    # 触发对方(AI)Pick
                    self.process_ai_pick()

                    # 显示最终对战
                    self.show_final_matchup()

    # --- AI 逻辑 (入口) ---

    def process_ai_ban(self):
        """处理对方(AI)的Ban选择"""
        available_to_ban = [w for w in self.my_decks_widgets]

        # --- AI Ban 逻辑入口 ---
        self.my_banned_widget = self.ai_logic_ban(available_to_ban)
        # --- 结束 ---

        if self.my_banned_widget:
            self.my_banned_widget.set_visual_state("banned")
            # 移除被Ban卡组的点击事件 (在进入Pick阶段时已经通过检查)
            try:
                self.my_banned_widget.clicked.disconnect()
            except TypeError:
                pass  # 没连接过

    def process_ai_pick(self):
        """处理对方(AI)的Pick选择"""
        available_to_pick = [w for w in self.opponent_decks_widgets if w != self.opponent_banned_widget]

        # --- AI Pick 逻辑入口 ---
        picked_widgets = self.ai_logic_pick(available_to_pick, 3)
        # --- 结束 ---

        self.opponent_picked_decks_data = []
        for widget in picked_widgets:
            widget.set_visual_state("picked")
            self.opponent_picked_decks_data.append(widget.deck_info)
            try:
                widget.clicked.disconnect()  # Pick了就不能点了
            except TypeError:
                pass

    def show_final_matchup(self):
        """显示最终的1v1随机匹配"""
        self.clear_layout(self.matchup_container)

        my_final_picks = [w.deck_info for w in self.my_picked_widgets]
        opp_final_picks = list(self.opponent_picked_decks_data)  # 确保是拷贝

        random.shuffle(my_final_picks)
        random.shuffle(opp_final_picks)

        self.matchup_frame.setTitle("最终对战 (1v1 随机匹配)")

        for i in range(3):
            my_deck = my_final_picks[i]
            opp_deck = opp_final_picks[i]

            match_row = QFrame(self)
            match_layout = QHBoxLayout(match_row)

            my_label = QLabel(my_deck['name'])
            my_label.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
            my_label.setStyleSheet("color: blue;")
            my_label.setAlignment(Qt.AlignmentFlag.AlignRight)

            vs_label = QLabel(" VS ")
            vs_label.setFont(QFont(FONT_NAME, 14, QFont.Weight.Bold))

            opp_label = QLabel(opp_deck['name'])
            opp_label.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
            opp_label.setStyleSheet("color: red;")
            opp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

            match_layout.addWidget(my_label)
            match_layout.addWidget(vs_label)
            match_layout.addWidget(opp_label)

            self.matchup_container.addWidget(match_row)

    # --- 可替换的 AI 逻辑 ---
    # (这些函数与 tkinter 版本完全相同)

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


# --- 运行 ---
if __name__ == "__main__":
    if not os.path.exists("icons/icons"):
        print("未检测到 'icons' 文件夹，正在创建...")
        os.makedirs("icons/icons")
        print("请将您的卡组图标文件 (如 deck_a.png) 放入 'icons' 文件夹中。")

    app = QApplication(sys.argv)
    ex = DeckBPSimulator()
    ex.show()
    sys.exit(app.exec())
