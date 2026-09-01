"""入口：PyQt6 单窗口 —— 无边框圆角窗口 + 浮动卡片 UI + 可折叠左侧导航 + 右侧标签页内嵌浏览器。

设计要点：
- 单窗口集中管理：所有账号/平台都在同一个窗口的内嵌浏览器里打开，不弹多窗口。
- 按账号隔离：每个账号一个 QWebEngineProfile（独立 Cookie/存储目录）。
- 标签页工作区：切换账号或平台时保留已打开的标签页，需手动关闭。
- 无边框窗口：自定义标题栏 + 12px 圆角浮动容器 + 柔和投影。
- 左侧导航可折叠收起，释放右侧工作区空间。
"""
import json
import os
import sys
import traceback
import time
import tempfile
import subprocess

# ---------------------------------------------------------------- 启动诊断 / 崩溃兜底
# 本程序为无控制台（windowed）单文件 EXE，任何启动异常都不可见。
# 这里在最早阶段安装 excepthook + 写日志 + 弹系统错误框，确保“打不开”时能看到原因。
def _log_dir() -> str:
    """跨平台日志目录：优先用户数据目录，失败则回退临时目录。"""
    try:
        import config as _cfg
        return os.path.join(_cfg.user_data_base(), "XHSManager")
    except Exception:
        return os.path.join(tempfile.gettempdir(), "XHSManager")


_LOG_DIR = _log_dir()
_LAUNCH_LOG = os.path.join(_LOG_DIR, "launch.log")


def open_path(path: str):
    """用系统文件管理器打开目录 / 用默认程序打开文件（跨平台）。"""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _fatal_error(et, ev, tb):
    txt = "".join(traceback.format_exception(et, ev, tb))
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        with open(_LAUNCH_LOG, "a", encoding="utf-8") as f:
            f.write("==== " + time.strftime("%Y-%m-%d %H:%M:%S") + " ====\n" + txt + "\n")
    except Exception:
        pass
    try:
        if sys.platform == "darwin":
            # macOS：用系统脚本弹提示框（osascript 在 .app 内也可用）
            _msg = txt[:1000].replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(
                ["osascript", "-e",
                 f'display dialog "启动失败，详情见日志：\\n{_LOG_DIR}" & "\n\n" & "{_msg}"'
                 ' with title "小红书多账号管理" buttons {"好"} default button 1'],
                timeout=15,
            )
        elif os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, txt[:3000], "XHSManager 启动失败", 0x10)
    except Exception:
        pass


sys.excepthook = _fatal_error
try:
    import threading
    threading.excepthook = lambda a: _fatal_error(a.exc_type, a.exc_value, a.exc_traceback)
except Exception:
    pass

# ---------------------------------------------------------------- QtWebEngine 运行时稳健性
# 老机器 / 远程桌面 / 云桌面往往无 GPU 且 Chromium 沙箱受限，需禁用沙箱并走软件渲染，
# 否则渲染进程会崩溃导致主窗口无法显示（表现为“打不开”）。
# 有独显的新机器可在「设置 / 备份」里开启硬件加速（重启后生效）。
# 注意：settings 只依赖 config，无 Qt 依赖，可安全地在导入 PyQt 之前读取。
import settings  # noqa: E402

_HW_ACCEL = bool(settings.get_settings().get("hardware_accel", False))

# 注意：macOS 的 Chromium 沙箱由系统层实现，不加 --no-sandbox 反而更稳定；
# Windows / Linux 下受限环境（容器、受限账户、远程桌面）才需要禁用沙箱。
if sys.platform == "darwin":
    _FLAGS = ""
else:
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    _FLAGS = " --no-sandbox --disable-dev-shm-usage"
if not _HW_ACCEL:
    _FLAGS += " --disable-gpu"
if _FLAGS.strip():
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") + _FLAGS
    )

from PyQt6.QtCore import Qt, QUrl, QEvent, QSize, QRectF
from PyQt6.QtGui import (QBrush, QColor, QFont, QDesktopServices, QPainter,
                         QPen, QBitmap, QImage)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QHBoxLayout,
    QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit, QLabel,
    QPushButton, QMessageBox, QDialog, QFormLayout, QComboBox, QTextEdit,
    QDialogButtonBox, QMenu, QFileDialog, QProgressBar, QTabWidget, QTabBar,
    QGraphicsDropShadowEffect, QSizePolicy, QScrollArea, QFrame, QCheckBox,
)

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

import config
import store
import settings as settings_mod
import theme
import icons

UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

ROLE = Qt.ItemDataRole.UserRole
STATUS_OPTIONS = ["正常", "限流", "封禁预警", "资质到期", "停用"]

SHADOW_MARGIN = 6
RESIZE_THICKNESS = 5
WINDOW_RADIUS = 6
SIDE_EXPANDED_W = 260
SIDE_COLLAPSED_W = 56


def load_backends():
    try:
        with open(config.BACKENDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("backends", [])
    except Exception:
        return []


# ---------------------------------------------------------------- 对话框
class AccountDialog(QDialog):
    """新增 / 编辑账号。"""

    def __init__(self, parent, acc=None):
        super().__init__(parent)
        self.acc = acc
        self.values = None
        self.setWindowTitle("编辑账号" if acc else "新增账号")
        self.setMinimumWidth(430)

        form = QFormLayout()
        form.setSpacing(10)
        self.e_name = QLineEdit(acc.get("name", "") if acc else "")
        self.e_name.setPlaceholderText("例如：广州公考-主号")
        self.e_group = QLineEdit(acc.get("group", "") if acc else "")
        self.e_track = QLineEdit(acc.get("track", "") if acc else "")
        self.e_owner = QLineEdit(acc.get("owner", "") if acc else "")
        self.c_status = QComboBox()
        self.c_status.addItems(STATUS_OPTIONS)
        if acc:
            self.c_status.setCurrentText(acc.get("status") or "正常")
        self.e_real = QLineEdit(acc.get("realname", "") if acc else "")
        self.e_real.setPlaceholderText("同实名/同主体关联标记（选填）")
        self.t_note = QTextEdit(acc.get("note", "") if acc else "")
        self.t_note.setFixedHeight(72)

        form.addRow("账号名称 *", self.e_name)
        form.addRow("分组", self.e_group)
        form.addRow("赛道", self.e_track)
        form.addRow("负责人", self.e_owner)
        form.addRow("状态", self.c_status)
        form.addRow("实名信息", self.e_real)
        form.addRow("备注", self.t_note)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("保存")
        bb.button(QDialogButtonBox.StandardButton.Ok).setObjectName("btnPrimary")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(14)
        lay.addLayout(form)
        lay.addWidget(bb)

    def _on_ok(self):
        name = self.e_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "账号名称不能为空")
            return
        self.values = {
            "name": name,
            "group": self.e_group.text().strip(),
            "track": self.e_track.text().strip(),
            "owner": self.e_owner.text().strip(),
            "status": self.c_status.currentText(),
            "realname": self.e_real.text().strip(),
            "note": self.t_note.toPlainText().strip(),
        }
        self.accept()


