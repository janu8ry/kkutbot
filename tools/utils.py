import time
from datetime import datetime, timedelta
from typing import Any

from discord.ext import commands

from config import config, get_nested_dict, get_nested_property
from database.models import GameBase, User

__all__ = [
    "dict_emojis",
    "fmt",
    "time_convert",
    "get_timestamp",
    "is_admin",
    "split_string",
    "get_winrate",
    "get_tier",
    "get_nested_dict",
    "get_nested_property",
]


class FormattingDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def dict_emojis() -> dict[str, str]:
    return {k: f"<:{k}:{v}>" for k, v in config.emojis.items()}


def fmt(text: str) -> str:
    """
    Replaces "{emoji_name}" placeholders in the text with actual emojis.
    Parameters
    ----------
    text : str
        Target string containing emoji placeholders
    Returns
    -------
    str
        String with placeholders replaced by emojis
    """
    return text.format_map(FormattingDict(dict_emojis()))


def time_convert(timeinfo: int | float | timedelta) -> str:
    """
    Converts time to the largest unit.
    Parameters
    ----------
    timeinfo : int | float | timedelta
        Time value to convert
    Returns
    -------
    str
        Converted time string
    """
    if isinstance(timeinfo, (int, float)):
        timeinfo = timedelta(seconds=timeinfo)
    if timeinfo.days > 365:
        return f"{timeinfo.days // 365}년"
    elif timeinfo.days > 0:
        return f"{timeinfo.days}일"
    elif timeinfo.seconds >= 3600:
        return f"{timeinfo.seconds // 3600}시간"
    elif timeinfo.seconds >= 60:
        return f"{timeinfo.seconds // 60}분"
    return f"{timeinfo.seconds}초"


def get_timestamp(date: str) -> int:
    """
    Converts a date string to a Unix timestamp.
    Parameters
    ----------
    date : str
        Date string to convert
    Returns
    -------
    int
        Converted Unix timestamp
    """
    return int(time.mktime(datetime.strptime(date, "%Y-%m-%d").timetuple()))


def is_admin(ctx: commands.Context) -> bool:
    return ctx.author.id in config.admin


def split_string(w: str, unit: int = 2000, t: str = "\n") -> tuple[str, ...]:
    """
    Splits a given string into chunks.
    Parameters
    ----------
    w : str
        Target string to split
    unit : int
        Maximum size of each chunk
    t : str
        End character of each chunk
    Returns
    -------
    tuple[str, ...]
        Tuple of split strings
    """
    n = w.split(t)
    x: list[str] = []
    r: list[str] = []
    for idx, i in enumerate(n):
        x.append(i)
        if idx + 1 == len(n) or sum([len(j) for j in x + [n[idx + 1]]]) + len(x) > unit:
            r.append("\n".join(x))
            x = []
    return tuple(r)


def get_winrate(data: GameBase) -> Any:
    game_times = data.times
    game_win_times: int = data.win
    if 0 in (game_times, game_win_times):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


def get_tier(data: User, mode: str, emoji: bool = True) -> str:
    if mode not in ("rank_solo", "rank_online"):
        raise TypeError
    tier = "언랭크 :sob:" if emoji else "언랭크"
    modes = {"rank_solo": data.game.rank_solo, "rank_online": data.game.rank_online}
    for k, v in config.tierlist.items():
        if (
            data.points >= v["points"]
            and get_winrate(modes[mode]) >= v["winrate"]
            and modes[mode].times >= v["times"]
            and modes[mode].best >= v["best"]
        ):
            tier = f"{k} {v['emoji']}"
        else:
            break
    return tier if emoji else tier.split(" ")[0]
