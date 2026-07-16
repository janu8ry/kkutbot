import datetime
import gzip
import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from typing import Any

import sentry_sdk
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from config import config

__all__ = ["KkutbotLogger", "setup_logger"]

COMMAND = logging.INFO + 3
INVITE = logging.INFO + 4
LEAVE = logging.INFO + 5

logging.addLevelName(COMMAND, "COMMAND")
logging.addLevelName(INVITE, "INVITE")
logging.addLevelName(LEAVE, "LEAVE")


class KkutbotLogger(logging.Logger):
    def command(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(COMMAND):
            self._log(COMMAND, msg, args, **kwargs)

    def invite(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(INVITE):
            self._log(INVITE, msg, args, **kwargs)

    def leave(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(LEAVE):
            self._log(LEAVE, msg, args, **kwargs)


logging.setLoggerClass(KkutbotLogger)


def rotator(source: str, dest: str) -> None:
    with open(source, "rb") as rf, gzip.open(f"{dest}.gz", "wb") as wf:
        wf.write(rf.read())
    os.remove(source)


def namer(_: Any) -> str:
    return os.path.join("logs", time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)) + ".log")


def setup_command_logger() -> None:
    if "logs" not in os.listdir():
        os.mkdir("logs")
    logger = logging.getLogger("kkutbot")
    logger.__class__ = KkutbotLogger
    logger.setLevel(logging.DEBUG)

    console = Console(
        theme=Theme(
            {
                "logging.level.command": "green",
                "logging.level.invite": "gold1",
                "logging.level.leave": "magenta",
            }
        ),
        width=200,
        force_terminal=True,
    )
    stream_handler = RichHandler(console=console, show_path=False)
    stream_handler.setFormatter(logging.Formatter(fmt="%(name)s :\t%(message)s"))
    stream_handler.setLevel(logging.DEBUG)

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join("logs", "latest.log"), when="midnight", encoding="utf-8", atTime=datetime.time(23, 59, 59)
    )
    file_handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(lineno)d]: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    file_handler.setLevel(logging.INFO)

    file_handler.rotator = rotator
    file_handler.namer = namer

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    logger.info("로깅 설정 완료!")


def setup_error_logger() -> None:
    logger = logging.getLogger("kkutbot")

    sentry_sdk.init(
        dsn=config.sentry.dsn if not config.is_test else "",
        traces_sample_rate=1.0,
        release=str(config.version),
        environment="test" if config.is_test else "production",
        integrations=[AsyncioIntegration(), LoggingIntegration(event_level=None)],
    )

    logger.info("Sentry 설정 완료!")


def setup_logger() -> None:
    setup_command_logger()
    setup_error_logger()
