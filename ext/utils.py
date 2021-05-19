import json
import random
from datetime import timedelta
from typing import Union

import discord
from discord.ext import commands

from ext.db import config, read

with open('general/wordlist.json', 'r', encoding="utf-8") as f:
    wordlist = json.load(f)

with open('general/DUlaw.json', 'r', encoding="utf-8") as f:
    DU = json.load(f)


async def get_winrate(target: Union[int, discord.User, discord.Member], mode: str) -> float:
    game_times = await read(target, f'game.{mode}.times')
    game_win_times = await read(target, f'game.{mode}.win')
    if 0 in (game_times, game_win_times):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


async def get_tier(target: Union[int, discord.User, discord.Member], mode: str, emoji: bool = True) -> str:
    if mode not in ("rank_solo", "rank_multi"):
        raise TypeError
    tier = "언랭크 :sob:" if emoji else "언랭크"
    for k, v in config('tierlist').items():
        if (await read(target, 'points')) >= v['points'] and (await get_winrate(target, mode)) >= v['winrate'] and (await read(target, f'game.{mode}.times')) >= v['times']:
            tier = f"{k} {v['emoji']}"
        else:
            break
    return tier if emoji else tier.split(" ")[0]


def time_convert(time: timedelta) -> str:
    if time.days > 0:
        return f"{time.days}일"
    if time.seconds >= 3600:
        return f"{time.seconds // 3600}시간"
    if time.seconds >= 60:
        return f"{time.seconds // 60}분"
    return f"{time.seconds}초"


def split_string(n: str, unit=2000, t="\n") -> tuple:  # thanks to seojin200403
    n = n.split(t)
    x = []
    r = []
    for idx, i in enumerate(n):
        x.append(i)
        if idx + 1 == len(n) or sum([len(j) for j in x + [n[idx+1]]]) + len(x) > unit:
            r.append("\n".join(x))
            x = []
    return tuple(r)


def get_word(_word: str) -> list:
    du = get_DU(_word[-1])
    return_list = []
    for x in du:
        if x in wordlist:
            return_list += wordlist[x[-1]]
    return return_list


def get_DU(_word: str) -> list:
    if _word[-1] in DU:
        return DU[_word[-1]]
    else:
        return [_word[-1]]


def is_admin(ctx: commands.Context) -> bool:
    return ctx.author.id in config('admin')


def choose_first_word(special: bool = False) -> str:
    while True:
        random_list = random.choice(list(wordlist.values()))
        bot_word = random.choice(random_list)
        if len(get_word(bot_word)) >= 3:
            if special:
                if len(bot_word) == 3:
                    break
            else:
                break
    return bot_word
