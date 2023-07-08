import json
import random
import time
from datetime import datetime, timedelta
from typing import Any, Union, Type

from discord.ext import commands

from config import config, get_nested_dict, get_nested_property
from database.models import User, GameBase  # noqa

__all__ = [
    "time_convert", "get_timestamp", "is_admin", "split_string", "get_winrate",
    "get_tier", "get_transition", "get_word", "is_hanbang", "choose_first_word",
    "get_nested_dict", "get_nested_property"
]

with open("static/wordlist.json", "r", encoding="utf-8") as f:
    wordlist: dict[str, list[str]] = json.load(f)

with open("static/transition.json", "r", encoding="utf-8") as f:
    transition: dict[str, list[str]] = json.load(f)


def time_convert(timeinfo: Union[int, float, timedelta]) -> str:
    """
    converts time into biggest unit.
    Parameters
    ----------
    timeinfo : Union[int, float, timedelta]
        time object to convert
    Returns
    -------
    str
        converted time unit
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
    converts date into unix timestamp.
    Parameters
    ----------
    date : str
        time object to convert
    Returns
    -------
    int
        converted unix timestamp
    """
    return int(time.mktime(datetime.strptime(date, "%Y-%m-%d").timetuple()))


def is_admin(ctx: commands.Context) -> bool:
    return ctx.author.id in config.admin


def split_string(w: str, unit: int = 2000, t: str = "\n") -> tuple[str, ...]:
    """
    splits given strings into unit.
    Parameters
    ----------
    w : str
        target string to split
    unit: int
        size of unit
    t: str
        end char of each unit
    Returns
    -------
    tuple[str, ...]
        tuple of splitted string
    """
    n = w.split(t)
    x: list[str] = []
    r: list[str] = []
    for idx, i in enumerate(n):
        x.append(i)
        if idx + 1 == len(n) or sum([len(j) for j in x + [n[idx+1]]]) + len(x) > unit:
            r.append("\n".join(x))
            x = []
    return tuple(r)


def get_winrate(data: Type[GameBase]) -> Any:
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
    modes = {'rank_solo': data.game.rank_solo, 'kkd': data.game.kkd}
    for k, v in config.tierlist.items():
        if data.points >= v["points"] and get_winrate(modes[mode]) >= v["winrate"] and modes[mode].times >= v["times"] and modes[mode].best >= v["best"]:
            tier = f"{k} {v['emoji']}"
        else:
            break
    return tier if emoji else tier.split(" ")[0]


def get_transition(word: str) -> list[str]:
    if word[-1] in transition:
        return transition[word[-1]]
    else:
        return [word[-1]]


def get_word(word: str) -> list[str]:
    du = get_transition(word[-1])
    return_list = []
    for x in du:
        if x in wordlist:
            return_list += wordlist[x[-1]]
    return return_list


def choose_first_word(kkd: bool = False) -> str:
    while True:
        random_list = random.choice(list(wordlist.values()))
        bot_word = random.choice(random_list)
        if len(get_word(bot_word)) >= 3:
            if kkd:
                if len(bot_word) == 3:
                    break
            else:
                break
    return bot_word


def is_hanbang(word: str, used_words: list[str], kkd: bool = False) -> bool:
    if kkd:
        words = [w for w in get_word(word) if len(w) == 3]
    else:
        words = get_word(word)
    if not [w for w in words if w not in used_words]:
        return True
    return False