class SettingsDialog(QDialog):
    """设置 / 备份：数据备份、JSON 导出导入、打开数据目录。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.mw = parent
        self.setWindowTitle("设置 / 备份")
        self.setMinimumWidth(540)

        db = store.load_db()
        info = QLabel(
            f"版本：v{config.APP_VERSION}　账号：{store.account_count(db)}/{config.MAX_ACCOUNTS}<br>"
            f"数据目录：{config.DATA_DIR}<br>"
            f"浏览器配置目录：{config.PROFILES_DIR}"
        )
        info.setWordWrap(True)

        self.result_lbl = QLabel("")
        self.result_lbl.setWordWrap(True)
        self.result_lbl.setStyleSheet("color:#3F9B6D;")

        btn_backup = QPushButton("立即备份数据（JSON）")
        btn_export = QPushButton("导出账号台账到…")
        btn_import = QPushButton("从 JSON 导入（覆盖本地，自动备份原数据）")
        btn_dir = QPushButton("打开数据目录")

        btn_backup.clicked.connect(self._backup)
        btn_export.clicked.connect(self._export)
        btn_import.clicked.connect(self._import)
        btn_dir.clicked.connect(lambda: open_path(config.DATA_DIR))

        # ---- 性能：硬件加速开关 ----
        perf_box = QWidget()
        perf_box.setObjectName("perfBox")
        pl = QVBoxLayout(perf_box)
        pl.setContentsMargins(12, 10, 12, 10)
        pl.setSpacing(5)

        self.chk_gpu = QCheckBox("启用硬件加速（GPU 渲染）")
        self.chk_gpu.setChecked(bool(settings.get_settings().get("hardware_accel", False)))
        self.chk_gpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_gpu.setToolTip(
            "开启后网页滚动、视频更流畅，但需要机器有可用显卡驱动。\n"
            "默认关闭（软件渲染），以保证无显卡的老机器和远程桌面能正常打开。\n"
            "修改后需退出并重新打开本工具才生效。"
        )
        gpu_hint = QLabel(
            "默认关闭＝软件渲染，兼容所有机器。若本机有独立显卡且网页滚动偏卡，"
            "可勾选此项；若开启后出现白屏、闪退或打不开，请取消勾选。"
        )
        gpu_hint.setWordWrap(True)
        gpu_hint.setObjectName("hintLabel")
        self.gpu_reco = QLabel(settings.gpu_recommendation_text())
        self.gpu_reco.setWordWrap(True)
        self.gpu_reco.setObjectName("hintLabel")
        self.gpu_state = QLabel("")
        self.gpu_state.setWordWrap(True)

        pl.addWidget(self.chk_gpu)
        pl.addWidget(gpu_hint)
        pl.addWidget(self.gpu_reco)
        pl.addWidget(self.gpu_state)
        self.chk_gpu.toggled.connect(self._toggle_gpu)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        bb.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(9)
        lay.addWidget(info)
        lay.addSpacing(6)
        for b in (btn_backup, btn_export, btn_import, btn_dir):
            lay.addWidget(b)
        lay.addSpacing(4)
        lay.addWidget(perf_box)
        lay.addWidget(self.result_lbl)
        lay.addWidget(bb)

    def _toggle_gpu(self, on: bool):
        s = settings.get_settings()
        s["hardware_accel"] = bool(on)
        settings.save_settings(s)
        if on:
            self.gpu_state.setStyleSheet("color:#C0701A;")
            self.gpu_state.setText("已开启，退出并重新打开本工具后生效。若打不开请见下方说明。")
        else:
            self.gpu_state.setStyleSheet("color:#3F9B6D;")
            self.gpu_state.setText("已关闭（软件渲染），退出并重新打开本工具后生效。")

    def _backup(self):
        try:
            p = store.backup_now()
            self.result_lbl.setText(f"已备份：{p}")
        except Exception as e:  # noqa: BLE001
            self.result_lbl.setStyleSheet("color:#C0392B;")
            self.result_lbl.setText(f"备份失败：{e}")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出账号台账", "accounts.json", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            store.export_json(path)
            self.result_lbl.setStyleSheet("color:#3F9B6D;")
            self.result_lbl.setText(f"已导出：{path}")
        except Exception as e:  # noqa: BLE001
            self.result_lbl.setStyleSheet("color:#C0392B;")
            self.result_lbl.setText(f"导出失败：{e}")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择要导入的 JSON", "", "JSON 文件 (*.json)")
        if not path:
            return
        r = QMessageBox.question(
            self, "确认导入",
            "导入将覆盖当前本机账号台账（会自动备份原数据）。\n确定继续？")
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            store.import_json(path)
            self.result_lbl.setStyleSheet("color:#3F9B6D;")
            self.result_lbl.setText(f"导入成功：{path}")
            self.mw.reload_all()
        except Exception as e:  # noqa: BLE001
            self.result_lbl.setStyleSheet("color:#C0392B;")
            self.result_lbl.setText(f"导入失败：{e}")


# ---------------------------------------------------------------- 自定义绘制：品牌标识（红渐变瓷贴 + 白环，非 emoji）
class BrandMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.BRAND_RED))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 7, 7)
        # 白色圆环（与 icons.py 的 brand 图标一致）
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidthF(1.8)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        c = self.rect().center()
        p.drawEllipse(QRectF(c.x() - 6.2, c.y() - 6.2, 12.4, 12.4))
        p.drawEllipse(QRectF(c.x() - 1.6, c.y() - 1.6, 3.2, 3.2))


# ---------------------------------------------------------------- 自定义标题栏（含地址/导航）
class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.mw = parent
        self.setFixedHeight(40)
        self.setObjectName("titleBar")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(8)

        self.dot = BrandMark(self)

        # 导航控件：后退/前进/刷新/停止/地址/外部打开
        self.btn_back = QPushButton()
        self.btn_fwd = QPushButton()
        self.btn_reload = QPushButton()
        self.btn_stop = QPushButton()
        self.btn_back.setIcon(icons.icon("arrow-left", theme.TEXT_SUB, 14))
        self.btn_fwd.setIcon(icons.icon("arrow-right", theme.TEXT_SUB, 14))
        self.btn_reload.setIcon(icons.icon("refresh", theme.TEXT_SUB, 14))
        self.btn_stop.setIcon(icons.icon("stop", theme.TEXT_SUB, 14))
        for b, tip in ((self.btn_back, "后退"),
                       (self.btn_fwd, "前进"),
                       (self.btn_reload, "刷新当前页"),
                       (self.btn_stop, "停止加载")):
            b.setObjectName("btnTool")
            b.setIconSize(QSize(14, 14))
            b.setFixedSize(28, 26)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(tip)

        self.addr = QLineEdit()
        self.addr.setReadOnly(True)
        self.addr.setPlaceholderText("当前页面地址")
        self.addr.setObjectName("addrBar")

        self.btn_ext = QPushButton()
        self.btn_ext.setObjectName("btnTool")
        self.btn_ext.setIcon(icons.icon("external", theme.TEXT_SUB, 14))
        self.btn_ext.setIconSize(QSize(14, 14))
        self.btn_ext.setFixedSize(28, 26)
        self.btn_ext.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ext.setToolTip("用系统默认浏览器打开当前页面")

        self.btn_back.clicked.connect(lambda: self.mw._nav("back"))
        self.btn_fwd.clicked.connect(lambda: self.mw._nav("forward"))
        self.btn_reload.clicked.connect(lambda: self.mw._nav("reload"))
        self.btn_stop.clicked.connect(lambda: self.mw._nav("stop"))
        self.btn_ext.clicked.connect(self.mw._open_external)

        nav_lay = QHBoxLayout()
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(4)
        nav_lay.addWidget(self.btn_back)
        nav_lay.addWidget(self.btn_fwd)
        nav_lay.addWidget(self.btn_reload)
        nav_lay.addWidget(self.btn_stop)
        nav_lay.addWidget(self.addr, 1)
        nav_lay.addWidget(self.btn_ext)

        self.btn_min = QPushButton()
        self.btn_max = QPushButton()
        self.btn_close = QPushButton()
        self.btn_min.setIcon(icons.icon("minus", theme.TEXT_SUB, 12))
        self.btn_max.setIcon(icons.icon("square", theme.TEXT_SUB, 12))
        self.btn_close.setIcon(icons.icon("close", theme.TEXT_SUB, 12))
        for b, name in ((self.btn_min, "winMin"),
                        (self.btn_max, "winMax"),
                        (self.btn_close, "winClose")):
            b.setObjectName(name)
            b.setIconSize(QSize(12, 12))
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedSize(32, 24)

        lay.addWidget(self.dot)
        lay.addLayout(nav_lay, 1)
        lay.addStretch(0)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)

        self.btn_min.clicked.connect(self.mw.showMinimized)
        self.btn_max.clicked.connect(self.mw._toggle_max)
        self.btn_close.clicked.connect(self.mw.close)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            # 在按钮/地址栏上按下时不拖动窗口，避免影响点击和聚焦
            child = self.childAt(ev.pos())
            if isinstance(child, (QPushButton, QLineEdit)):
                super().mousePressEvent(ev)
                return
            self.mw.window().windowHandle().startSystemMove()
        else:
            super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        self.mw._toggle_max()


# ---------------------------------------------------------------- 侧边栏折叠把手（导航栏右侧）
class CollapseGrip(QWidget):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.setFixedWidth(8)
        self.setCursor(Qt.CursorShape.SplitHCursor)
        self.setToolTip("点击收起/展开侧边栏")
        self.setObjectName("collapseGrip")

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(200, 212, 228))
        pen.setWidth(1)
        p.setPen(pen)
        x = self.width() / 2
        p.drawLine(int(x), 24, int(x), self.height() - 24)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.mw._set_side_collapsed(not self.mw.side_collapsed)


# ---------------------------------------------------------------- 标签页关闭按钮（自定义柔和 ×）
class TabCloseButton(QPushButton):
    """替换 Qt 默认生硬的方块关闭按钮：细线圆角 ×，hover 加深。"""
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.setObjectName("btnTabClose")
        self.setIcon(icons.icon("close", theme.TEXT_FAINT, 10, 1.4))
        self.setIconSize(QSize(10, 10))
        self.setFixedSize(16, 16)
        self.setToolTip("关闭标签页")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clicked.connect(self.mw._close_tab_by_button)

    def enterEvent(self, ev):
        self.setIcon(icons.icon("close", theme.TEXT_SUB, 10, 1.4))
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self.setIcon(icons.icon("close", theme.TEXT_FAINT, 10, 1.4))
        super().leaveEvent(ev)


# ---------------------------------------------------------------- 自定义 WebEnginePage：接管弹窗/新标签页
class WebPage(QWebEnginePage):
    """拦截 target=_blank 与 JS window.open，把新窗口请求转成工具内标签页。

    Qt WebEngine 默认对弹窗返回 None，导致点击「聊天卡片」「发布」等
    需要新开标签页的链接无任何反应。通过 createWindow 返回一个已放入
    标签页的 page，即可正常打开。
    """

    def __init__(self, profile, parent=None, mw=None):
        super().__init__(profile, parent)
        self.mw = mw
        # 渲染进程异常（崩溃/卡死）信号：开启硬件加速后若显卡驱动不兼容，
        # Chromium 渲染进程会异常退出。捕获后由主窗口自动回退软件渲染。
        try:
            self.renderProcessTerminated.connect(self._on_render_terminated)
        except Exception:
            pass

    def _on_render_terminated(self, status):
        if self.mw is not None:
            self.mw.on_render_process_terminated(status)

    def createWindow(self, _type):
        if self.mw is None:
            return None
        return self.mw._create_new_tab_page(self.profile())


# ---------------------------------------------------------------- 可视右下角 resize handle
class ResizeHandle(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setToolTip("拖动调整窗口大小")

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(180, 195, 215))
        pen.setWidth(2)
        p.setPen(pen)
        w, h = self.width(), self.height()
        # 三条斜线
        for i in range(3):
            offset = 4 + i * 4
            p.drawLine(w - offset, h, w, h - offset)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            wh = self.window().windowHandle()
            if wh:
                wh.startSystemResize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge)


# ---------------------------------------------------------------- 边缘拉伸控件
class ResizeGrip(QWidget):
    CURSORS = {
        Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeBDiagCursor,
        Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
        Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
        Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
        Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
        Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
    }

    def __init__(self, parent, edges):
        super().__init__(parent)
        self.edges = edges
        self.setCursor(self.CURSORS[edges])
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            wh = self.window().windowHandle()
            if wh:
                wh.startSystemResize(self.edges)


# ---------------------------------------------------------------- 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.backends = load_backends()
        self.profiles = {}
        self.tab_views = {}
        self.side_collapsed = False

        # ---- 右侧工作区 ----
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)  # 用自定义 TabCloseButton，不用默认方块 ×
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setDocumentMode(False)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_welcome())
        tab_wrap = QWidget()
        tw_lay = QVBoxLayout(tab_wrap)
        tw_lay.setContentsMargins(0, 0, 0, 0)
        tw_lay.addWidget(self.tabs)
        self.stack.addWidget(tab_wrap)

        self._build_ui()
        self.reload_all()

        # 恢复折叠状态
        s = settings_mod.get_settings()
        collapsed = s.get("side_collapsed", False)
        if collapsed:
            self._set_side_collapsed(True, save=False)
        self._restore_last()

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(1320, 860)
        self.setMinimumSize(960, 660)

        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        self.central_lay = QVBoxLayout(central)
        self.central_lay.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN,
                                            SHADOW_MARGIN, SHADOW_MARGIN)
        self.central_lay.setSpacing(0)

        self.container = QWidget()
        self.container.setObjectName("windowContainer")
        container_lay = QVBoxLayout(self.container)
        container_lay.setContentsMargins(0, 0, 0, 0)
        container_lay.setSpacing(0)

        self.title_bar = TitleBar(self)
        container_lay.addWidget(self.title_bar)
        # 标题栏已集成地址/导航控件，给主窗口保留快捷引用
        self.addr = self.title_bar.addr
        self.btn_back = self.title_bar.btn_back
        self.btn_fwd = self.title_bar.btn_fwd
        self.btn_reload = self.title_bar.btn_reload
        self.btn_stop = self.title_bar.btn_stop
        self.btn_ext = self.title_bar.btn_ext

        self.content = QWidget()
        content_lay = QVBoxLayout(self.content)
        content_lay.setContentsMargins(8, 8, 8, 8)
        content_lay.setSpacing(8)
        self.main_content = self._build_main_content()
        content_lay.addWidget(self.main_content, 1)

        footer = QWidget()
        footer.setObjectName("footerBar")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(4, 2, 4, 2)
        fl.setSpacing(10)
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusLabel")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(140)
        self.progress.setVisible(False)
        fl.addWidget(self.status_lbl, 1)
        fl.addWidget(self.progress)
        content_lay.addWidget(footer)

        container_lay.addWidget(self.content, 1)
        self.central_lay.addWidget(self.container)

        # 右下角可视 resize 手柄（叠在 content 上）
        self.resize_handle = ResizeHandle(self.content)
        self.resize_handle.raise_()

        self._apply_window_shadow()
        self._create_resize_grips(central)

    def _build_main_content(self) -> QWidget:
        w = QWidget()
        w.setObjectName("mainContent")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.side = self._build_side()
        self.collapse_grip = CollapseGrip(self)
        lay.addWidget(self.side)
        lay.addWidget(self.collapse_grip)
        lay.addWidget(self._build_main(), 1)
        return w

    def _build_side(self) -> QWidget:
        side = QWidget()
        side.setObjectName("sideBar")
        side.setFixedWidth(SIDE_EXPANDED_W)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(10, 10, 10, 10)
        side_lay.setSpacing(10)

        # 模块头
        hdr = QWidget()
        hdr.setObjectName("sideHeader")
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(3)
        t = QLabel(config.APP_NAME)
        t.setObjectName("brandTitle")
        s = QLabel(f"多账号集中管理 · v{config.APP_VERSION}")
        s.setObjectName("brandSub")
        hl.addWidget(t)
        hl.addWidget(s)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("搜索账号 / 分组 / 负责人")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.addAction(
            icons.icon("search", theme.TEXT_FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.filter_edit.textChanged.connect(self._reload_tree)

        sec = QLabel("账号")
        sec.setObjectName("sectionLabel")
        self.count_lbl = QLabel(f"0 / {config.MAX_ACCOUNTS}")
        self.count_lbl.setObjectName("countLabel")
        head_row = QHBoxLayout()
        head_row.addWidget(sec)
        head_row.addStretch(1)
        head_row.addWidget(self.count_lbl)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(16)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_ctx_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double)

        self.btn_new = QPushButton("  新账号")
        self.btn_new.setObjectName("btnNew")
        self.btn_new.setIcon(icons.icon("plus", "#FFFFFF"))
        self.btn_new.setIconSize(QSize(15, 15))
        self.btn_new.setFixedHeight(36)
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self._new_account)

        self.btn_set = QPushButton("  设置 / 备份")
        self.btn_set.setObjectName("btnGhost")
        self.btn_set.setIcon(icons.icon("sliders", theme.TEXT_SUB))
        self.btn_set.setIconSize(QSize(15, 15))
        self.btn_set.setFixedHeight(32)
        self.btn_set.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set.clicked.connect(self._open_settings)

        side_lay.addWidget(hdr)
        side_lay.addWidget(self.filter_edit)
        side_lay.addLayout(head_row)
        side_lay.addWidget(self.tree, 1)
        side_lay.addWidget(self.btn_new)
        side_lay.addWidget(self.btn_set)

        return side

    def _build_collapsed_side(self) -> QWidget:
        """收起态的窄侧边栏（只保留账号入口 + 展开按钮）。"""
        side = QWidget()
        side.setObjectName("sideBarCollapsed")
        side.setFixedWidth(SIDE_COLLAPSED_W)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(6, 10, 6, 10)
        lay.setSpacing(10)

        # 展开按钮
        self.btn_expand = QPushButton()
        self.btn_expand.setObjectName("btnCollapse")
        self.btn_expand.setIcon(icons.icon("chevrons-right", theme.TEXT_FAINT))
        self.btn_expand.setIconSize(QSize(15, 15))
        self.btn_expand.setToolTip("展开侧边栏")
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.clicked.connect(lambda: self._set_side_collapsed(False))
        lay.addWidget(self.btn_expand, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 账号列表占位容器
        self.collapsed_list = QWidget()
        self.collapsed_list.setObjectName("collapsedList")
        self.collapsed_list_lay = QVBoxLayout(self.collapsed_list)
        self.collapsed_list_lay.setContentsMargins(0, 0, 0, 0)
        self.collapsed_list_lay.setSpacing(8)
        self.collapsed_list_lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.collapsed_list)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(scroll, 1)

        self.btn_new_collapsed = QPushButton()
        self.btn_new_collapsed.setObjectName("btnNewCollapsed")
        self.btn_new_collapsed.setIcon(icons.icon("plus", "#FFFFFF"))
        self.btn_new_collapsed.setIconSize(QSize(16, 16))
        self.btn_new_collapsed.setToolTip("新账号")
        self.btn_new_collapsed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_collapsed.clicked.connect(self._new_account)

        self.btn_set_collapsed = QPushButton()
        self.btn_set_collapsed.setObjectName("btnGhostCollapsed")
        self.btn_set_collapsed.setIcon(icons.icon("sliders", theme.TEXT_SUB))
        self.btn_set_collapsed.setIconSize(QSize(16, 16))
        self.btn_set_collapsed.setToolTip("设置 / 备份")
        self.btn_set_collapsed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_collapsed.clicked.connect(self._open_settings)

        lay.addWidget(self.btn_new_collapsed, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self.btn_set_collapsed, alignment=Qt.AlignmentFlag.AlignHCenter)

        return side

    def _set_side_collapsed(self, collapsed: bool, save: bool = True):
        if self.side_collapsed == collapsed:
            return
        self.side_collapsed = collapsed
        lay = self.main_content.layout()

        if collapsed:
            if not hasattr(self, "side_collapsed_widget"):
                self.side_collapsed_widget = self._build_collapsed_side()
            lay.removeWidget(self.side)
            self.side.hide()
            lay.insertWidget(0, self.side_collapsed_widget)
            self.side_collapsed_widget.show()
            self._refresh_collapsed_list()
        else:
            if hasattr(self, "side_collapsed_widget"):
                lay.removeWidget(self.side_collapsed_widget)
                self.side_collapsed_widget.hide()
            lay.insertWidget(0, self.side)
            self.side.show()
            self._reload_tree()

        if save:
            s = settings_mod.get_settings()
            s["side_collapsed"] = collapsed
            settings_mod.save_settings(s)

    def _refresh_collapsed_list(self):
        if not hasattr(self, "collapsed_list_lay"):
            return
        # 清空已有按钮
        while self.collapsed_list_lay.count():
            item = self.collapsed_list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        db = store.load_db()
        for acc in store.list_accounts(db):
            btn = QPushButton(self._account_initial(acc.get("name", "账号")))
            btn.setObjectName("btnAccountCollapsed")
            btn.setFixedSize(42, 42)
            btn.setToolTip(acc.get("name", ""))
            btn.setProperty("aid", acc["id"])
            btn.clicked.connect(lambda _c, a=acc["id"]: self._expand_and_open_account(a))
            self.collapsed_list_lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.collapsed_list_lay.addStretch(1)

    def _expand_and_open_account(self, aid: str):
        self._set_side_collapsed(False)
        # 在树中找到该账号并展开
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            it = root.child(i)
            d = it.data(0, ROLE)
            if d and d.get("id") == aid:
                it.setExpanded(True)
                self.tree.scrollToItem(it)
                break

    @staticmethod
    def _account_initial(name: str) -> str:
        name = name.strip()
        if not name:
            return "账"
        # 优先取中文字符，否则取字母
        for ch in name:
            if "\u4e00" <= ch <= "\u9fff":
                return ch
        return name[0].upper()

    def _build_main(self) -> QWidget:
        main = QWidget()
        main.setObjectName("mainArea")
        lay = QVBoxLayout(main)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.stack, 1)

        return main

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        w.setObjectName("welcomeCard")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        title = QLabel("多账号集中管理")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tip = QLabel(
            "1. 左下角「+ 新账号」添加账号<br>"
            "2. 左侧展开账号，点击要使用的<b>平台</b><br>"
            "3. 在打开的标签页中<b>手动登录</b>，登录态按账号独立保存<br>"
            "4. 切换账号/平台会<b>保留已打开的标签页</b>，需手动关闭"
        )
        tip.setObjectName("welcomeTip")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setWordWrap(True)

        lay.addWidget(title)
        lay.addWidget(tip)
        return w

    # ---------------- 圆角遮罩 / 拉伸 ----------------
    def _apply_window_shadow(self):
        # 实色窗口已不再使用投影特效（投影会拖慢软件渲染下的合成）
        pass

    def _create_resize_grips(self, parent):
        self.grips = []
        edges = [
            (Qt.Edge.LeftEdge | Qt.Edge.TopEdge,),
            (Qt.Edge.TopEdge,),
            (Qt.Edge.RightEdge | Qt.Edge.TopEdge,),
            (Qt.Edge.LeftEdge,),
            (Qt.Edge.RightEdge,),
            (Qt.Edge.LeftEdge | Qt.Edge.BottomEdge,),
            (Qt.Edge.BottomEdge,),
            (Qt.Edge.RightEdge | Qt.Edge.BottomEdge,),
        ]
        for e in edges:
            g = ResizeGrip(parent, e[0])
            self.grips.append(g)
        self._position_grips()

    def _position_grips(self):
        if not self.grips:
            return
        w = self.centralWidget().width()
        h = self.centralWidget().height()
        t = RESIZE_THICKNESS
        rects = [
            (0, 0, t, t),                                    # LT
            (t, 0, w - 2 * t, t),                            # T
            (w - t, 0, t, t),                                # RT
            (0, t, t, h - 2 * t),                            # L
            (w - t, t, t, h - 2 * t),                        # R
            (0, h - t, t, t),                                # LB
            (t, h - t, w - 2 * t, t),                        # B
            (w - t, h - t, t, t),                            # RB
        ]
        for g, (x, y, cw, ch) in zip(self.grips, rects):
            g.setGeometry(x, y, cw, ch)

    # ---------------- 窗口状态 ----------------
    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _sync_window_state(self):
        is_max = self.isMaximized() or self.isFullScreen()
        self.title_bar.btn_max.setIcon(
            icons.icon("restore" if is_max else "square", theme.TEXT_SUB))
        self.title_bar.setProperty("maximized", is_max)
        self.title_bar.style().unpolish(self.title_bar)
        self.title_bar.style().polish(self.title_bar)
        self.container.setProperty("maximized", is_max)
        self.container.style().unpolish(self.container)
        self.container.style().polish(self.container)

        if is_max:
            self.central_lay.setContentsMargins(0, 0, 0, 0)
            self._update_mask()
            for g in self.grips:
                g.hide()
            if hasattr(self, "resize_handle"):
                self.resize_handle.hide()
        else:
            self.central_lay.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN,
                                                SHADOW_MARGIN, SHADOW_MARGIN)
            self._update_mask()
            for g in self.grips:
                g.show()
            if hasattr(self, "resize_handle"):
                self.resize_handle.show()
        self._position_grips()
        self._position_resize_handle()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._position_grips()
        self._position_resize_handle()
        self._update_mask()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._update_mask()

    def _update_mask(self):
        """用几何遮罩做圆角（硬件友好），替代整窗透明背景的 per-pixel alpha 合成。"""
        if self.isMaximized() or self.isFullScreen():
            self.clearMask()
            return
        r = self.rect()
        bmp = QBitmap(r.size())
        bmp.clear()
        p = QPainter(bmp)
        p.setBrush(Qt.GlobalColor.black)
        p.setPen(Qt.GlobalColor.black)
        p.drawRoundedRect(r.adjusted(0, 0, -1, -1), WINDOW_RADIUS, WINDOW_RADIUS)
        p.end()
        self.setMask(bmp)

    def _position_resize_handle(self):
        if hasattr(self, "resize_handle") and self.resize_handle.isVisible():
            # 内移一个窗口圆角距离，避免被圆角遮罩裁掉
            self.resize_handle.move(
                self.content.width() - self.resize_handle.width() - 2 - WINDOW_RADIUS,
                self.content.height() - self.resize_handle.height() - 2 - WINDOW_RADIUS,
            )
            self.resize_handle.raise_()

    def changeEvent(self, ev):
        if ev.type() == QEvent.Type.WindowStateChange:
            self._sync_window_state()
        super().changeEvent(ev)

    # ---------------- 树 ----------------
    def _reload_tree(self, _text=None):
        filt = (self.filter_edit.text() or "").strip().lower()

        expanded = set()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            it = root.child(i)
            d = it.data(0, ROLE)
            if d and it.isExpanded():
                expanded.add(d["id"])

        self.tree.clear()
        db = store.load_db()
        accounts = store.list_accounts(db)
        bold = QFont()
        bold.setBold(True)

        for acc in accounts:
            hay = f"{acc.get('name','')} {acc.get('group','')} " \
                  f"{acc.get('owner','')} {acc.get('track','')}".lower()
            if filt and filt not in hay:
                continue

            item = QTreeWidgetItem([acc.get("name", "")])
            item.setData(0, ROLE, {"type": "account", "id": acc["id"]})
            item.setFont(0, bold)
            st = acc.get("status") or "正常"
            item.setToolTip(
                0,
                f"分组：{acc.get('group') or '-'}　负责人：{acc.get('owner') or '-'}\n"
                f"赛道：{acc.get('track') or '-'}　状态：{st}\n"
                f"实名：{acc.get('realname') or '-'}　备注：{acc.get('note') or '-'}",
            )
            if st != "正常":
                item.setForeground(0, QBrush(QColor(theme.BRAND_RED)))

            for be in self.backends:
                url = be.get("url", "")
                # 不再渲染 emoji icon，仅显示平台名称
                child = QTreeWidgetItem([be["name"]])
                child.setData(0, ROLE, {
                    "type": "backend",
                    "account_id": acc["id"],
                    "key": be["key"],
                    "url": url,
                })
                if not url:
                    child.setDisabled(True)
                    child.setToolTip(0, be.get("desc") or "暂未配置地址（预留拓展端口）")
                else:
                    child.setToolTip(0, f"{be.get('desc','')}\n{url}")
                item.addChild(child)

            self.tree.addTopLevelItem(item)
            if acc["id"] in expanded:
                item.setExpanded(True)

        self.count_lbl.setText(f"{len(accounts)} / {config.MAX_ACCOUNTS}")
        if self.side_collapsed:
            self._refresh_collapsed_list()

    def reload_all(self):
        self._reload_tree()
        self._update_status()

    # ---------------- 交互 ----------------
    def _on_item_clicked(self, item, _col):
        d = item.data(0, ROLE)
        if not d:
            return
        if d["type"] == "account":
            item.setExpanded(not item.isExpanded())
        else:
            self._open(d["account_id"], d["key"], d["url"])

    def _on_item_double(self, item, _col):
        d = item.data(0, ROLE)
        if d and d["type"] == "account":
            self._edit_account(d["id"])

    def _on_ctx_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        d = item.data(0, ROLE)
        if not d:
            return
        menu = QMenu(self)

        if d["type"] == "account":
            a_edit = menu.addAction("编辑账号")
            a_del = menu.addAction("删除账号")
            menu.addSeparator()
            a_clear = menu.addAction("清除该账号浏览器数据（退出登录）")
            chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if chosen == a_edit:
                self._edit_account(d["id"])
            elif chosen == a_del:
                self._delete_account(d["id"])
            elif chosen == a_clear:
                self._clear_profile(d["id"])
        else:
            a_open = menu.addAction("在外部浏览器打开")
            chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if chosen == a_open and d.get("url"):
                QDesktopServices.openUrl(QUrl(d["url"]))

    # ---------------- 账号 CRUD ----------------
    def _new_account(self):
        db = store.load_db()
        if store.account_count(db) >= config.MAX_ACCOUNTS:
            QMessageBox.warning(
                self, "已达上限",
                f"账号数量已达上限 {config.MAX_ACCOUNTS} 个，无法继续添加。\n"
                f"本工具定位为 5–20 账号的轻量集中管理，如需更多请删除不用的账号。")
            return
        dlg = AccountDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.values:
            return
        db = store.load_db()
        try:
            acc = store.add_account(db, dlg.values["name"])
        except ValueError as e:
            QMessageBox.warning(self, "无法添加", str(e))
            return
        store.update_account(db, acc["id"], dlg.values)
        self._reload_tree()
        if self.side_collapsed:
            self._refresh_collapsed_list()

    def _edit_account(self, aid):
        db = store.load_db()
        acc = store.get_account(db, aid)
        if not acc:
            return
        dlg = AccountDialog(self, acc)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.values:
            return
        db = store.load_db()
        store.update_account(db, aid, dlg.values)
        self._reload_tree()
        self._refresh_tab_labels()
        self._update_status()

    def _delete_account(self, aid):
        db = store.load_db()
        acc = store.get_account(db, aid)
        if not acc:
            return
        r = QMessageBox.question(
            self, "删除账号",
            f"确定删除账号「{acc['name']}」？\n"
            f"该账号已打开的标签页会一并关闭，浏览器登录态也会清除。")
        if r != QMessageBox.StandardButton.Yes:
            return
        self._close_tabs_of_account(aid)
        store.delete_account(db, aid)
        store.clear_account_profile(aid)
        prof = self.profiles.pop(aid, None)
        if prof is not None:
            prof.deleteLater()
        self.reload_all()

    def _clear_profile(self, aid):
        db = store.load_db()
        acc = store.get_account(db, aid)
        if not acc:
            return
        r = QMessageBox.question(
            self, "清除浏览器数据",
            f"将清除「{acc['name']}」的登录态、Cookie 与缓存，需重新登录。\n确定继续？")
        if r != QMessageBox.StandardButton.Yes:
            return
        self._close_tabs_of_account(aid)
        store.clear_account_profile(aid)
        prof = self.profiles.pop(aid, None)
        if prof is not None:
            prof.deleteLater()
        QMessageBox.information(self, "完成", f"已清除「{acc['name']}」的浏览器数据")
        self._update_status()

    def _open_settings(self):
        SettingsDialog(self).exec()

    # ---------------- 内嵌浏览器 + 标签页 ----------------
    def _profile_for(self, aid: str) -> QWebEngineProfile:
        prof = self.profiles.get(aid)
        if prof is not None:
            return prof

        base = config.profile_path(aid)
        prof = QWebEngineProfile(aid, self)
        prof.setPersistentStoragePath(base)
        prof.setCachePath(os.path.join(base, "cache"))
        prof.setHttpUserAgent(UA_CHROME)
        prof.setHttpAcceptLanguage("zh-CN,zh;q=0.9")
        try:
            prof.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        except Exception:  # noqa: BLE001
            pass
        try:
            prof.setThirdPartyCookiePolicy(
                QWebEngineProfile.ThirdPartyCookiePolicy.AlwaysAllowThirdPartyCookies)
        except Exception:  # noqa: BLE001
            pass
        try:
            prof.setSpellCheckEnabled(False)
        except Exception:  # noqa: BLE001
            pass

        self.profiles[aid] = prof
        return prof

    def _make_view(self, aid: str) -> QWebEngineView:
        prof = self._profile_for(aid)
        view = QWebEngineView()
        page = WebPage(prof, view, mw=self)
        view.setPage(page)
        self._connect_view(view)
        return view

    def _connect_view(self, view: QWebEngineView):
        """统一连接浏览器视图信号。"""
        view.urlChanged.connect(lambda _u, v=view: self._on_view_url(v))
        view.loadProgress.connect(lambda p, v=view: self._on_view_progress(v, p))
        view.loadFinished.connect(lambda ok, v=view: self._on_view_finished(v, ok))

    def on_render_process_terminated(self, status):
        """渲染进程异常退出兜底：开启硬件加速后若显卡不兼容导致崩溃，
        自动写回软件渲染设置并提示用户重启，避免反复打不开 / 白屏。
        """
        # status 可能是枚举或 int，统一取数值
        try:
            code = int(status)
        except Exception:
            code = int(getattr(status, "value", 0))
        # 0 = NormalTermination（正常退出，不处理）；1/2/3 视为异常
        if code == 0:
            return
        s = settings.get_settings()
        if not s.get("hardware_accel", False):
            return  # 已是软件渲染，异常另有原因，不干预
        # 回退：关闭硬件加速并持久化
        s["hardware_accel"] = False
        s["_gpu_probed"] = True
        settings.save_settings(s)
        if not getattr(self, "_gpu_fallback_shown", False):
            self._gpu_fallback_shown = True
            QMessageBox.warning(
                self, "已自动切换回软件渲染",
                "检测到网页渲染进程异常（可能与当前显卡驱动不兼容）。\n\n"
                "已自动关闭「硬件加速」并保存，请退出并重新打开本工具，"
                "之后将走稳定的软件渲染模式。\n\n"
                "如需再次尝试硬件加速，可在「设置 / 备份」中手动勾选。")

    def _create_new_tab_page(self, profile: QWebEngineProfile) -> WebPage:
        """为 target=_blank / window.open 创建新标签页，并返回其 page。"""
        aid = next((k for k, p in self.profiles.items() if p == profile), "")
        view = QWebEngineView()
        page = WebPage(profile, view, mw=self)
        view.setPage(page)
        self._connect_view(view)

        db = store.load_db()
        acc = store.get_account(db, aid) if aid else None
        name = acc.get("name", "未知账号") if acc else "新页面"
        label = f"{name} · 新页面"

        ident = (aid, "__popup__", id(view))
        view.setProperty("aid", aid)
        view.setProperty("bkey", "__popup__")
        view.setProperty("ident", ident)

        self.tab_views[ident] = view
        self.tabs.addTab(view, label)
        idx = self.tabs.indexOf(view)
        self.tabs.tabBar().setTabButton(
            idx, QTabBar.ButtonPosition.RightSide, TabCloseButton(self))
        self.tabs.setCurrentWidget(view)
        return page

    def _open(self, aid: str, key: str, url: str):
        if not url:
            QMessageBox.information(
                self, "尚未配置",
                "该后台还没有配置地址（预留拓展端口）。\n"
                "在 backends.json 中补上 url 后重启即可启用。")
            return
        db = store.load_db()
        acc = store.get_account(db, aid)
        if not acc:
            self._reload_tree()
            return

        ident = (aid, key)
        view = self.tab_views.get(ident)
        if view is None:
            be = next((b for b in self.backends if b.get("key") == key), None)
            label = f"{acc.get('name','')} · {be.get('name','') if be else key}"
            view = self._make_view(aid)
            view.setProperty("aid", aid)
            view.setProperty("bkey", key)
            view.setProperty("ident", ident)
            view.load(QUrl(url))
            self.tab_views[ident] = view
            self.tabs.addTab(view, label)
            idx = self.tabs.indexOf(view)
            self.tabs.tabBar().setTabButton(
                idx, QTabBar.ButtonPosition.RightSide, TabCloseButton(self))
            self.tabs.setCurrentWidget(view)
        else:
            self.tabs.setCurrentWidget(view)

        self.stack.setCurrentIndex(1)
        self._update_status()
        self._sync_nav()

        s = settings_mod.get_settings()
        s["last_account_id"] = aid
        s["last_backend_key"] = key
        settings_mod.save_settings(s)

    def _close_tab_by_button(self):
        """自定义关闭按钮被点击时，找到它所在的 tab 并关闭。"""
        btn = self.sender()
        if btn is None:
            return
        tb = self.tabs.tabBar()
        for i in range(self.tabs.count()):
            if tb.tabButton(i, QTabBar.ButtonPosition.RightSide) == btn:
                self._close_tab(i)
                return

    def _close_tab(self, idx: int):
        w = self.tabs.widget(idx)
        if w is None:
            return
        self.tabs.removeTab(idx)
        ident = w.property("ident") or (w.property("aid"), w.property("bkey"))
        self.tab_views.pop(ident, None)
        w.setParent(None)
        w.deleteLater()

        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(0)
        self._update_status()
        self._sync_nav()

    def _on_tab_changed(self, idx: int):
        """当前标签激活渲染，其余后台标签冻结以省 CPU（针对无 GPU 软件渲染的老机器）。"""
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if w is None:
                continue
            page = w.page() if hasattr(w, "page") else None
            if page is None:
                continue
            if i == idx:
                page.setLifecycleState(QWebEnginePage.LifecycleState.Active)
            else:
                page.setLifecycleState(QWebEnginePage.LifecycleState.Frozen)
        self._sync_nav()
        self._update_status()

    def _close_tabs_of_account(self, aid: str):
        for ident in [k for k in self.tab_views if k[0] == aid]:
            v = self.tab_views.pop(ident)
            i = self.tabs.indexOf(v)
            if i >= 0:
                self.tabs.removeTab(i)
            v.setParent(None)
            v.deleteLater()
        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(0)

    def _refresh_tab_labels(self):
        db = store.load_db()
        for ident, v in self.tab_views.items():
            aid = ident[0]
            key = ident[1]
            acc = store.get_account(db, aid)
            if key == "__popup__":
                name = acc.get("name", "未知账号") if acc else "新页面"
                i = self.tabs.indexOf(v)
                if i >= 0:
                    self.tabs.setTabText(i, f"{name} · 新页面")
                continue
            be = next((b for b in self.backends if b.get("key") == key), None)
            if acc and be:
                i = self.tabs.indexOf(v)
                if i >= 0:
                    self.tabs.setTabText(i, f"{acc.get('name','')} · {be.get('name','')}")

    def _restore_last(self):
        s = settings_mod.get_settings()
        aid = s.get("last_account_id") or ""
        key = s.get("last_backend_key") or ""
        if not aid:
            return
        db = store.load_db()
        if not store.get_account(db, aid):
            return
        be = next((b for b in self.backends
                   if b.get("key") == key and b.get("url")), None)
        if be is None:
            be = next((b for b in self.backends if b.get("url")), None)
        if be:
            self._open(aid, be["key"], be["url"])

    # ---------------- 视图信号 / 导航 ----------------
    def _cur_view(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def _nav(self, method: str):
        v = self._cur_view()
        if v is not None:
            getattr(v, method)()

    def _on_view_url(self, v):
        if self.tabs.currentWidget() is not v:
            return
        self.addr.setText(v.url().toString())
        self._sync_nav_buttons(v)

    def _on_view_progress(self, v, p):
        if self.tabs.currentWidget() is not v:
            return
        self.progress.setVisible(p < 100)
        self.progress.setValue(p)

    def _on_view_finished(self, v, ok):
        if self.tabs.currentWidget() is not v:
            return
        self.progress.setVisible(False)
        self._sync_nav_buttons(v)
        if not ok:
            self.status_lbl.setText("页面加载失败，请检查网络")

    def _sync_nav_buttons(self, v):
        h = v.history()
        self.btn_back.setEnabled(h.canGoBack())
        self.btn_fwd.setEnabled(h.canGoForward())

    def _sync_nav(self):
        v = self._cur_view()
        if v is None:
            self.addr.clear()
            self.btn_back.setEnabled(False)
            self.btn_fwd.setEnabled(False)
            self.progress.setVisible(False)
            return
        self.addr.setText(v.url().toString())
        self._sync_nav_buttons(v)

    def _open_external(self):
        v = self._cur_view()
        u = v.url().toString() if v else ""
        if u and u != "about:blank":
            QDesktopServices.openUrl(QUrl(u))
        else:
            QMessageBox.information(self, "提示", "当前没有可打开的页面")

    def _update_status(self):
        v = self._cur_view()
        if v is None:
            self.status_lbl.setText(
                "未打开任何后台 — 在左侧选择账号下的平台即可打开标签页"
                + (f"（当前已开 {self.tabs.count()} 个）" if self.tabs.count() else "")
            )
            return
        db = store.load_db()
        acc = store.get_account(db, v.property("aid"))
        key = v.property("bkey")
        be = next((b for b in self.backends if b.get("key") == key), None)
        if not acc or not be:
            self.status_lbl.setText("")
            return
        self.status_lbl.setText(
            f"当前：{acc.get('name','')} · {be.get('name','')}　|　"
            f"独立配置：{os.path.join(config.PROFILES_DIR, acc['id'])}　|　"
            f"已开标签页 {self.tabs.count()}（可手动关闭）"
        )


def _ensure_check_icon() -> str:
    """生成复选框勾选图标（白色对勾 PNG），返回 QSS 可用的 url。

    Qt 样式表一旦给 QCheckBox::indicator 指定了背景色，默认样式就不再绘制对勾，
    必须显式给一张图片。这里按需绘制生成，避免引入 qrc 资源编译步骤。
    """
    p = os.path.join(config.DATA_DIR, "ui_check.png")
    try:
        if not os.path.exists(p):
            size = 32  # 2x 以便高清屏不糊
            img = QImage(size, size, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            pt = QPainter(img)
            pt.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#FFFFFF"))
            pen.setWidthF(size * 0.13)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pt.setPen(pen)
            pt.setBrush(Qt.BrushStyle.NoBrush)
            # 对勾：短撇 + 长捺
            pt.drawLine(int(size * 0.24), int(size * 0.50),
                        int(size * 0.42), int(size * 0.68))
            pt.drawLine(int(size * 0.42), int(size * 0.68),
                        int(size * 0.76), int(size * 0.30))
            pt.end()
            img.save(p, "PNG")
        return p.replace("\\", "/")
    except Exception:
        return ""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    url = _ensure_check_icon()
    qss = theme.QSS
    if url:
        qss = qss.replace("{CHECK_ICON}", url)
    else:
        # 生成失败则退回无图模式（纯蓝底，仍能区分勾选态）
        qss = qss.replace("    image: url({CHECK_ICON});\n", "")
    app.setStyleSheet(qss)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
