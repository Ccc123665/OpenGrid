"""界面主题 · Swiss Spa 液态玻璃风。

设计原则：
- 纯净：近白冷调渐变打底，白色玻璃卡片浮起，克制的大圆角与极柔和投影
- 克制：全站仅一套协调中性色 + 单一冷蓝 accent；品牌红只出现在 CTA 与关闭悬停
- 呼吸：8pt 间距网格，组件之间留白充足，绝不拥挤
- 流畅：所有交互态（hover/pressed/selected）过渡自然，无突兀色块
"""

# ---- 调色板（严格遵守） ----
BG_TOP = "#F7F9FC"
BG_BOTTOM = "#ECF1F7"

SURFACE = "rgba(255,255,255,0.92)"     # 玻璃卡片
SURFACE_SOLID = "#FFFFFF"
SURFACE_HOVER = "rgba(244,247,251,0.9)"
SURFACE_ACTIVE = "rgba(235,241,251,0.95)"

LINE = "#E4EAF2"                        # 统一描边
LINE_SOFT = "#ECF0F6"

TEXT = "#1B2536"
TEXT_SUB = "#5C6B84"
TEXT_FAINT = "#93A1B8"

ACCENT = "#4E7FDE"                      # 唯一冷蓝 accent
ACCENT_SOFT = "#EBF1FB"
ACCENT_LINE = "#C9DAF3"

BRAND_RED = "#E1251B"
BRAND_RED_DARK = "#C81B12"

