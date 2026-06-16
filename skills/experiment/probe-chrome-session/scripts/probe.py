#!/usr/bin/env python3
"""
Probe Chrome session cookie injection via Playwright.
Runs the target URL twice: once without cookies (anonymous), once with Chrome cookies.
Outputs a side-by-side comparison to verify the injection worked.

Usage: python probe.py <url> <chrome_profile>
"""
import sys, os, shutil, tempfile
from pathlib import Path
from urllib.parse import urlparse

url            = sys.argv[1]
chrome_profile = sys.argv[2]

# --- Security: validate URL scheme before heavy imports ---
_parsed = urlparse(url)
if _parsed.scheme not in ('http', 'https') or not _parsed.netloc:
    print(f"ERROR: 无效 URL scheme '{_parsed.scheme}'，只允许 http/https", file=sys.stderr)
    sys.exit(1)

try:
    import pycookiecheat
except ImportError:
    print("ERROR: 缺少依赖，请先运行：pip install pycookiecheat", file=sys.stderr)
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: 缺少依赖，请先运行：pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/136.0.0.0 Safari/537.36'
)
LAUNCH_ARGS = ['--disable-blink-features=AutomationControlled']


def fetch_page(url, cookies=None):
    """Navigate to url, optionally inject cookies. Returns (status, title, body_preview)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
        ctx = browser.new_context(user_agent=UA)
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        try:
            resp = page.goto(url, timeout=30000, wait_until='load')
            status = resp.status if resp else 0
            # SPA 页面需要等 JS 渲染完；networkidle 超时就退回 2s 静默等待
            try:
                page.wait_for_load_state('networkidle', timeout=8000)
            except Exception:
                page.wait_for_timeout(2000)
            title  = page.title()
            body   = page.evaluate(
                "() => document.body"
                " ? document.body.innerText.replace(/\\s+/g,' ').trim().slice(0,400)"
                " : ''"
            )
        except Exception as e:
            status, title, body = 0, '(超时或报错)', str(e)[:300]
        finally:
            browser.close()
    return status, title, body


# --- 匿名访问 ---
print("[ 1/3 ] 匿名访问中...", flush=True)
anon_status, anon_title, anon_body = fetch_page(url)

# --- 提取 Chrome cookie ---
print("[ 2/3 ] 提取 Chrome cookie...", flush=True)
cookies_src = Path(chrome_profile) / 'Cookies'
if not cookies_src.exists():
    print(f"ERROR: Cookies 文件不存在：{cookies_src}", file=sys.stderr)
    print("请检查 CHROME_PROFILE 路径是否正确，Chrome 是否至少启动过一次。", file=sys.stderr)
    sys.exit(1)

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_path = f.name
shutil.copy2(cookies_src, tmp_path)
try:
    cookies_dict = pycookiecheat.chrome_cookies(url, cookie_file=tmp_path)
finally:
    os.unlink(tmp_path)

# 从 URL hostname 推断 cookie domain（取后两段，加前缀点号）
parts         = _parsed.hostname.split('.')
cookie_domain = '.' + '.'.join(parts[-2:])
cookie_count  = len(cookies_dict)

pw_cookies = [
    {'name': k, 'value': v, 'domain': cookie_domain, 'path': '/', 'secure': True}
    for k, v in cookies_dict.items()
]

# --- 登录态访问 ---
print("[ 3/3 ] 注入 cookie 后访问...", flush=True)
auth_status, auth_title, auth_body = fetch_page(url, cookies=pw_cookies)

# --- 对比输出 ---
sep = '─' * 62
print()
print(sep)
print(' 对比结果')
print(sep)
print(f" Chrome Profile : {Path(chrome_profile).name}")
print(f" Cookie 数量    : {cookie_count} 个（域：{cookie_domain}）")
print(sep)
print(f" [匿名] Status  : {anon_status}")
print(f" [匿名] Title   : {anon_title}")
print(f" [匿名] Body    : {anon_body[:200]}")
print()
print(f" [登录] Status  : {auth_status}")
print(f" [登录] Title   : {auth_title}")
print(f" [登录] Body    : {auth_body[:200]}")
print(sep)

if cookie_count == 0:
    print(" 结论：未提取到任何 cookie — 请先在 Chrome 里登录目标网站")
elif anon_title == auth_title:
    print(" 结论：Title 相同 → Cookie 可能未生效，或该页面无需登录")
    print(f"        Title: {auth_title!r}")
else:
    print(" 结论：Title 不同 → Cookie 注入有效 ✓")
    print(f"        匿名: {anon_title!r}")
    print(f"        登录: {auth_title!r}")
print(sep)
