import time
from datetime import datetime
from typing import Any
from unicodedata import east_asian_width

from discord.ext import commands

from config import config, get_nested_dict, get_nested_property
from database.models import GameBase, RankGameBase

__all__ = [
    "fmt",
    "get_timestamp",
    "is_admin",
    "split_string",
    "get_winrate",
    "format_number",
    "truncate_by_width",
    "get_rank_display",
    "get_rank_progress",
    "get_perm_name",
    "TIER_EMOJIS",
    "PLACEMENT_GAMES",
    "get_nested_dict",
    "get_nested_property",
    "ROMAN_DIVISIONS",
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


def format_number(n: int | float) -> str:
    """
    Format numbers with 5+ digits using k/m/b/t units.
    Parameters
    ----------
    n : int | float
        Number to format
    Returns
    -------
    str
        Formatted number string
    """
    if abs(n) < 10000:
        return str(n)
    units = ((1_000_000_000_000, "t"), (1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k"))
    for div, suffix in units:
        if abs(n) >= div:
            v = n / div
            decimals = min(2, max(0, 4 - len(str(int(abs(v))))))
            factor = 10**decimals
            v = int(v * factor) / factor
            text = format(v, f".{decimals}f").rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    return str(n)


def truncate_by_width(text: str, limit: int = 15) -> str:
    """
    Truncates a string based on its display width, counting wide characters as two.
    Parameters
    ----------
    text : str
        Target string to truncate
    limit : int
        Maximum display width of the result
    Returns
    -------
    str
        Truncated string, suffixed with "..." if shortened
    """
    widths = [2 if east_asian_width(char) in "WF" else 1 for char in text]
    if sum(widths) <= limit:
        return text
    result = ""
    width = 0
    for char, char_width in zip(text, widths):
        if width + char_width > limit - 3:
            break
        result += char
        width += char_width
    return result + "..."


def get_winrate(data: GameBase) -> Any:
    game_times = data.times
    game_win_times: int = data.win
    if 0 in (game_times, game_win_times):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


ROMAN_DIVISIONS = {1: "I", 2: "II", 3: "III"}
TIER_EMOJIS = {
    "언랭크": "{unrank}",
    "브론즈": "{bronze}",
    "실버": "{silver}",
    "골드": "{gold}",
    "플래티넘": "{platinum}",
    "다이아몬드": "{diamond}",
    "마스터": "{m_master}",
}
UNRANKED = next(iter(TIER_EMOJIS))
PLACEMENT_GAMES = 5


def get_rank_display(rank: RankGameBase, emoji: bool = True) -> str:
    tier = rank.tier if rank.tier in TIER_EMOJIS else UNRANKED
    name = tier if (tier == UNRANKED or rank.division == 0) else f"{tier} {ROMAN_DIVISIONS[rank.division]}"
    return f"{name} {TIER_EMOJIS[tier]}" if emoji else name


def get_rank_progress(rank: RankGameBase) -> str:
    if rank.tier not in TIER_EMOJIS or rank.tier == UNRANKED:
        return get_rank_display(rank)
    return f"{get_rank_display(rank)} | `{rank.lp}` LP"


PERM_NAMES = {
    "send_messages": "메시지 보내기",
    "embed_links": "링크 첨부",
    "attach_files": "파일 첨부",
    "read_messages": "채팅 채널 읽기",
    "add_reactions": "반응 추가하기",
    "external_emojis": "외부 이모티콘 사용하기",
    "use_application_commands": "애플리케이션 명령어 사용",
}


def get_perm_name(perm: str) -> str:
    """
    Translates a discord permission flag into Korean.
    Parameters
    ----------
    perm : str
        Permission flag name to translate
    Returns
    -------
    str
        Korean name, or the flag name itself when no translation exists
    """
    return PERM_NAMES.get(perm, perm)
