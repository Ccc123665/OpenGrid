# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller macOS .app 打包配置（与 Windows 版同源码，仅输出形态不同）。

由「打包Mac版.command」调用，工作目录必须为本文件所在目录（spec 用 cwd 定位源码）。
"""
import os

ROOT = os.getcwd()
SRC = os.path.join(ROOT, "src")
ASSETS = os.path.join(SRC, "assets")
APP_NAME = "小红书多账号管理"


def _qt6_dir():
    try:
        import PyQt6
        return os.path.join(os.path.dirname(PyQt6.__file__), "Qt6")
    except Exception:
        return None


QT6 = _qt6_dir()
if not QT6 or not os.path.isdir(QT6):
    raise SystemExit("[spec] 未定位到 PyQt6/Qt6 目录，请先双击「启动.command」安装依赖")


def _collect(src_dir, dest_dir, keep=None):
    """递归收集目录内文件，保持相对结构。"""
    out = []
    if not os.path.isdir(src_dir):
        return out
    for cur, _dirs, files in os.walk(src_dir):
        for fn in files:
            if keep is not None and not keep(fn):
                continue
            src = os.path.join(cur, fn)
            rel = os.path.relpath(src, src_dir)
            out.append((src, os.path.join(dest_dir, rel)))
    return out


extra_datas = []

# ---- macOS 专用：QtWebEngineCore.framework 的资源与多语言包 ----
# PyQt6-WebEngine 在 macOS 上以 framework 形式分发，PyInstaller 自带 hook 通常已处理，
# 这里做一次补充收集（后面有按目标路径去重，重复条目不会进包）。
_FW = os.path.join(QT6, "lib", "QtWebEngineCore.framework")
_FW_A = os.path.join(_FW, "Versions", "A")
for _base in (_FW_A, _FW):
    if os.path.isdir(_base):
        extra_datas += _collect(
            os.path.join(_base, "Resources"),
            os.path.join("PyQt6", "Qt6", "lib", "QtWebEngineCore.framework",
                         "Versions", "A", "Resources"),
            keep=lambda fn: not fn.endswith(".debug.pak") and not fn.endswith(".debug.bin"),
        )
        break

extra_datas += _collect(
    os.path.join(QT6, "translations", "qtwebengine_locales"),
    os.path.join("PyQt6", "Qt6", "translations", "qtwebengine_locales"),
)

a = Analysis(
    [os.path.join(SRC, "main.py")],
    pathex=[SRC],
    binaries=[],
    datas=[(ASSETS, "assets")] + extra_datas,
    hiddenimports=[
        "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "PyQt6.QtNetwork",
        "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineCore",
        "config", "store", "settings", "theme", "icons",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)


# ---- 瘦身：剔除调试资源、末两段同名的重复错误条目、按目标路径去重 ----
def _is_garbage(dest: str) -> bool:
    low = dest.lower()
    if low.endswith((".debug.pak", ".debug.bin")):
        return True
    parts = low.replace("\\", "/").split("/")
    return len(parts) >= 2 and parts[-1] == parts[-2]


for _toc_name in ("datas", "binaries"):
    _seen = set()
    _clean = []
    for _d in getattr(a, _toc_name):
        _dest = _d[0]
        if _is_garbage(_dest) or _dest in _seen:
            continue
        _seen.add(_dest)
        _clean.append(_d)
    setattr(a, _toc_name, _clean)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=APP_NAME + ".app",
    icon=None,
    bundle_identifier="com.xhs.manager",
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": "6.6.0",
        "CFBundleVersion": "6.6.0",
        "LSMinimumSystemVersion": "10.15",
        "NSAppleEventsUsageDescription": "用于在应用内浏览器中处理链接跳转",
        "NSCameraUsageDescription": "站内上传图片时可能需要调用摄像头",
        "NSMicrophoneUsageDescription": "站内录制视频时可能需要调用麦克风",
    },
)
