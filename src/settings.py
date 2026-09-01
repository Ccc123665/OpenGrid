"""用户设置：最近选中的账号/平台等轻量偏好（浏览器已内嵌，无需配置浏览器路径）。"""
import json
import os
import sys
import subprocess
from typing import Dict, Any

import config

_DEFAULTS: Dict[str, Any] = {
    "last_account_id": "",
    "last_backend_key": "",
    # 硬件加速：默认关闭（软件渲染），为兼容无 GPU 的老机器 / 远程桌面。
    # 有独显的新机器可开启以改善网页滚动流畅度，需重启生效。
    "hardware_accel": False,
    # 是否已做过首次显卡探测（避免每次启动都重跑探测）
    "_gpu_probed": False,
}


def is_macos() -> bool:
    return sys.platform == "darwin"


def _is_remote_session() -> bool:
    """是否处于远程 / 无本地 GPU 的会话。

    - Windows：RDP 下 Chromium 的 GPU 虚拟化会失败（Failed to create shared
      context），此时即使有独显也应走软件渲染。判定依据为环境变量 SESSIONNAME
      形如 RDP-Tcp#0。
    - macOS / Linux：通过 SSH 转发 GUI（X11 / 无显示器）时同理。
    """
    name = (os.environ.get("SESSIONNAME") or "").upper()
    if name.startswith("RDP"):
        return True
    # SSH 会话下没有本地显示器，GUI 由转发提供，GPU 不可用
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True
    return False


def _detect_gpu_macos() -> bool:
    """macOS 显卡探测。

    macOS 的 GPU 驱动由系统统一提供（Apple Silicon 统一内存 GPU / AMD Radeon /
    Intel Iris 均为系统级支持），不像 Windows 那样存在驱动不兼容导致白屏的问题，
    因此只要识别到常规 GPU 就推荐开启硬件加速；纯软件渲染（llvmpipe、虚拟机
    虚拟显卡）才返回 False。
    """
    try:
        out = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=20,
        ).stdout.lower()
    except Exception:
        return False
    if not out.strip():
        return False
    # 纯软件渲染 / 虚拟显卡：不开硬件加速
    weak = ("llvmpipe", "software", "virtual", "vmware", "parallels", "basic display")
    if any(w in out for w in weak):
        return False
    # Apple Silicon（Apple M1/M2/M3…）、AMD、NVIDIA、Intel Iris 均支持
    good = ("apple m", "apple gpu", "amd", "radeon", "nvidia", "geforce",
            "iris", "arc ", "intel uhd", "intel hd")
    return any(g in out for g in good)


def _detect_gpu_windows() -> bool:
    """Windows 显卡探测（保守，宁可不开启）。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=8,
        ).stdout.lower()
    except Exception:
        return False
    if not out.strip():
        return False
    # 软件/基础/核显适配器：一律视为「不推荐开启硬件加速」
    # （Intel 核显 HD/UHD/Iris、Microsoft Basic、llvmpipe、Virtual 等）
    weak = ("microsoft basic", "llvmpipe", "software", "virtual",
            "intel", "hd graphics", "uhd graphics", "iris", "vga")
    if any(w in out for w in weak):
        return False
    # 其余非弱适配器中，认出独显厂商关键词才算独显
    good = ("nvidia", "geforce", "quadro", "rtx", "amd", "radeon", "rx ", "arc ")
    return any(g in out for g in good)


def _detect_discrete_gpu() -> bool:
    """探测「是否应推荐开启硬件加速」。

    通用规则（保守，宁可不开启）：
    1. 远程会话（Windows RDP / SSH 转发）→ 直接 False；
    2. Windows：仅当检测到 NVIDIA / AMD 独显时 True，核显一律 False；
    3. macOS：驱动由系统统一提供，识别到常规 GPU 即 True（纯软件渲染除外）。
    探测失败（命令异常）一律返回 False。
    """
    if _is_remote_session():
        return False
    if is_macos():
        return _detect_gpu_macos()
    if os.name == "nt":
        return _detect_gpu_windows()
    return False


def get_settings() -> Dict[str, Any]:
    s: Dict[str, Any]
    if os.path.exists(config.SETTINGS_FILE):
        try:
            with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
        except Exception:
            s = dict(_DEFAULTS)
    else:
        s = dict(_DEFAULTS)

    for k, v in _DEFAULTS.items():
        s.setdefault(k, v)

    # 首次启动：自动探测显卡并设置推荐默认值（之后用户手动改动均优先）
    if not s.get("_gpu_probed", False):
        s["hardware_accel"] = _detect_discrete_gpu()
        s["_gpu_probed"] = True
        save_settings(s)
    return s


def save_settings(s: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return s


def gpu_recommendation_text() -> str:
    """给设置对话框用的「当前显卡探测结论」一句话。"""
    if is_macos():
        if _detect_discrete_gpu():
            return "已检测到本机 GPU（macOS 系统级驱动，兼容良好），建议开启硬件加速以获得更流畅的网页体验。"
        return "未检测到可用 GPU（或为虚拟机 / 远程会话），默认走软件渲染以保证稳定打开。"
    if _detect_discrete_gpu():
        return "已检测到独立显卡（NVIDIA / AMD），建议开启硬件加速以获得更流畅的网页体验。"
    return "未检测到独立显卡（或为核显 / 远程桌面），默认走软件渲染以保证稳定打开。"
