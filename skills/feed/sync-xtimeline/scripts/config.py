#!/usr/bin/env python3
"""sync-xtimeline 的数据目录。

名册化之后这个 skill 不再持有自己的 DATA_DIR——它和 sync-ytchannel 共用
roster 名册那一个，向 roster 要。保留这个模块只是为了让 archive_tweets.py
的 import 不用改。旧的
~/.hskill/sync-xtimeline/config.json 在迁移后作废，但不自动删除。

刻意在调用时才向 roster_client 取值（而不是 import 时绑定函数对象），
这样测试能在进程内重定向。
"""
from pathlib import Path

import roster_client


def get_data_dir() -> Path:
    return roster_client.data_dir()
