# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 单文件打包配置（v2：PyQt6 + 内嵌 QtWebEngine）。

构建时必须 cd 到项目根目录执行（spec 用 cwd 定位）：
    python -m PyInstaller --clean --noconfirm build/xhs_manager.spec

QtWebEngine 的关键坑：Chromium 运行时不会被自动收集，必须显式携带
    - PyQt6/Qt6/bin/QtWebEngineProcess.exe（渲染进程，缺失则内嵌浏览器无法启动）
    - PyQt6/Qt6/resources（qtwebengine_resources*.pak 等）
    - PyQt6/Qt6/translations（qtwebengine_locales 等）
否则打包出的 EXE 会白屏或报 "QtWebEngineProcess 未找到"。
"""
import os

ROOT = os.getcwd()                                    # 项目根
SRC = os.path.join(ROOT, "src")
ASSETS = os.path.join(SRC, "assets")


def _qt6_dir():
    """动态定位 PyQt6 的 Qt6 运行时目录，避免硬编码版本路径。"""
    try:
        import PyQt6
        return os.path.join(os.path.dirname(PyQt6.__file__), "Qt6")
    except Exception:
        return None


QT6 = _qt6_dir()
if not QT6 or not os.path.isdir(QT6):
    raise SystemExit(
        "[spec] 未定位到 PyQt6/Qt6 目录。请确认已安装 PyQt6 与 PyQt6-WebEngine"
    )

qte_binaries = []
qte_datas = []

# Chrome/Chromium 渲染进程 —— 必须随包分发
_proc = os.path.join(QT6, "bin", "QtWebEngineProcess.exe")
if os.path.exists(_proc):
    qte_binaries.append((_proc, os.path.join("PyQt6", "Qt6", "bin")))
else:
    raise SystemExit(f"[spec] 未找到 QtWebEngineProcess.exe：{_proc}")

def _collect(src_dir, dest_dir, keep=None):
    """把 src_dir 下的文件逐条列出（可按文件名过滤），保留相对目录结构。"""
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


# Chromium 资源：剔除 *.debug.pak / *.debug.bin（仅调试用，合计约 75MB，运行不需要）
qte_datas += _collect(
    os.path.join(QT6, "resources"),
    os.path.join("PyQt6", "Qt6", "resources"),
    keep=lambda fn: not fn.endswith(".debug.pak") and not fn.endswith(".debug.bin"),
)

# Chromium 语言包：只取 qtwebengine_locales，跳过 Qt 自身的 .qm 翻译（本工具无需多语言 UI）
qte_datas += _collect(
    os.path.join(QT6, "translations", "qtwebengine_locales"),
    os.path.join("PyQt6", "Qt6", "translations", "qtwebengine_locales"),
)

a = Analysis(
    [os.path.join(SRC, "main.py")],
    pathex=[SRC],
    binaries=qte_binaries,
    datas=[(ASSETS, "assets")] + qte_datas,
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

# ---- 剔除冗余条目，显著减小体积 ----
# 现象：PyInstaller 自带的 PyQt6/QtWebEngine 钩子会再收集一遍同样的资源，
# 且部分条目目标路径出现文件名重复（如 resources\x.pak\x.pak），造成包体虚胖。
# 这里统一清理：删调试资源、删路径重复的错误条目、按目标路径去重。
def _is_garbage(dest: str) -> bool:
    low = dest.lower()
    if low.endswith((".debug.pak", ".debug.bin")):      # 仅调试用，运行不需要
        return True
    parts = low.replace("\\", "/").split("/")
    return len(parts) >= 2 and parts[-1] == parts[-2]   # 目标路径末段重复的错误条目


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
    name="XHSManager",
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
    name="XHSManager",
)
