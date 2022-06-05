from datetime import timedelta
from typing import Union

from discord.ext import commands

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


def is_admin(ctx: commands.Context) -> bool:
    return ctx.author.id in config('admin')


def split_string(n: str, unit=2000, t="\n") -> tuple:
    n = n.split(t)
    x = []
    r = []
    for idx, i in enumerate(n):
        x.append(i)
        if idx + 1 == len(n) or sum([len(j) for j in x + [n[idx+1]]]) + len(x) > unit:
            r.append("\n".join(x))
            x = []
    return tuple(r)
