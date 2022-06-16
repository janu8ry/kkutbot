import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import discord
from discord.ext import commands

from tools.db import read

from .config import config  # noqa


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


def get_date(timestamp: Optional[float], from_utc: bool = False) -> str:
    if timestamp:
        if from_utc:
            return str(datetime.fromtimestamp(timestamp).astimezone(timezone(timedelta(hours=9))))[:10]
        else:
            return str(datetime.fromtimestamp(timestamp))[:10]
    else:
        return "끝봇의 유저가 아닙니다."


def get_timestamp(date: str) -> int:
    return int(time.mktime(datetime.strptime(date, '%Y-%m-%d').timetuple()))


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


async def get_winrate(target: Union[int, discord.User, discord.Member], mode: str) -> float:
    game_times = await read(target, f'game.{mode}.times')
    game_win_times = await read(target, f'game.{mode}.win')
    if 0 in (game_times, game_win_times):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


async def get_tier(target: Union[int, discord.User, discord.Member], mode: str, emoji: bool = True) -> str:
    if mode not in ("rank_solo", "rank_online"):
        raise TypeError
    tier = "언랭크 :sob:" if emoji else "언랭크"
    for k, v in config('tierlist').items():
        if (await read(target, 'points')) >= v['points'] and (await get_winrate(target, mode)) >= v['winrate'] and (await read(target, f'game.{mode}.times')) >= v['times']:
            tier = f"{k} {v['emoji']}"
        else:
            break
    return tier if emoji else tier.split(" ")[0]


async def disable_buttons(interaction: discord.Interaction, view: discord.ui.View):
    for item in view.children:
        if isinstance(item, discord.ui.Button):
            item.disabled = True
    await interaction.response.edit_message(view=view)
