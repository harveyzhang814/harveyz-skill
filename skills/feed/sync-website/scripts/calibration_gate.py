#!/usr/bin/env python3
"""标定第 5 步的机械门槛
（docs/superpowers/specs/2026-09-02-sync-website-design.md §4.1）：纯函数，
不碰磁盘不碰网络。只挡假阴性（条目太少、字段形状不对）——挡不住假阳性（抽出
一堆导航链接，但形状合法：条数够、title 合格、url 合格），那一半交给调用方
紧接着的模型过目步骤。四条阈值是设计阶段拍的，没有拿真实站点样本验证过
（spec §9"推出来的"）。
"""
import json
import sys
from urllib.parse import urlparse

MIN_ITEMS = 3
MIN_TITLE_LEN = 5
MAX_TITLE_LEN = 200


def check_gate(articles: list[dict]) -> tuple[bool, str]:
    """Returns (passed, reason). reason is "" on pass, otherwise names
    which check failed and (where applicable) which article — calibrate
    needs this to tell the model what to fix, not just that it failed."""
    if len(articles) < MIN_ITEMS:
        return False, f"条目数 {len(articles)} < {MIN_ITEMS}"

    for i, a in enumerate(articles):
        title = a.get("title", "")
        if not (MIN_TITLE_LEN <= len(title) <= MAX_TITLE_LEN):
            return False, f"第 {i} 条 title 长度 {len(title)} 不在 [{MIN_TITLE_LEN}, {MAX_TITLE_LEN}] 内：{title!r}"

    for i, a in enumerate(articles):
        url = a.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, f"第 {i} 条 url 不是绝对链接：{url!r}"

    urls = [a["url"] for a in articles]
    if len(set(urls)) != len(urls):
        return False, "url 去重后数量与条目数不一致，存在重复"

    return True, ""


def main():
    articles = json.load(sys.stdin)
    passed, reason = check_gate(articles)
    print(json.dumps({"passed": passed, "reason": reason}, ensure_ascii=False))


if __name__ == "__main__":
    main()
