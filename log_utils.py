# -*- coding: utf-8 -*-
"""训练/测试日志备份。

把 stdout 同时写入一个带时间戳的日志文件（UTF-8），实现「日志备份」。
用法：在脚本最前面调用一次

    from log_utils import setup_log
    setup_log("train_intent")   # 生成 logs/train_intent_YYYYMMDD_HHMMSS.log
"""
import os
import sys
from datetime import datetime


class _Tee(object):
    """同时写文件与控制台的标准输出。"""

    def __init__(self, path):
        self.file = open(path, "w", encoding="utf-8")
        self.console = sys.stdout
        self.encoding = "utf-8"

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode(self.encoding, errors="replace")
        self.file.write(data)
        self.file.flush()
        try:
            self.console.write(data)
            self.console.flush()
        except Exception:
            pass

    def flush(self):
        self.file.flush()

    def isatty(self):
        return False


def setup_log(name, log_dir="logs"):
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(log_dir, "%s_%s.log" % (name, ts))
    sys.stdout = _Tee(path)
    return path
