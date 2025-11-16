import sys
import json
import random
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QGroupBox, QFrame, QRadioButton, QButtonGroup, QCheckBox,
    QDialog, QDialogButtonBox, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QIcon
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRect

# --- 常量 ---
ICON_WIDTH = 100
ICON_HEIGHT = 140
ICON_SIZE = QSize(ICON_WIDTH, ICON_HEIGHT)  # 卡组图标显示大小

MATCHUP_ICON_WIDTH = 30
MATCHUP_ICON_HEIGHT = 42
MATCHUP_ICON_SIZE = QSize(MATCHUP_ICON_WIDTH, MATCHUP_ICON_HEIGHT)  # 对战小图标

PLACEHOLDER_COLOR = "#a0a0a0"
BG_COLOR = "#f0f0f0"
FONT_NAME = "Microsoft YaHei UI"  # 使用与Tkinter版本一致的字体
FONT_FALLBACK = "Arial"


# --- DeckWidget (卡组组件) ---

class DeckWidget(QWidget):
    """显示单个卡组的自定义组件"""
    clicked = pyqtSignal()

    def __init__(self, deck_info, size=ICON_SIZE, parent=None):
        super().__init__(parent)
        self.deck_info = deck_info
        self.setFixedSize(size)

        self.current_size = size
        self.state = "normal"

        # 1. 底层图标
        self.icon_label = QLabel(self)
        self.icon_label.setGeometry(0, 0, size.width(), size.height())
        pixmap = self.load_deck_icon(deck_info["icon_path"], size)
        self.icon_label.setPixmap(pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                Qt.TransformationMode.SmoothTransformation))
        # self.icon_label.setScaledContents(True) # 移除：此行冗余且可能冲突

        # 2. 顶层名称
        self.name_label = QLabel(deck_info["name"], self)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_size = 10 if size == ICON_SIZE else 8
        self.name_label.setFont(QFont(FONT_NAME, font_size, QFont.Weight.Bold))
        self.name_label.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.7); 
            color: white;
            padding: 2px;
        """)
        self.name_label.adjustSize()
        self.name_label.resize(size.width(), self.name_label.height())
        self.name_label.move(0, size.height() - self.name_label.height() - int(size.height() * 0.05))

        # 3. 顶层 "Banned ❌" 覆盖
        ban_font_size = 35 if size == ICON_SIZE else 15
        self.ban_overlay = QLabel("❌", self)
        self.ban_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ban_overlay.setFont(QFont(FONT_NAME, ban_font_size, QFont.Weight.Bold))
        self.ban_overlay.setStyleSheet("color: #E74C3C; background-color: transparent;")
        self.ban_overlay.setGeometry(0, 0, size.width(), size.height())
        self.ban_overlay.hide()  # 默认隐藏

        # 4. 边框 (通过 paintEvent 绘制)
        self.border_color = QColor(BG_COLOR)
        self.border_width = 1

    def load_deck_icon(self, path, size):
        if not os.path.exists(path):
            return self.create_placeholder(size)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return self.create_placeholder(size)
        return pixmap

    def create_placeholder(self, size):
        pixmap = QPixmap(size)
        pixmap.fill(QColor(PLACEHOLDER_COLOR))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        font_size = 12 if size == ICON_SIZE else 8
        painter.setFont(QFont(FONT_FALLBACK, font_size))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "图标缺失")
        painter.end()
        return pixmap

    def set_visual_state(self, state):
        self.state = state
        self.ban_overlay.hide()

        if state == "normal":
            self.border_color = QColor("#ccc")
            self.border_width = 1
        elif state == "banned":
            self.border_color = QColor("#E74C3C")
            self.border_width = 3
            self.ban_overlay.show()
        elif state == "picked":  # "picked" 和 "selected" 状态共用绿色
            self.border_color = QColor("#2ECC71")
            self.border_width = 3

        self.update()  # 触发 paintEvent

    def paintEvent(self, event):
        """覆盖 paintEvent 来绘制边框"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(self.border_color, self.border_width))
        # 绘制一个矩形边框，(0,0) 到 (width-1, height-1)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            event.ignore()


# --- 卡组选择器 (新) ---

