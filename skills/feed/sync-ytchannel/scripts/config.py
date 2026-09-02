#!/usr/bin/env python3
"""sync-ytchannel 的数据目录：通过 store_config 向统一存储根要 youtube 渠道
目录（<ROOT>/feeds/youtube）——sync-xtimeline 的 youtube 对应实现。刻意在
调用时才向 store_config 取值（而不是 import 时绑定函数对象），这样测试能
在进程内重定向。
"""
from pathlib import Path

import store_config


def get_data_dir() -> Path:
    return store_config.feeds_dir("youtube")
