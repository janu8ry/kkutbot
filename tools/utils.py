from datetime import timedelta
from typing import Union

from .config import config  # noqa


def time_convert(time: Union[int, float, timedelta]) -> str:
    if isinstance(time, (int, float)):
        time = timedelta(seconds=time)
    if time.days > 0:
        return f"{time.days}일"
    if time.seconds >= 3600:
        return f"{time.seconds // 3600}시간"
    if time.seconds >= 60:
        return f"{time.seconds // 60}분"
    return f"{time.seconds}초"
