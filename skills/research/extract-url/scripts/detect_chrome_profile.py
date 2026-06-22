#!/usr/bin/env python3
"""
检测哪个 Chrome profile 登录了 X.com (Twitter)。
用法: python3 detect_chrome_profile.py

⚠️  仅供用户手动诊断。Agent 不得主动调用此脚本——
    CHROME_PROFILE 必须来自 vars.json 配置，不得自动探测。
"""
import os
import shutil
import sqlite3
import tempfile
import json
from pathlib import Path

CHROME_BASE = Path.home() / "Library/Application Support/Google/Chrome"
XCOM_HOSTS = [".twitter.com", ".x.com"]
AUTH_COOKIES = {"auth_token", "ct0", "twid"}


def get_profile_email(profile_dir: Path) -> str:
    prefs = profile_dir / "Preferences"
    try:
        data = json.loads(prefs.read_text(errors="ignore"))
        accounts = data.get("account_info", [])
        if accounts:
            return accounts[0].get("email", "")
        return data.get("user_name", "")
    except Exception:
        return ""


def check_xcom_cookies(profile_dir: Path) -> dict:
    """返回在 X.com 找到的 auth cookie 名称集合（不解密，只检查存在性）"""
    cookies_db = profile_dir / "Cookies"
    if not cookies_db.exists():
        return {}

    # 复制到 /tmp 避免 Chrome 锁文件冲突
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name
    try:
        shutil.copy2(cookies_db, tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT name, host_key FROM cookies WHERE host_key IN ({})".format(
                ",".join("?" * len(XCOM_HOSTS))
            ),
            XCOM_HOSTS,
        )
        rows = cur.fetchall()
        conn.close()
        found = {row["name"] for row in rows}
        return found
    except Exception as e:
        return {"_error": str(e)}
    finally:
        os.unlink(tmp_path)


def main():
    if not CHROME_BASE.exists():
        print("未找到 Chrome 目录:", CHROME_BASE)
        return

    profiles = sorted(
        [d for d in CHROME_BASE.iterdir() if d.is_dir() and (d.name == "Default" or d.name.startswith("Profile"))],
        key=lambda d: (d.name != "Default", d.name),
    )

    print(f"{'Profile':<12} {'账号':<38} {'X.com cookies':<30} {'推荐'}")
    print("-" * 95)

    best = None
    for p in profiles:
        email = get_profile_email(p) or "(未登录 Google)"
        cookies = check_xcom_cookies(p)

        if "_error" in cookies:
            status = f"[错误: {cookies['_error'][:40]}]"
            has_auth = False
        else:
            auth_found = AUTH_COOKIES & cookies
            has_auth = bool(auth_found)
            all_found = cookies
            if all_found:
                status = ", ".join(sorted(all_found))
            else:
                status = "(无 X.com cookie)"

        recommend = "<-- 推荐" if has_auth and best is None else ""
        if has_auth and best is None:
            best = p

        print(f"{p.name:<12} {email:<38} {status:<30} {recommend}")

    print()
    if best:
        print(f"建议 CHROME_PROFILE 设置为：")
        print(f"  {best}")
    else:
        print("未在任何 profile 中找到 X.com auth_token，请先在 Chrome 中登录 X.com。")


if __name__ == "__main__":
    main()
