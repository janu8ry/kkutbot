import json
import random
import time
from datetime import datetime, timedelta
from typing import Any, Union

import discord
from discord.ext import commands

from config import config  # noqa
from tools.db import read

with open("static/wordlist.json", "r", encoding="utf-8") as f:
    wordlist: dict[str, list[str]] = json.load(f)

with open("static/transition.json", "r", encoding="utf-8") as f:
    transition: dict[str, list[str]] = json.load(f)


def time_convert(timeinfo: Union[int, float, timedelta]) -> str:
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


def format_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def get_timestamp(date: str) -> int:
    return int(time.mktime(datetime.strptime(date, "%Y-%m-%d").timetuple()))


def is_admin(ctx: commands.Context) -> bool:
    return ctx.author.id in config("admin")


def split_string(w: str, unit: int = 2000, t: str = "\n") -> tuple[str, ...]:
    n = w.split(t)
    x: list[str] = []
    r: list[str] = []
    for idx, i in enumerate(n):
        x.append(i)
        if idx + 1 == len(n) or sum([len(j) for j in x + [n[idx+1]]]) + len(x) > unit:
            r.append("\n".join(x))
            x = []
    return tuple(r)


async def get_winrate(target: Union[int, discord.User, discord.Member], mode: str) -> Any:
    game_times: int = await read(target, f"game.{mode}.times")
    game_win_times: int = await read(target, f"game.{mode}.win")
    if 0 in (game_times, game_win_times):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


async def get_tier(target: Union[int, discord.User, discord.Member], mode: str, emoji: bool = True) -> str:
    if mode not in ("rank_solo", "rank_online"):
        raise TypeError
    tier = "언랭크 :sob:" if emoji else "언랭크"
    for k, v in config("tierlist").items():
        if (await read(target, "points")) >= v["points"] and (await get_winrate(target, mode)) >= v["winrate"] and (await read(target, f"game.{mode}.times")) >= v["times"] and (await read(target, f"game.{mode}.best")) >= v["best"]:
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