QSS = """
/* ================= 基础 ================= */
* {
    outline: none;
}
QWidget {
    color: #1B2536;
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow { background: #E4EAF2; }
QWidget#centralRoot { background: #E4EAF2; }

/* 窗口外壳：轻薄实色圆角容器 */
QWidget#windowContainer {
    background: qlineargradient(x1:0, y1:0, x2:0.6, y2:1,
        stop:0   #FAFCFE,
        stop:0.5 #F3F7FC,
        stop:1   #ECF1F7);
    border: 1px solid #E4EAF2;
    border-radius: 6px;
}
QWidget#windowContainer[maximized="true"] {
    border-radius: 0px;
    border: none;
}

/* ================= 标题栏（含地址/导航） ================= */
QWidget#titleBar {
    background: transparent;
    border-bottom: 1px solid #E4EAF2;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QWidget#titleBar[maximized="true"] {
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
}
QLabel#winTitle {
    background: transparent;
    color: #1B2536;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
QPushButton#winMin, QPushButton#winMax, QPushButton#winClose {
    background: transparent;
    border: none;
    border-radius: 7px;
    padding: 0px;
    min-width: 32px;  max-width: 32px;
    min-height: 24px; max-height: 24px;
}
QPushButton#winMin:hover, QPushButton#winMax:hover {
    background: rgba(78,127,222,0.10);
}
QPushButton#winClose:hover {
    background: #E1251B;
}

/* 标题栏地址栏 */
QLineEdit#addrBar {
    background: rgba(244,247,251,0.95);
    border: 1px solid #E4EAF2;
    border-radius: 6px;
    padding: 3px 8px;
    color: #5C6B84;
    font-size: 12px;
    min-height: 24px; max-height: 24px;
}
QLineEdit#addrBar:focus {
    border: 1px solid #D3DEED;
    background: #FFFFFF;
}

/* ================= 左侧导航（轻薄卡片） ================= */
QWidget#sideBar, QWidget#sideBarCollapsed {
    background: #FFFFFF;
    border: 1px solid #E4EAF2;
    border-radius: 16px;
}
QWidget#sideHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(235,241,251,0.95),
        stop:1 rgba(247,250,254,0.75));
    border: 1px solid rgba(201,218,243,0.7);
    border-radius: 12px;
}
QLabel#brandTitle { background: transparent; color: #1B2536; font-size: 15px; font-weight: 600; letter-spacing: 0.2px; }
QLabel#brandSub   { background: transparent; color: #93A1B8; font-size: 11px; }
QLabel#sectionLabel { background: transparent; color: #93A1B8; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
QLabel#countLabel { background: transparent; color: #93A1B8; font-size: 11px; }

/* 侧栏右边缘折叠把手 */
QWidget#collapseGrip {
    background: transparent;
    border: none;
}
QWidget#collapseGrip:hover { background: rgba(78,127,222,0.08); }

/* 折叠 / 展开按钮：柔和圆形 */
QPushButton#btnCollapse {
    background: transparent;
    border: none;
    border-radius: 14px;
    color: #93A1B8;
    padding: 0px;
    min-width: 28px;  max-width: 28px;
    min-height: 28px; max-height: 28px;
}
QPushButton#btnCollapse:hover { background: rgba(78,127,222,0.10); }
QPushButton#btnCollapse:pressed { background: rgba(78,127,222,0.16); }

/* 收起态账号按钮 */
QPushButton#btnAccountCollapsed {
    background: rgba(255,255,255,0.95);
    border: 1px solid rgba(228,234,242,0.9);
    border-radius: 21px;
    color: #1B2536;
    font-size: 14px;
    font-weight: 600;
    padding: 0px;
    min-width: 42px;  max-width: 42px;
    min-height: 42px; max-height: 42px;
}
QPushButton#btnAccountCollapsed:hover {
    background: #EBF1FB;
    border-color: #C9DAF3;
}

QPushButton#btnNewCollapsed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #E1251B, stop:1 #EE5245);
    border: none;
    border-radius: 19px;
    padding: 0px;
    min-width: 38px;  max-width: 38px;
    min-height: 38px; max-height: 38px;
}
QPushButton#btnNewCollapsed:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #C81B12, stop:1 #E43E33);
}
QPushButton#btnGhostCollapsed {
    background: transparent;
    border: none;
    border-radius: 19px;
    padding: 0px;
    min-width: 38px;  max-width: 38px;
    min-height: 38px; max-height: 38px;
}
QPushButton#btnGhostCollapsed:hover { background: rgba(78,127,222,0.10); }

/* ================= 账号树 ================= */
QTreeWidget {
    background: transparent;
    border: none;
    show-decoration-selected: 0;
}
QTreeWidget::item {
    height: 34px;
    padding-left: 8px;
    margin: 1px 4px;
    border-radius: 8px;
    color: #33415C;
    border: 1px solid transparent;
}
QTreeWidget::item:hover {
    background: rgba(78,127,222,0.06);
}
QTreeWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(235,241,251,0.98), stop:1 rgba(255,255,255,0.6));
    color: #1B2536;
    border-left: 3px solid #4E7FDE;
}
QTreeWidget::item:disabled { color: #B9C3D4; }
QTreeWidget::branch { background: transparent; }
QTreeWidget::branch:selected { background: transparent; }

/* ================= 标题栏工具按钮 ================= */
QPushButton#btnTool {
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    color: #5C6B84;
    min-width: 28px;  max-width: 28px;
    min-height: 26px; max-height: 26px;
}
QPushButton#btnTool:hover   { background: rgba(78,127,222,0.09); }
QPushButton#btnTool:pressed { background: rgba(78,127,222,0.15); }
QPushButton#btnTool:disabled { background: transparent; }

/* ================= 标签页 ================= */
QTabWidget::pane {
    background: #FFFFFF;
    border: 1px solid #E4EAF2;
    border-radius: 12px;
    top: -1px;
}
QTabBar { background: transparent; }
QTabBar::tab {
    background: rgba(255,255,255,0.55);
    border: 1px solid rgba(228,234,242,0.8);
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 5px 22px 5px 12px;
    margin-right: 4px;
    color: #5C6B84;
    font-size: 11px;
    min-width: 70px;
    max-width: 160px;
}
QTabBar::tab:hover:!selected {
    background: rgba(255,255,255,0.85);
    color: #1B2536;
}
QTabBar::tab:selected {
    background: rgba(255,255,255,0.98);
    color: #1B2536;
    font-weight: 600;
    border-color: rgba(201,218,243,0.95);
    border-bottom: 2px solid rgba(255,255,255,0.98);
}

/* 自定义标签关闭按钮：细线圆角 × */
QPushButton#btnTabClose {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 0px;
    margin-right: 6px;
    min-width: 16px;  max-width: 16px;
    min-height: 16px; max-height: 16px;
}
QPushButton#btnTabClose:hover {
    background: rgba(78, 127, 222, 0.10);
}

/* ================= 欢迎页 ================= */
QWidget#welcomeCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0   #FFFFFF,
        stop:0.55 #FAFCFE,
        stop:1   #EBF1FB);
    border: 1px solid #E4EAF2;
    border-radius: 14px;
}
QLabel#welcomeTitle { background: transparent; color: #1B2536; font-size: 21px; font-weight: 600; letter-spacing: 0.4px; }
QLabel#welcomeTip   { background: transparent; color: #5C6B84; font-size: 12px; line-height: 2.0; }

/* ================= 复选框 / 提示小字 / 设置分区 ================= */
QCheckBox {
    background: transparent;
    color: #33415C;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #D3DEED;
    border-radius: 4px;
    background: #FFFFFF;
}
QCheckBox::indicator:hover { border-color: #4E7FDE; }
QCheckBox::indicator:checked {
    background: #4E7FDE;
    border-color: #4E7FDE;
    image: url({CHECK_ICON});
}
QCheckBox:disabled { color: #B9C3D4; }

QWidget#perfBox {
    background: #F7FAFD;
    border: 1px solid #E4EAF2;
    border-radius: 10px;
}
QLabel#hintLabel {
    background: transparent;
    color: #8A97AC;
    font-size: 11px;
    line-height: 1.5;
}

/* ================= 输入控件 ================= */
QLineEdit, QTextEdit {
    background: rgba(255,255,255,0.92);
    border: 1px solid #E4EAF2;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: #C9DAF3;
    selection-color: #1B2536;
}
QLineEdit:hover, QTextEdit:hover { border-color: #D3DEED; }
QLineEdit:focus, QTextEdit:focus { border: 1px solid #4E7FDE; background: #FFFFFF; }
QLineEdit[readOnly="true"] {
    background: rgba(244,247,251,0.85);
    color: #5C6B84;
    border-color: rgba(228,234,242,0.7);
}
QLineEdit[readOnly="true"]:focus { border-color: rgba(228,234,242,0.7); }

QComboBox {
    background: rgba(255,255,255,0.92);
    border: 1px solid #E4EAF2;
    border-radius: 8px;
    padding: 6px 10px;
}
QComboBox:hover { border-color: #D3DEED; }
QComboBox:focus { border-color: #4E7FDE; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #E4EAF2;
    border-radius: 10px;
    padding: 4px;
    selection-background-color: #EBF1FB;
    selection-color: #1B2536;
}

/* ================= 按钮 ================= */
QPushButton {
    background: rgba(255,255,255,0.92);
    border: 1px solid #E4EAF2;
    border-radius: 10px;
    padding: 8px 14px;
    color: #33415C;
}
QPushButton:hover   { background: #F5F8FC; border-color: #D3DEED; }
QPushButton:pressed { background: #EDF2F9; }
QPushButton:disabled { color: #B9C3D4; background: rgba(248,250,252,0.8); border-color: #ECF0F6; }

/* 唯一红色 CTA */
QPushButton#btnNew, QPushButton#btnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #E1251B, stop:1 #EE5245);
    border: none;
    color: #FFFFFF;
    font-weight: 600;
    padding: 9px 14px;
    border-radius: 10px;
}
QPushButton#btnNew:hover, QPushButton#btnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #C81B12, stop:1 #E43E33);
}
QPushButton#btnNew:pressed, QPushButton#btnPrimary:pressed { background: #B81710; }

QPushButton#btnGhost {
    background: transparent;
    border: 1px solid #E4EAF2;
    color: #5C6B84;
}
QPushButton#btnGhost:hover { background: rgba(78,127,222,0.07); border-color: #D3DEED; }

/* ================= 状态栏 / 进度 ================= */
QWidget#footerBar { background: transparent; }
QLabel#statusLabel { background: transparent; color: #93A1B8; font-size: 11px; }
QProgressBar {
    background: rgba(78,127,222,0.12);
    border: none;
    border-radius: 4px;
    min-height: 7px; max-height: 7px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4E7FDE, stop:1 #7FA6EC);
    border-radius: 4px;
}

/* ================= 滚动条（隐形化） ================= */
QScrollBar:vertical { background: transparent; width: 8px; margin: 4px 2px; }
QScrollBar::handle:vertical { background: rgba(147,161,184,0.4); border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: rgba(147,161,184,0.65); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 2px 4px; }
QScrollBar::handle:horizontal { background: rgba(147,161,184,0.4); border-radius: 4px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: rgba(147,161,184,0.65); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ================= 菜单 / 提示 ================= */
QMenu {
    background: rgba(255,255,255,0.98);
    border: 1px solid #E4EAF2;
    border-radius: 10px;
    padding: 5px;
}
QMenu::item { padding: 7px 16px; border-radius: 7px; color: #33415C; }
QMenu::item:selected { background: #EBF1FB; color: #1B2536; }
QMenu::separator { height: 1px; background: #ECF0F6; margin: 4px 8px; }

QToolTip {
    background: rgba(255,255,255,0.98);
    color: #33415C;
    border: 1px solid #E4EAF2;
    border-radius: 7px;
    padding: 6px 9px;
    font-size: 12px;
}

/* ================= 对话框 ================= */
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #F7F9FC, stop:1 #ECF1F7);
}
QDialog QLabel { background: transparent; }
"""
