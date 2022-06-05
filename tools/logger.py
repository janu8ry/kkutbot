import gzip
import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

from .config import config  # noqa


def rotator(source: str, dest: str):
    with open(source, "rb") as rf, gzip.open(f"logs/{dest[5:]}.gz", "wb") as wf:
        wf.write(rf.read())
    os.remove(source)


def namer(_) -> str:
    return os.path.join("logs", time.strftime("%Y-%m-%d") + ".log")


def setup_logger():
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

    stream_handler = RichHandler(rich_tracebacks=not config("test"), console=console)
    stream_handler.setFormatter(logging.Formatter(fmt="%(name)s :\t%(message)s"))
    stream_handler.setLevel(logging.DEBUG + 3)

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join("logs", "latest.log"), when="midnight", encoding="utf-8"
    )
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

    def command(self, msg, *args, **kwargs):
        self.log(logging.DEBUG + 5, msg, *args, **kwargs)

    logging.Logger.command = command

    logging.addLevelName(logging.DEBUG + 3, "INVITE")

    def invite(self, msg, *args, **kwargs):
        self.log(logging.DEBUG + 3, msg, *args, **kwargs)

    logging.Logger.invite = invite

    logging.addLevelName(logging.DEBUG + 4, "LEAVE")

    def leave(self, msg, *args, **kwargs):
        self.log(logging.DEBUG + 4, msg, *args, **kwargs)

    logging.Logger.leave = leave

    dpy_logger = logging.getLogger("discord")
    dpy_logger.addHandler(stream_handler)
    dpy_logger.setLevel(logging.DEBUG)

    logger.info("로깅 설정 완료!")
