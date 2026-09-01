"""把 Mac 版目录打包成 zip，并正确设置文件权限位（.command 必须可执行）。
macOS 的「归档实用工具」解压时会还原 UNIX 权限位，因此这里必须写入 external_attr。

位置：build/make_mac_zip.py → 项目根 = 上级目录
"""
import os
import shutil
import zipfile

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD)                       # 项目根
DIST = os.path.join(ROOT, "dist")
SRC = os.path.join(DIST, "小红书多账号管理-Mac版")
OUT = os.path.join(DIST, "小红书多账号管理_Mac版.zip")

if not os.path.isdir(SRC):
    raise SystemExit(f"[错误] 找不到 Mac 版源目录：{SRC}")

EXEC_NAMES = {"启动.command", "打包Mac版.command", "环境自检.command"}
SKIP = {"__pycache__", ".venv", "dist", "build"}

# 单一来源：spec 与 entitlements 的正本放在 build/，每次打包自动同步进 Mac 包，
# 保证 Mac 包里的副本与 GitHub Actions 用的正本永远一致。
for _fn in ("xhs_manager_mac.spec", "entitlements.plist"):
    _src = os.path.join(BUILD, _fn)
    if os.path.exists(_src):
        shutil.copy2(_src, os.path.join(SRC, _fn))
        print(f"  同步正本 {_fn}")

if os.path.exists(OUT):
    os.remove(OUT)

count = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for cur, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in SKIP]
        # zip 内以 dist/ 为根，解压后顶层直接是「小红书多账号管理-Mac版/」
        rel_dir = os.path.relpath(cur, DIST)
        if rel_dir != ".":
            zi = zipfile.ZipInfo(rel_dir.replace(os.sep, "/") + "/")
            zi.external_attr = (0o40755 << 16) | 0x10
            z.writestr(zi, "")
        for fn in sorted(files):
            if fn.endswith((".pyc", ".pyo")) or fn.startswith("_"):
                continue
            full = os.path.join(cur, fn)
            arc = os.path.relpath(full, DIST).replace(os.sep, "/")
            zi = zipfile.ZipInfo(arc)
            zi.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if fn in EXEC_NAMES else 0o644
            zi.external_attr = (mode << 16)
            with open(full, "rb") as f:
                z.writestr(zi, f.read())
            count += 1
            print(f"  {mode:o}  {arc}")

print(f"\n打包完成：{count} 个文件")
print("输出：", OUT)
print("大小：%.1f KB" % (os.path.getsize(OUT) / 1024))
