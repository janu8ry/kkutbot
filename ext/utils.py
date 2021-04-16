from datetime import timedelta
import random
from typing import Union

import discord
from discord.ext import commands

from ext.db import read, config
from ext.bot import Kkutbot

DU = Kkutbot.DUlaw()
wordlist = Kkutbot.wordlist()


def get_winrate(target: Union[int, discord.User, discord.Member], mode: str) -> float:
    game_times = read(target, f'game.{mode}.times')
    game_win_times = read(target, f'game.{mode}.win')
    if (game_times == 0) or (game_win_times == 0):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


def get_tier(target: Union[int, discord.User, discord.Member], mode: str, emoji: bool = True) -> str:
    tier = "언랭크 :sob:" if emoji else "언랭크"
    for k, v in config('tierlist').items():
        if read(target, 'points') >= v['points'] and get_winrate(target, mode) >= v['winrate'] and read(target, f'game.{mode}.times') >= v['times']:
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
    x = list()
    r = list()
    for idx, i in enumerate(n):
        x.append(i)
        if idx + 1 == len(n) or sum([len(j) for j in x + [n[idx+1]]]) + len(x) > unit:
            r.append("\n".join(x))
            x = list()
    return tuple(r)


def get_word(_word: str) -> list:
    du = get_DU(_word[-1])
    return_list = list()
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


if __name__ == "__main__":
    pass
