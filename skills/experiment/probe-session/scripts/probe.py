#!/usr/bin/env python3
"""
Probe Chrome session cookie injection via Playwright.

Load strategy selection:
  - Known/learned domains → SKILL_DIR/strategies.json
  - Unknown domains       → probe PROBE_ORDER in sequence, record winner

All strategies (seeded + learned) live in one file next to the skill.

Usage: python probe.py <url> <chrome_profile>
"""
import sys, os, shutil, tempfile, json
from pathlib import Path
from urllib.parse import urlparse

url            = sys.argv[1]
chrome_profile = sys.argv[2]

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


# ── Constants ─────────────────────────────────────────────────────────

UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/136.0.0.0 Safari/537.36'
)
LAUNCH_ARGS = ['--disable-blink-features=AutomationControlled']

# strategies.json 与 skill 同目录（scripts/ 的上一级）
STRATEGIES_PATH = Path(__file__).parent.parent / 'data' / 'strategies.json'

# 按顺序尝试的策略列表（未知站点时使用）
PROBE_ORDER = [
    # 适用大多数 SPA（X.com、React/Vue 应用）
    {
        "id": "dce+ni",
        "wait_until": "domcontentloaded",
        "post_wait": "networkidle",
        "post_wait_ms": 8000,
        "fallback_ms": 2000,
        "desc": "domcontentloaded + networkidle(8s)",
    },
    # 适用资源加载能在 30s 内完成的传统站点
    {
        "id": "load+ni",
        "wait_until": "load",
        "post_wait": "networkidle",
        "post_wait_ms": 8000,
        "fallback_ms": 2000,
        "desc": "load + networkidle(8s)",
    },
    # 兜底：固定等待，适用 networkidle 无法稳定触发的站点
    {
        "id": "dce+5s",
        "wait_until": "domcontentloaded",
        "post_wait": "fixed",
        "fixed_ms": 5000,
        "desc": "domcontentloaded + fixed 5s",
    },
]

# ── Strategy helpers ──────────────────────────────────────────────────

def get_root_domain(url: str) -> str:
    parts = urlparse(url).hostname.split('.')
    return '.'.join(parts[-2:])


def load_strategies() -> dict:
    if STRATEGIES_PATH.exists():
        try:
            return json.loads(STRATEGIES_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_strategy(domain: str, strategy: dict):
    strategies = load_strategies()
    strategies[domain] = strategy
    STRATEGIES_PATH.write_text(json.dumps(strategies, ensure_ascii=False, indent=2))


def resolve_strategy(domain: str, url: str):
    """
    Return (strategy, source, cached_anon_result).
    cached_anon_result is (status, title, body) when the probe itself
    produced the anonymous result (avoids a redundant second request).
    """
    strategies = load_strategies()
    if domain in strategies:
        return strategies[domain], 'strategies.json', None

    # Unknown domain — probe each strategy
    print(f"  未知站点 [{domain}]，按顺序探测加载策略...", flush=True)
    for i, s in enumerate(PROBE_ORDER):
        print(f"  [{i+1}/{len(PROBE_ORDER)}] {s['desc']} ...", flush=True)
        status, title, body, ok = _fetch(url, s)
        if ok and title and '超时' not in title:
            print(f"  ✓ 找到有效策略 [{s['id']}]，已记录到 {STRATEGIES_PATH}", flush=True)
            save_strategy(domain, s)
            return s, 'probed', (status, title, body)

    print(f"  ⚠ 所有策略均未获得有效 title，使用默认策略（不记录）", flush=True)
    return PROBE_ORDER[0], 'fallback', None


# ── Core fetch ────────────────────────────────────────────────────────

def _apply_post_wait(page, strategy: dict):
    if strategy.get('post_wait') == 'networkidle':
        try:
            page.wait_for_load_state('networkidle', timeout=strategy.get('post_wait_ms', 8000))
        except Exception:
            page.wait_for_timeout(strategy.get('fallback_ms', 2000))
    elif strategy.get('post_wait') == 'fixed':
        page.wait_for_timeout(strategy.get('fixed_ms', 2000))


def _fetch(url: str, strategy: dict, cookies: list = None):
    """Return (status, title, body, ok)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
        ctx = browser.new_context(user_agent=UA)
        if cookies:
            try:
                ctx.add_cookies(cookies)
            except Exception:
                ok_n = sum(1 for c in cookies if _try_add_cookie(ctx, c))
                print(f"  [注意] 批量注入失败，逐条注入：{ok_n}/{len(cookies)} 条成功", flush=True)
        page = ctx.new_page()
        try:
            resp   = page.goto(url, timeout=30000, wait_until=strategy['wait_until'])
            status = resp.status if resp else 0
            _apply_post_wait(page, strategy)
            title = page.title()
            body  = page.evaluate(
                "() => document.body"
                " ? document.body.innerText.replace(/\\s+/g,' ').trim().slice(0,400)"
                " : ''"
            )
            return status, title, body, True
        except Exception as e:
            return 0, '(超时或报错)', str(e)[:300], False
        finally:
            browser.close()


def _try_add_cookie(ctx, cookie: dict) -> bool:
    try:
        ctx.add_cookies([cookie])
        return True
    except Exception:
        return False


# ── Main ──────────────────────────────────────────────────────────────

domain = get_root_domain(url)

print(f"[ 0/3 ] 确定加载策略...", flush=True)
strategy, source, cached_anon = resolve_strategy(domain, url)
print(f"  [{strategy['id']}] {strategy.get('desc', '')}（来源：{source}）", flush=True)

# 匿名访问（若探测时已顺带跑过，直接复用结果）
if cached_anon:
    print("[ 1/3 ] 匿名访问结果来自策略探测，跳过重复请求", flush=True)
    anon_status, anon_title, anon_body = cached_anon
else:
    print("[ 1/3 ] 匿名访问中...", flush=True)
    anon_status, anon_title, anon_body, _ = _fetch(url, strategy)

# 提取 Chrome cookie
print("[ 2/3 ] 提取 Chrome cookie...", flush=True)
cookies_src = Path(chrome_profile) / 'Cookies'
if not cookies_src.exists():
    print(f"ERROR: Cookies 文件不存在：{cookies_src}", file=sys.stderr)
    sys.exit(1)

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
    tmp_path = f.name
shutil.copy2(cookies_src, tmp_path)
try:
    cookies_dict = pycookiecheat.chrome_cookies(url, cookie_file=tmp_path)
finally:
    os.unlink(tmp_path)

parts         = _parsed.hostname.split('.')
cookie_domain = '.' + '.'.join(parts[-2:])
cookie_count  = len(cookies_dict)
pw_cookies    = [
    {'name': k, 'value': v, 'domain': cookie_domain, 'path': '/', 'secure': True}
    for k, v in cookies_dict.items()
]

# 登录态访问
print("[ 3/3 ] 注入 cookie 后访问...", flush=True)
auth_status, auth_title, auth_body, _ = _fetch(url, strategy, cookies=pw_cookies)

# 对比输出
sep = '─' * 62
print()
print(sep)
print(' 对比结果')
print(sep)
print(f" Chrome Profile : {Path(chrome_profile).name}")
print(f" Cookie 数量    : {cookie_count} 个（域：{cookie_domain}）")
print(f" 加载策略       : [{strategy['id']}] {strategy.get('desc','')}（{source}）")
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
