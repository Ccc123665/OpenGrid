"""全局配置与路径常量。兼容开发态与 PyInstaller 单文件冻结态。"""
import sys
import os

APP_NAME = "小红书多账号全域管理工具"
APP_VERSION = "6.6.0"
MAX_ACCOUNTS = 20  # 文档强制上限：仅适配 5-20 账号

# ---- 资源路径（只读配置资源） ----
# 开发态：本文件位于 .../src；
# 单文件冻结态：sys._MEIPASS 指向临时解压根目录；
# 目录版（onedir）冻结态：PyInstaller 6.x 将资源放在可执行文件旁的 _internal/ 子目录，
#   且通常仍会设置 sys._MEIPASS 指向它。这里依次尝试多个候选，取“确实含 assets/”的那个，
#   以兼容单文件、onedir(_internal)、以及个别未设置 _MEIPASS 的 onedir 形态。
_BASE = os.path.dirname(os.path.abspath(__file__))      # .../src
if getattr(sys, "frozen", False):
    _exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    _cands = [
        getattr(sys, "_MEIPASS", None),
        os.path.join(_exe_dir, "_internal"),
        _exe_dir,
    ]
    RESOURCE_BASE = next(
        (c for c in _cands if c and os.path.isdir(os.path.join(c, "assets"))),
        _cands[0],
    )
else:
    RESOURCE_BASE = _BASE

ASSETS_DIR = os.path.join(RESOURCE_BASE, "assets")
BACKENDS_FILE = os.path.join(ASSETS_DIR, "backends.json")

# ---- 数据路径（用户数据，按平台放到各系统约定位置） ----
def user_data_base() -> str:
    """跨平台用户数据根目录：

    - Windows → %APPDATA%
    - macOS   → ~/Library/Application Support
    - Linux   → $XDG_DATA_HOME 或 ~/.local/share
    """
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support")
    if os.name == "nt":
        return os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


def _data_dir() -> str:
    d = os.path.join(user_data_base(), "XHSManager")
    os.makedirs(d, exist_ok=True)
    return d


DATA_DIR = _data_dir()
DATA_FILE = os.path.join(DATA_DIR, "accounts.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")   # 每账号一个 QtWebEngine Profile 目录


def profile_path(aid: str) -> str:
    """某账号的独立浏览器配置目录（Cookie / localStorage / 登录态）。

    不同账号目录互不相通 → 同设备多账号不串号（防关联）。
    同一账号的六大后台共享此目录 → 一次登录，全平台互通。
    """
    p = os.path.join(PROFILES_DIR, aid)
    os.makedirs(p, exist_ok=True)
    return p
