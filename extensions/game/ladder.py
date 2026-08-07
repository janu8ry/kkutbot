import random
from typing import Any

from database.models import RankGameBase

from .words import get_word

__all__ = [
    "get_win_lp",
    "get_lose_lp",
    "update_ladder",
    "get_difficulty_tier",
    "get_bot_surrender_threshold",
    "choose_bot_word",
    "get_rank_display",
    "get_rank_progress",
    "TIER_EMOJIS",
    "ROMAN_DIVISIONS",
    "PLACEMENT_GAMES",
]

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
TIERS = list(TIER_EMOJIS)
UNRANKED = TIERS[0]
LOWEST_TIER = TIERS[1]
HIGHEST_TIER = TIERS[-1]
PLACEMENT_GAMES = 5
LP_PER_DIVISION = 100
DIVISIONS = 3
DIVISION_DEMOTION_LP = 85
TIER_DEMOTION_LP = 50

PLACEMENT_MAP: dict[int, tuple[str, int]] = {
    0: ("브론즈", 3),
    1: ("브론즈", 2),
    2: ("브론즈", 1),
    3: ("실버", 3),
    4: ("실버", 1),
    5: ("골드", 1),
}
PLACEMENT_DIFFICULTY = ("브론즈", "브론즈", "실버", "골드", "플래티넘")
DIFFICULTY: dict[str, dict[str, Any]] = {
    "브론즈": {"surrender": 4, "band": (0.0, 0.5), "hanbang": False},
    "실버": {"surrender": 3, "band": (0.1, 0.7), "hanbang": False},
    "골드": {"surrender": 2, "band": (0.2, 0.9), "hanbang": False},
    "플래티넘": {"surrender": 1, "band": (0.4, 0.9), "hanbang": True},
    "다이아몬드": {"surrender": 0, "band": (0.6, 1.0), "hanbang": True},
    "마스터": {"surrender": 0, "band": (0.75, 1.0), "hanbang": True},
}
DIFFICULTY_SAMPLE_SIZE = 50


def get_rank_display(rank: RankGameBase, emoji: bool = True) -> str:
    tier = rank.tier if rank.tier in TIER_EMOJIS else UNRANKED
    name = tier if (tier == UNRANKED or rank.division == 0) else f"{tier} {ROMAN_DIVISIONS[rank.division]}"
    return f"{name} {TIER_EMOJIS[tier]}" if emoji else name


def get_rank_progress(rank: RankGameBase) -> str:
    if rank.tier not in TIER_EMOJIS or rank.tier == UNRANKED:
        return get_rank_display(rank)
    return f"{get_rank_display(rank)} | `{rank.lp}` LP"


def get_win_lp(score: int) -> int:
    return 20 + max(0, min(5, (score - 11) // 4))


def get_lose_lp() -> int:
    return 15


def update_ladder(rank: RankGameBase, won: bool, score: int) -> tuple[str, str, bool] | None:
    before = (rank.tier, rank.division)
    before_display = get_rank_display(rank)

    if rank.tier == UNRANKED:
        remaining = rank.division or PLACEMENT_GAMES
        if won:
            rank.lp |= 1 << (PLACEMENT_GAMES - remaining)
        remaining -= 1
        if remaining > 0:
            rank.division = remaining
            return None
        rank.tier, rank.division = PLACEMENT_MAP[rank.lp.bit_count()]
        rank.lp = 0
    elif won:
        rank.lp += get_win_lp(score)
        if rank.tier == HIGHEST_TIER:
            pass
        elif rank.lp >= LP_PER_DIVISION:
            if rank.division > 1:
                rank.division -= 1
            else:
                next_tier = TIERS[TIERS.index(rank.tier) + 1]
                rank.tier = next_tier
                rank.division = 0 if next_tier == HIGHEST_TIER else DIVISIONS
            rank.lp -= LP_PER_DIVISION
            if rank.lp == 0:
                rank.lp = 1
    else:
        if rank.lp >= get_lose_lp():
            rank.lp -= get_lose_lp()
        elif rank.lp >= 1:
            rank.lp = 0
        elif rank.tier == LOWEST_TIER and rank.division == DIVISIONS:
            pass
        elif rank.tier != HIGHEST_TIER and rank.division < DIVISIONS:
            rank.division += 1
            rank.lp = DIVISION_DEMOTION_LP
        else:
            rank.tier = TIERS[TIERS.index(rank.tier) - 1]
            rank.division = 1
            rank.lp = TIER_DEMOTION_LP

    if (rank.tier, rank.division) == before:
        return None
    promoted = (TIERS.index(rank.tier), -rank.division) > (TIERS.index(before[0]), -before[1])
    return before_display, get_rank_display(rank), promoted


def get_difficulty_tier(rank: RankGameBase) -> str:
    if rank.tier == UNRANKED:
        played = PLACEMENT_GAMES - (rank.division or PLACEMENT_GAMES)
        return PLACEMENT_DIFFICULTY[min(played, PLACEMENT_GAMES - 1)]
    return rank.tier


def get_bot_surrender_threshold(tier: str) -> int:
    return DIFFICULTY[tier]["surrender"]


def choose_bot_word(candidates: list[str], used_words: list[str], tier: str) -> str | None:
    conf = DIFFICULTY[tier]
    sample = random.sample(candidates, min(DIFFICULTY_SAMPLE_SIZE, len(candidates)))
    used = set(used_words)
    graded = sorted(((w, sum(1 for x in get_word(w) if x not in used and x != w)) for w in sample), key=lambda t: -t[1])
    if not conf["hanbang"]:
        graded = [(w, c) for w, c in graded if c > 0]
        if not graded:
            return None
    lo, hi = conf["band"]
    start = int(len(graded) * lo)
    end = max(int(len(graded) * hi), start + 1)
    return random.choice(graded[start:end])[0]