class DeckSelector(QDialog):
    """一个用于从卡组池中选择卡组的弹出对话框"""

    def __init__(self, parent, title, deck_pool, min_select, max_select):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(int(ICON_WIDTH * 5.5), int(ICON_HEIGHT * 2.5))
        self.setStyleSheet(f"background-color: {BG_COLOR};")

        self.deck_pool = deck_pool
        self.min_select = min_select
        self.max_select = max_select
        self.selected_decks_info = []
        self.selected_widgets = []
        self.widgets_map = {}  # widget -> deck_info

        layout = QVBoxLayout(self)

        # 1. 状态标签
        self.status_label = QLabel(self.get_status_text())
        self.status_label.setFont(QFont(FONT_NAME, 10))
        layout.addWidget(self.status_label)

        # 2. 滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # 填充卡组
        max_cols = 5
        for i, deck_info in enumerate(self.deck_pool):
            row = i // max_cols
            col = i % max_cols

            widget = DeckWidget(deck_info, ICON_SIZE)  # 弹窗中使用大图标
            widget.clicked.connect(lambda w=widget: self.toggle_select(w))
            scroll_layout.addWidget(widget, row, col)

            self.widgets_map[widget] = deck_info

        # 3. 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("确认")
        self.ok_button.setEnabled(False)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def toggle_select(self, widget):
        if widget in self.selected_widgets:
            self.selected_widgets.remove(widget)
            widget.set_visual_state("normal")
        else:
            if len(self.selected_widgets) < self.max_select:
                self.selected_widgets.append(widget)
                widget.set_visual_state("picked")  # 使用绿色高亮
            else:
                QApplication.beep()

        self.update_status()

    def get_status_text(self):
        count = len(self.selected_widgets)
        if self.min_select == self.max_select:
            return f"请选择 {self.min_select} 套卡组 ({count}/{self.min_select})"
        else:
            return f"请选择 {self.min_select} 到 {self.max_select} 套卡组 ({count})"

    def update_status(self):
        self.status_label.setText(self.get_status_text())
        count = len(self.selected_widgets)
        self.ok_button.setEnabled(self.min_select <= count <= self.max_select)

    def accept(self):
        self.selected_decks_info = [self.widgets_map[w] for w in self.selected_widgets]
        super().accept()

    @staticmethod
    def get_decks(parent, title, deck_pool, min_s, max_s):
        """静态方法，用于启动对话框并返回结果"""
        dialog = DeckSelector(parent, title, deck_pool, min_s, max_s)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_decks_info
        return None  # 用户取消


