import logging
from logging.handlers import TimedRotatingFileHandler
import os
import gzip

from rich.logging import RichHandler


def rotator(source, dest):
    with open(source, "rb") as rf:
        with gzip.open(f"{dest}.log.gz", "wb") as wf:
            wf.write(rf.read())
    os.remove(source)


def namer(name):
    return name + ".log.gz"


def setup_logger():
    logger = logging.getLogger('kkutbot')
    logger.setLevel(logging.DEBUG)

    stream_handler = RichHandler(rich_tracebacks=True)
    stream_handler.setFormatter(logging.Formatter(fmt="%(name)s :\t%(message)s"))
    stream_handler.setLevel(logging.INFO)

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join("logs", "logs.log"),
        when="midnight",
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


