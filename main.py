import logging

from rich.traceback import install as rich_install

from tools.logger import setup_logger

logger = logging.getLogger("kkutbot")

if __name__ == "__main__":
    rich_install()
    setup_logger()