# --- 主应用 ---
class DeckBPSimulator(QWidget):
    def __init__(self):
        super().__init__()
        self.title = "卡组B/P对局模拟器 (PyQt6 v2.1)"
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 1300, 900)
        self.setStyleSheet(f"background-color: {BG_COLOR};")

        # 1. 加载配置
        self.deck_pool = self.load_json("deck_pool.json", "卡组资源池")
        self.my_fixed_decks_info_from_file = self.load_json("my_decks.json", "我方卡组")
        if not self.deck_pool or not self.my_fixed_decks_info_from_file:
            sys.exit(1)

        # 2. 初始化状态变量
        self.my_decks_data_current = []
        self.my_decks_changed = False

        self.game_state = "SETUP"
        self.my_decks_widgets = []
        self.opponent_decks_widgets = []
        self.opponent_decks_data = []
        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_widgets = []
        self.opponent_picked_decks_data = []

        # 3. 创建UI
        self.init_ui()
        self.connect_signals()
        self.reset_game()

    def load_json(self, filepath, name):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error_message(f"错误: 未找到配置文件 '{filepath}'。")
            return None
        except json.JSONDecodeError:
            self.show_error_message(f"错误: 配置文件 '{filepath}' 格式错误。")
            return None

    def show_error_message(self, message):
        QMessageBox.critical(self, "错误", message)

    def init_ui(self):
        """创建所有UI组件"""
        self.main_layout = QVBoxLayout(self)

        # --- 顶部控制面板 (重构) ---
        control_frame = QFrame(self)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(0, 0, 0, 0)

        # 对方卡组选择
        opp_group = QGroupBox("对方卡组")
        opp_layout = QHBoxLayout()
        self.opp_radio_random = QRadioButton("随机")
        self.opp_radio_custom = QRadioButton("自定义")
        self.opponent_radio_group = QButtonGroup(self)
        self.opponent_radio_group.addButton(self.opp_radio_random, 0)
        self.opponent_radio_group.addButton(self.opp_radio_custom, 1)
        self.opp_radio_random.setChecked(True)
        opp_layout.addWidget(self.opp_radio_random)
        opp_layout.addWidget(self.opp_radio_custom)

        self.count_slider = QSlider(Qt.Orientation.Horizontal)
        self.count_slider.setRange(4, 6)
        self.count_slider.setTickInterval(1)
        self.count_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.count_slider_label = QLabel(f"{self.count_slider.value()}")
        opp_layout.addWidget(self.count_slider)
        opp_layout.addWidget(self.count_slider_label)
        opp_group.setLayout(opp_layout)
        control_layout.addWidget(opp_group)

        # 我方卡组选择
        my_group = QGroupBox("我方卡组")
        my_layout = QHBoxLayout()
        self.my_radio_file = QRadioButton("默认")
        self.my_radio_custom = QRadioButton("自定义")
        self.my_radio_group = QButtonGroup(self)
        self.my_radio_group.addButton(self.my_radio_file, 0)
        self.my_radio_group.addButton(self.my_radio_custom, 1)
        self.my_radio_file.setChecked(True)
        my_layout.addWidget(self.my_radio_file)
        my_layout.addWidget(self.my_radio_custom)

        self.save_my_decks_button = QPushButton("保存卡组")
        self.save_my_decks_button.setEnabled(False)
        my_layout.addWidget(self.save_my_decks_button)
        my_group.setLayout(my_layout)
        control_layout.addWidget(my_group)

        # 游戏控制
        game_control_group = QGroupBox("控制")
        game_control_layout = QHBoxLayout()
        self.generate_button = QPushButton("生成对局")
        self.undo_button = QPushButton("撤回")
        self.reset_button = QPushButton("重置")
        game_control_layout.addWidget(self.generate_button)
        game_control_layout.addWidget(self.undo_button)
        game_control_layout.addWidget(self.reset_button)
        game_control_group.setLayout(game_control_layout)
        control_layout.addWidget(game_control_group)

        control_layout.addStretch(1)
        self.main_layout.addWidget(control_frame)

        # 状态/提示信息
        self.status_label = QLabel("...")
        self.status_label.setFont(QFont(FONT_NAME, 14, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # 对方卡组
        self.opponent_frame = QGroupBox("对方卡组 (待生成)")
        self.opponent_frame.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        opp_frame_layout = QVBoxLayout()
        self.custom_opponent_pick_check = QCheckBox("手动选择对方出战卡组")
        opp_frame_layout.addWidget(self.custom_opponent_pick_check, 0, Qt.AlignmentFlag.AlignRight)
        self.opponent_decks_container = QHBoxLayout()
        self.opponent_decks_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
        opp_frame_layout.addLayout(self.opponent_decks_container)
        self.opponent_frame.setLayout(opp_frame_layout)
        self.main_layout.addWidget(self.opponent_frame, 1)

        # 我方卡组
        self.my_frame = QGroupBox("我方卡组")
        self.my_frame.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        my_frame_layout = QVBoxLayout()
        self.custom_opponent_ban_check = QCheckBox("手动选择对方Ban")
        my_frame_layout.addWidget(self.custom_opponent_ban_check, 0, Qt.AlignmentFlag.AlignRight)
        self.my_decks_container = QHBoxLayout()
        self.my_decks_container.setAlignment(Qt.AlignmentFlag.AlignLeft)
        my_frame_layout.addLayout(self.my_decks_container)
        self.my_frame.setLayout(my_frame_layout)
        self.main_layout.addWidget(self.my_frame, 1)

        # 最终对战表
        self.matchup_frame = QGroupBox("最终对战")
        self.matchup_frame.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        self.matchup_container = QVBoxLayout()
        self.matchup_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.generate_matchup_button = QPushButton("随机生成对战")
        self.generate_matchup_button.hide()  # 默认隐藏
        self.matchup_container.addWidget(self.generate_matchup_button, 0, Qt.AlignmentFlag.AlignCenter)

        self.matchup_list_frame = QFrame()  # 用于容纳对战列表
        self.matchup_list_layout = QVBoxLayout(self.matchup_list_frame)
        self.matchup_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.matchup_container.addWidget(self.matchup_list_frame)

        self.matchup_frame.setLayout(self.matchup_container)
        self.main_layout.addWidget(self.matchup_frame, 1)

    def connect_signals(self):
        """连接所有UI信号"""
        self.count_slider.valueChanged.connect(lambda v: self.count_slider_label.setText(str(v)))
        self.opponent_radio_group.buttonClicked.connect(self.toggle_opponent_mode)
        self.my_radio_group.buttonClicked.connect(self.toggle_my_deck_mode)

        self.save_my_decks_button.clicked.connect(self.save_my_decks)
        self.generate_button.clicked.connect(self.start_game_flow)
        self.undo_button.clicked.connect(self.process_undo)
        self.reset_button.clicked.connect(self.reset_game)
        self.generate_matchup_button.clicked.connect(self.display_random_matchups)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.my_decks_widgets = []
        self.opponent_decks_widgets = []

    # --- UI 模式切换 ---
    def toggle_opponent_mode(self):
        is_random = self.opp_radio_random.isChecked()
        self.count_slider.setEnabled(is_random)
        self.count_slider_label.setEnabled(is_random)
        if is_random:
            self.status_label.setText("请设置卡组，然后点击'生成对局'")
        else:
            self.status_label.setText("请点击'生成对局'按钮以 [自定义] 对方卡组")

    def toggle_my_deck_mode(self):
        if self.my_radio_file.isChecked():
            self.my_decks_data_current = list(self.my_fixed_decks_info_from_file)
            self.my_decks_changed = False
            self.save_my_decks_button.setEnabled(False)
            self.reload_my_decks_ui()
            self.status_label.setText("我方卡组已重置为 [默认]")
        else:  # custom
            selected = DeckSelector.get_decks(
                self, "请选择6套 [我方] 卡组", self.deck_pool, 6, 6
            )
            if selected:
                self.my_decks_data_current = selected
                self.my_decks_changed = True
                self.save_my_decks_button.setEnabled(True)
                self.reload_my_decks_ui()
                self.status_label.setText("我方卡组已 [自定义]")
            else:
                self.my_radio_file.setChecked(True)  # 用户取消，切回"file"模式

    def save_my_decks(self):
        if not self.my_decks_changed: return
        try:
            with open("my_decks.json", 'w', encoding='utf-8') as f:
                json.dump(self.my_decks_data_current, f, indent=4, ensure_ascii=False)

            self.my_fixed_decks_info_from_file = list(self.my_decks_data_current)
            self.my_decks_changed = False
            self.save_my_decks_button.setEnabled(False)
            self.status_label.setText("成功保存 [我方卡组] 到 my_decks.json")
            self.status_label.setStyleSheet("color: green;")
        except Exception as e:
            self.show_error_message(f"保存失败: {e}")

    # --- 游戏流程 ---

    def reload_my_decks_ui(self):
        """仅刷新我方卡组UI (用于自定义)"""
        while self.my_decks_container.count():
            child = self.my_decks_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.my_decks_widgets = []
        for deck in self.my_decks_data_current:
            widget = DeckWidget(deck, ICON_SIZE)
            self.my_decks_container.addWidget(widget)
            self.my_decks_widgets.append(widget)

    def reset_game(self):
        """重置整个游戏状态和UI"""
        self.game_state = "SETUP"
        self.status_label.setText("请设置卡组，然后点击'生成对局'")
        self.status_label.setStyleSheet("color: black;")

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_widgets = []
        self.opponent_picked_decks_data = []

        self.my_decks_data_current = list(self.my_fixed_decks_info_from_file)
        self.opponent_decks_data = []

        while self.opponent_decks_container.count():
            self.opponent_decks_container.takeAt(0).widget().deleteLater()
        self.opponent_decks_widgets = []

        self.clear_layout(self.matchup_list_layout)  # 只清除对战列表

        self.opponent_frame.setTitle("对方卡组 (待生成)")
        self.reload_my_decks_ui()

        self.opp_radio_random.setChecked(True)
        self.my_radio_file.setChecked(True)
        self.custom_opponent_ban_check.setChecked(False)
        self.custom_opponent_pick_check.setChecked(False)
        self.my_decks_changed = False

        self.generate_matchup_button.hide()
        self.set_controls_locked(False)
        self.undo_button.setEnabled(False)
        self.save_my_decks_button.setEnabled(False)

    def set_controls_locked(self, locked):
        """锁定/解锁顶部的控制"""
        self.opp_radio_random.setEnabled(not locked)
        self.opp_radio_custom.setEnabled(not locked)
        self.my_radio_file.setEnabled(not locked)
        self.my_radio_custom.setEnabled(not locked)

        self.count_slider.setEnabled(not locked and self.opp_radio_random.isChecked())
        self.count_slider_label.setEnabled(not locked and self.opp_radio_random.isChecked())

        self.generate_button.setEnabled(not locked)
        self.save_my_decks_button.setEnabled(not locked and self.my_decks_changed)
        self.undo_button.setEnabled(False)  # 撤回只在特定阶段启用

        self.custom_opponent_ban_check.setEnabled(not locked)
        self.custom_opponent_pick_check.setEnabled(not locked)

    def start_game_flow(self):
        """点击“生成”按钮，开始B/P流程"""
        self.set_controls_locked(True)

        self.game_state = "BAN"
        while self.opponent_decks_container.count():
            self.opponent_decks_container.takeAt(0).widget().deleteLater()
        self.opponent_decks_widgets = []

        self.clear_layout(self.matchup_list_layout)
        self.generate_matchup_button.hide()

        for widget in self.my_decks_widgets:
            widget.set_visual_state("normal")
            try:
                widget.clicked.disconnect()
            except TypeError:
                pass

        self.my_banned_widget = None
        self.opponent_banned_widget = None
        self.my_picked_widgets = []
        self.opponent_picked_widgets = []
        self.opponent_picked_decks_data = []

        # 3. 生成对方卡组
        if self.opp_radio_random.isChecked():
            count = self.count_slider.value()
            if len(self.deck_pool) < count:
                self.show_error_message("卡组资源池中的卡组数量不足。")
                self.reset_game();
                return
            self.opponent_decks_data = random.sample(self.deck_pool, count)
        else:  # custom
            selected = DeckSelector.get_decks(
                self, "请选择 4 到 6 套 [对方] 卡组", self.deck_pool, 4, 6
            )
            if not selected:  # 用户取消
                self.reset_game();
                return
            self.opponent_decks_data = selected

        count = len(self.opponent_decks_data)
        self.opponent_frame.setTitle(f"对方卡组 ({count}套)")

        for deck in self.opponent_decks_data:
            widget = DeckWidget(deck, ICON_SIZE)
            self.opponent_decks_container.addWidget(widget)
            self.opponent_decks_widgets.append(widget)
            widget.clicked.connect(lambda w=widget: self.handle_deck_click(w, "opponent"))

        self.status_label.setText("[Ban阶段] 请点击一套 [对方卡组] 进行Ban (1/1)")
        self.status_label.setStyleSheet("color: blue;")

    def handle_deck_click(self, widget, target_team):
        """处理卡组点击事件 (Ban 和 Pick)"""

        if self.game_state == "BAN":
            if target_team == "opponent":
                if self.opponent_banned_widget: return
                self.opponent_banned_widget = widget
                widget.set_visual_state("banned")

                for w in self.opponent_decks_widgets:
                    try:
                        w.clicked.disconnect()
                    except TypeError:
                        pass

                self.undo_button.setEnabled(True)
                self.process_ai_ban()

        elif self.game_state == "CUSTOM_OPPONENT_BAN":
            if target_team == "my":
                if self.my_banned_widget: return
                self.my_banned_widget = widget
                widget.set_visual_state("banned")

                for w in self.my_decks_widgets:
                    try:
                        w.clicked.disconnect()
                    except TypeError:
                        pass

                self.undo_button.setEnabled(True)
                self.start_player_pick_phase()

        elif self.game_state == "PICK":
            if target_team == "my":
                if widget in self.my_picked_widgets:
                    self.my_picked_widgets.remove(widget)
                    widget.set_visual_state("normal")
                elif len(self.my_picked_widgets) < 3:
                    self.my_picked_widgets.append(widget)
                    widget.set_visual_state("picked")

                count = len(self.my_picked_widgets)
                self.status_label.setText(f"[Pick阶段] 请选择 3 套 [我方卡组] 出战 ({count}/3)")

                if len(self.my_picked_widgets) == 3:
                    self.game_state = "PENDING_OPPONENT_PICK"
                    self.status_label.setText("我方阵容确定！等待对方选择...")
                    self.status_label.setStyleSheet("color: green;")
                    for w in self.my_decks_widgets:
                        try:
                            w.clicked.disconnect()
                        except TypeError:
                            pass
                    self.process_ai_pick()

        elif self.game_state == "CUSTOM_OPPONENT_PICK":
            if target_team == "opponent":
                if widget in self.opponent_picked_widgets:
                    self.opponent_picked_widgets.remove(widget)
                    widget.set_visual_state("normal")
                elif len(self.opponent_picked_widgets) < 3:
                    self.opponent_picked_widgets.append(widget)
                    widget.set_visual_state("picked")

                count = len(self.opponent_picked_widgets)
                self.status_label.setText(f"[对方Pick阶段] 请选择 3 套 [对方卡组] 出战 ({count}/3)")

                if len(self.opponent_picked_widgets) == 3:
                    self.game_state = "DONE"
                    self.status_label.setText("双方阵容确定！")
                    self.status_label.setStyleSheet("color: green;")
                    self.opponent_picked_decks_data = [w.deck_info for w in self.opponent_picked_widgets]
                    for w in self.opponent_decks_widgets:
                        try:
                            w.clicked.disconnect()
                        except TypeError:
                            pass
                    self.show_final_matchup_button()

    def start_player_pick_phase(self):
        """进入玩家Pick阶段"""
        self.undo_button.setEnabled(False)  # Pick操作可逆，禁用撤回
        self.game_state = "PICK"
        self.status_label.setText("[Pick阶段] 请选择 3 套 [我方卡组] 出战 (0/3)")
        self.status_label.setStyleSheet("color: blue;")

        for w in self.my_decks_widgets:
            if w != self.my_banned_widget:
                w.clicked.connect(lambda w=w: self.handle_deck_click(w, "my"))

    # --- AI 逻辑 (入口) ---

    def process_ai_ban(self):
        """处理对方(AI或手动)的Ban选择"""
        if self.custom_opponent_ban_check.isChecked():
            self.game_state = "CUSTOM_OPPONENT_BAN"
            self.status_label.setText("[对方Ban阶段] 请点击一套 [我方卡组] 进行Ban")
            self.status_label.setStyleSheet("color: red;")
            for w in self.my_decks_widgets:
                w.clicked.connect(lambda w=w: self.handle_deck_click(w, "my"))
        else:
            available_to_ban = [w for w in self.my_decks_widgets]
            self.my_banned_widget = self.ai_logic_ban(available_to_ban)
            if self.my_banned_widget:
                self.my_banned_widget.set_visual_state("banned")
            self.start_player_pick_phase()

    def process_ai_pick(self):
        """处理对方(AI或手动)的Pick选择"""
        self.undo_button.setEnabled(False)

        if self.custom_opponent_pick_check.isChecked():
            self.game_state = "CUSTOM_OPPONENT_PICK"
            self.status_label.setText("[对方Pick阶段] 请选择 3 套 [对方卡组] 出战 (0/3)")
            self.status_label.setStyleSheet("color: red;")
            for w in self.opponent_decks_widgets:
                if w != self.opponent_banned_widget:
                    w.clicked.connect(lambda w=w: self.handle_deck_click(w, "opponent"))
        else:
            available_to_pick = [w for w in self.opponent_decks_widgets if w != self.opponent_banned_widget]
            picked_widgets = self.ai_logic_pick(available_to_pick, 3)

            self.opponent_picked_decks_data = []
            for widget in picked_widgets:
                widget.set_visual_state("picked")
                self.opponent_picked_decks_data.append(widget.deck_info)
                try:
                    widget.clicked.disconnect()
                except TypeError:
                    pass

            self.game_state = "DONE"
            self.status_label.setText("双方阵容确定！")
            self.status_label.setStyleSheet("color: green;")
            self.show_final_matchup_button()

    def process_undo(self):
        """撤回Ban操作"""
        if self.game_state != "PICK" and self.game_state != "CUSTOM_OPPONENT_PICK":
            return

        self.game_state = "BAN"
        self.status_label.setText("[Ban阶段] (已撤回) 请点击一套 [对方卡组] 进行Ban (1/1)")
        self.status_label.setStyleSheet("color: blue;")
        self.undo_button.setEnabled(False)

        for w in self.my_decks_widgets:
            try:
                w.clicked.disconnect()
            except TypeError:
                pass

        if self.my_banned_widget:
            self.my_banned_widget.set_visual_state("normal")
            self.my_banned_widget = None

        if self.opponent_banned_widget:
            self.opponent_banned_widget.set_visual_state("normal")
            self.opponent_banned_widget = None

        for w in self.opponent_decks_widgets:
            w.clicked.connect(lambda w=w: self.handle_deck_click(w, "opponent"))

    def show_final_matchup_button(self):
        """显示"生成对战"按钮"""
        self.matchup_frame.setTitle("最终对战")
        self.clear_layout(self.matchup_list_layout)
        self.generate_matchup_button.show()

    def display_random_matchups(self):
        """显示最终的1v1随机匹配"""
        self.clear_layout(self.matchup_list_layout)

        my_final_picks = [w.deck_info for w in self.my_picked_widgets]
        opp_final_picks = list(self.opponent_picked_decks_data)

        if len(my_final_picks) != 3 or len(opp_final_picks) != 3:
            self.status_label.setText("错误：双方出战卡组不为3。")
            self.status_label.setStyleSheet("color: red;")
            return

        random.shuffle(my_final_picks)
        random.shuffle(opp_final_picks)

        self.matchup_frame.setTitle("最终对战 (1v1 随机匹配)")

        for i in range(3):
            my_deck = my_final_picks[i]
            opp_deck = opp_final_picks[i]

            match_row = QWidget()
            row_layout = QGridLayout(match_row)

            # 我方 (图标 + 名称)
            my_team_layout = QHBoxLayout()
            my_icon_label = DeckWidget(my_deck, MATCHUP_ICON_SIZE)  # 使用DeckWidget创建小图标
            my_name_label = QLabel(my_deck['name'])
            my_name_label.setFont(QFont(FONT_NAME, 11, QFont.Weight.Bold))
            my_name_label.setStyleSheet("color: blue;")
            my_team_layout.addWidget(my_name_label)
            my_team_layout.addWidget(my_icon_label)

            # VS
            vs_label = QLabel(" VS ")
            vs_label.setFont(QFont(FONT_NAME, 14, QFont.Weight.Bold))

            # 对方 (图标 + 名称)
            opp_team_layout = QHBoxLayout()
            opp_icon_label = DeckWidget(opp_deck, MATCHUP_ICON_SIZE)
            opp_name_label = QLabel(opp_deck['name'])
            opp_name_label.setFont(QFont(FONT_NAME, 11, QFont.Weight.Bold))
            opp_name_label.setStyleSheet("color: red;")
            opp_team_layout.addWidget(opp_icon_label)
            opp_team_layout.addWidget(opp_name_label)

            row_layout.addLayout(my_team_layout, 0, 0, Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(vs_label, 0, 1, Qt.AlignmentFlag.AlignCenter)
            row_layout.addLayout(opp_team_layout, 0, 2, Qt.AlignmentFlag.AlignLeft)

            row_layout.setColumnStretch(0, 3)
            row_layout.setColumnStretch(1, 1)
            row_layout.setColumnStretch(2, 3)

            self.matchup_list_layout.addWidget(match_row)

    # --- 可替换的 AI 逻辑 ---

    def ai_logic_ban(self, available_decks):
        if not available_decks: return None
        return random.choice(available_decks)

    def ai_logic_pick(self, available_decks, num_to_pick):
        if len(available_decks) < num_to_pick:
            return available_decks
        return random.sample(available_decks, num_to_pick)


# --- 运行 ---
if __name__ == "__main__":
    if not os.path.exists("icons"):
        os.makedirs("icons")
        print("已创建 'icons' 文件夹。请放入卡组图标。")

    app = QApplication(sys.argv)
    ex = DeckBPSimulator()
    ex.show()
    sys.exit(app.exec())