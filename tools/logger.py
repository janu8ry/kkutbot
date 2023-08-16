import datetime
import gzip
import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from config import config

__all__ = ["setup_logger"]


def rotator(source: str, dest: str) -> None:
    with open(source, "rb") as rf, gzip.open(f"logs/{dest[5:]}.gz", "wb") as wf:
        wf.write(rf.read())
    os.remove(source)


def namer(_: Any) -> str:
    return os.path.join("logs", time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)) + ".log")


def setup_command_logger() -> None:
    if "logs" not in os.listdir():
        os.mkdir("logs")
    logger = logging.getLogger("kkutbot")
    logger.setLevel(logging.DEBUG)

    console = Console(
        theme=Theme(
            {
                "logging.level.command": "green",
                "logging.level.invite": "gold1",
                "logging.level.leave": "magenta",
            }
        )
    )
    stream_handler = RichHandler(rich_tracebacks=not config.is_test, console=console)

    stream_handler.setFormatter(logging.Formatter(fmt="%(name)s :\t%(message)s"))
    stream_handler.setLevel(logging.DEBUG + 3)

    file_handler = TimedRotatingFileHandler(filename=os.path.join("logs", "latest.log"), when="midnight", encoding="utf-8", atTime=datetime.time(23, 59, 59))  # type: ignore
    file_handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(lineno)d]: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    file_handler.setLevel(logging.DEBUG)

    file_handler.rotator = rotator
    file_handler.namer = namer

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    logging.addLevelName(logging.DEBUG + 5, "COMMAND")

    def command(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.DEBUG + 5, msg, *args, **kwargs)

    logging.Logger.command = command  # type: ignore

    logging.addLevelName(logging.DEBUG + 3, "INVITE")

    def invite(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.DEBUG + 3, msg, *args, **kwargs)

    logging.Logger.invite = invite  # type: ignore

    logging.addLevelName(logging.DEBUG + 4, "LEAVE")

    def leave(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.DEBUG + 4, msg, *args, **kwargs)

    logging.Logger.leave = leave  # type: ignore

    logger.info("명령어 로깅 설정 완료!")


def setup_error_logger() -> None:
    logger = logging.getLogger("kkutbot")

    sentry_sdk.init(
        dsn=config.sentry.dsn,
        traces_sample_rate=1.0,
        release=str(config.version),
        environment="test" if config.is_test else "production",
        integrations=[
            AsyncioIntegration(),
            LoggingIntegration(event_level=None)
        ],
    )

    logger.info("에러 로깅 설정 완료!")


def setup_logger() -> None:
    setup_command_logger()
    setup_error_logger()
