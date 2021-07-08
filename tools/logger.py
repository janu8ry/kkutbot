import logging
from logging.handlers import TimedRotatingFileHandler
import os
import gzip
import time

from rich.logging import RichHandler


def rotator(source, dest: str):
    dest = dest[5:]
    logs = [f for f in os.listdir('logs') if f.startswith(dest[:-4])]
    if f"{dest}.gz" in logs:
        dest = f"{dest[:-4]}({len(logs)}).log"
    with open(source, "rb") as rf:
        with gzip.open(f"logs/{dest}.gz", "wb") as wf:
            wf.write(rf.read())
    os.remove(source)


def namer(_):
    return os.path.join("logs", time.strftime("%Y-%m-%d") + ".log")


def setup_logger():
    logger = logging.getLogger('kkutbot')
    logger.setLevel(logging.DEBUG)

    stream_handler = RichHandler(rich_tracebacks=True)
    stream_handler.setFormatter(logging.Formatter(fmt="%(name)s :\t%(message)s"))
    stream_handler.setLevel(logging.INFO)

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join("logs", "latest.log"),
        # when="midnight"
        encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
    )

    file_handler.rotator = rotator
    file_handler.namer = namer

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    logger.info("로깅 설정 완료!")
