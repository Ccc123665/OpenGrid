# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 单文件便携版配置（与 onedir 版同源码，仅输出形态不同）。"""
import os

ROOT = os.getcwd()
SRC = os.path.join(ROOT, "src")
ASSETS = os.path.join(SRC, "assets")


def _qt6_dir():
    try:
        import PyQt6
        return os.path.join(os.path.dirname(PyQt6.__file__), "Qt6")
    except Exception:
        return None


QT6 = _qt6_dir()
if not QT6 or not os.path.isdir(QT6):
    raise SystemExit("[spec] 未定位到 PyQt6/Qt6 目录")

qte_binaries = []
qte_datas = []

_proc = os.path.join(QT6, "bin", "QtWebEngineProcess.exe")
if os.path.exists(_proc):
    qte_binaries.append((_proc, os.path.join("PyQt6", "Qt6", "bin")))
else:
    raise SystemExit(f"[spec] 未找到 QtWebEngineProcess.exe：{_proc}")


def _collect(src_dir, dest_dir, keep=None):
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


qte_datas += _collect(
    os.path.join(QT6, "resources"),
    os.path.join("PyQt6", "Qt6", "resources"),
    keep=lambda fn: not fn.endswith(".debug.pak") and not fn.endswith(".debug.bin"),
)
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
    a.binaries,
    a.datas,
    [],
    name="XHSManager_onefile",
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
