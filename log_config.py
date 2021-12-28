from typing import Any

from loguru import logger
import time


class log:
    # 日志配置
    log_file_name = time.strftime("%Y_%m_%d")
    logger.add(f"log/ding_auto_{log_file_name}.log", rotation="500MB", encoding="utf-8", enqueue=True,
               retention="1 week")

    def info(self: str, *args: Any, **kwargs: Any):
        logger.info(self, args, kwargs)

    def error(self: str, *args: Any, **kwargs: Any):
        logger.error(self, args, kwargs)
