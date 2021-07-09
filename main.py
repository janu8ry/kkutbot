import logging

from rich import traceback

from tools.logger import setup_logger

logger = logging.getLogger("kkutbot")

if __name__ == "__main__":
    traceback.install()
    setup_logger()
