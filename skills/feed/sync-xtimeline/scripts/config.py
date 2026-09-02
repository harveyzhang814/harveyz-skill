#!/usr/bin/env python3
"""sync-xtimeline 的数据目录：通过 store_config 向统一存储根要 tweets 渠道
目录（<ROOT>/feeds/tweets）。刻意在调用时才向 store_config 取值（而不是
import 时绑定函数对象），这样测试能在进程内重定向。
"""
from pathlib import Path

import store_config


def get_data_dir() -> Path:
    return store_config.feeds_dir("tweets")
