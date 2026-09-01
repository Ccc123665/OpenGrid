"""本地 JSON 数据存储层：账号台账。

v2：已移除操作日志 / 数据看板 / 定时登记台账三个模块，仅保留账号管理所需数据。

纯本地文件读写，无任何网络/自动化行为。账号上限强制 MAX_ACCOUNTS。
"""
import json
import os
import shutil
import uuid
import datetime
from typing import Any, Dict, List, Optional

import config

# v1 遗留键（模块已移除，导入时自动丢弃）
_LEGACY_KEYS = ("logs", "scheduler", "data_board")


# ---------- 数据模型 ----------
def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_account(name: str) -> Dict[str, Any]:
    aid = uuid.uuid4().hex[:12]
    return {
        "id": aid,
        "name": name.strip(),
        "group": "",          # 分组
        "track": "",          # 赛道
        "owner": "",          # 负责人
        "status": "正常",      # 正常 | 限流 | 封禁预警 | 资质到期 | 停用
        "realname": "",       # 实名信息（同实名/同主体关联标记）
        "note": "",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _empty_db() -> Dict[str, Any]:
    return {"version": 2, "accounts": []}


# ---------- 读写 ----------
def load_db() -> Dict[str, Any]:
    if os.path.exists(config.DATA_FILE):
        try:
            with open(config.DATA_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            backup_corrupt()
            return _empty_db()
        db.setdefault("accounts", [])
        for k in _LEGACY_KEYS:      # 兼容 v1 数据，丢弃已移除模块
            db.pop(k, None)
        return db
    return _empty_db()


def save_db(db: Dict[str, Any]) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    tmp = config.DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, config.DATA_FILE)


def backup_corrupt() -> None:
    if os.path.exists(config.DATA_FILE):
        dst = config.DATA_FILE + ".corrupt." + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy(config.DATA_FILE, dst)


# ---------- 账号操作 ----------
def list_accounts(db: Dict[str, Any]) -> List[Dict[str, Any]]:
    return db["accounts"]


def get_account(db: Dict[str, Any], aid: str) -> Optional[Dict[str, Any]]:
    for a in db["accounts"]:
        if a["id"] == aid:
            return a
    return None


def add_account(db: Dict[str, Any], name: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("账号名称不能为空")
    if len(db["accounts"]) >= config.MAX_ACCOUNTS:
        raise ValueError(f"账号数量已达上限 {config.MAX_ACCOUNTS}，无法继续添加")
    acc = _new_account(name)
    db["accounts"].append(acc)
    db["version"] = 2
    save_db(db)
    return acc


def update_account(db: Dict[str, Any], aid: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    acc = get_account(db, aid)
    if not acc:
        raise ValueError("账号不存在")
    allowed = {"name", "group", "track", "owner", "status", "realname", "note"}
    for k, v in fields.items():
        if k in allowed:
            acc[k] = v
    acc["updated_at"] = _now()
    save_db(db)
    return acc


def delete_account(db: Dict[str, Any], aid: str) -> None:
    db["accounts"] = [a for a in db["accounts"] if a["id"] != aid]
    save_db(db)


def account_count(db: Dict[str, Any]) -> int:
    return len(db["accounts"])


def clear_account_profile(aid: str) -> bool:
    """清除某账号的浏览器数据（Cookie / 登录态 / 缓存）。"""
    d = os.path.join(config.PROFILES_DIR, aid)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


# ---------- 备份 / 导入 / 导出（JSON） ----------
def export_json(dst_path: str) -> str:
    """导出整库 JSON 到指定路径（用于团队共享/迁移）。"""
    db = load_db()
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    return dst_path


def import_json(src_path: str) -> Dict[str, Any]:
    """从 JSON 导入整库（覆盖本地）。导入前自动备份当前数据。"""
    with open(src_path, "r", encoding="utf-8") as f:
        db = json.load(f)
    db.setdefault("accounts", [])
    for k in _LEGACY_KEYS:
        db.pop(k, None)
    if len(db["accounts"]) > config.MAX_ACCOUNTS:
        raise ValueError(
            f"导入数据含 {len(db['accounts'])} 个账号，超过上限 {config.MAX_ACCOUNTS}"
        )
    if os.path.exists(config.DATA_FILE):
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy(config.DATA_FILE, config.DATA_FILE + f".bak.{ts}")
    save_db(db)
    return db


def backup_now() -> str:
    """手动备份当前数据到 DATA_DIR/backup_时间戳.json。"""
    if not os.path.exists(config.DATA_FILE):
        save_db(load_db())
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(config.DATA_DIR, f"backup_{ts}.json")
    shutil.copy(config.DATA_FILE, dst)
    return dst
