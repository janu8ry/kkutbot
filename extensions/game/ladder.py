import random
from typing import Any

from database.models import RankGameBase

from .words import dead_end_words, get_word

__all__ = [
    "get_win_lp",
    "get_lose_lp",
    "update_ladder",
    "get_difficulty_tier",
    "get_bot_surrender_threshold",
    "choose_bot_word",
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
    "브론즈": {"surrender": 4, "target": 330, "variety": 12, "hanbang": 0.0},
    "실버": {"surrender": 3, "target": 240, "variety": 12, "hanbang": 0.0},
    "골드": {"surrender": 2, "target": 190, "variety": 12, "hanbang": 0.0},
    "플래티넘": {"surrender": 1, "target": 145, "variety": 12, "hanbang": 0.0},
    "다이아몬드": {"surrender": 0, "target": 95, "variety": 10, "hanbang": 0.02},
    "마스터": {"surrender": 0, "target": 70, "variety": 10, "hanbang": 0.04},
}
DIFFICULTY_SAMPLE_SIZE = 120


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
        if won:
            rank.lp |= 1 << (rank.times - 1)
        if rank.times < PLACEMENT_GAMES:
            return None
        rank.tier, rank.division = PLACEMENT_MAP[rank.lp.bit_count()]
        rank.lp = 1
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
        return PLACEMENT_DIFFICULTY[min(rank.times, PLACEMENT_GAMES - 1)]
    return rank.tier


def get_bot_surrender_threshold(tier: str) -> int:
    return DIFFICULTY[tier]["surrender"]


def grade_word(word: str, used: set[str]) -> tuple[int, int]:
    replies = [x for x in get_word(word) if x not in used and x != word]
    return len(replies), sum(1 for x in replies if len(x) == 2)


def choose_bot_word(candidates: list[str], used_words: list[str], tier: str) -> str | None:
    conf = DIFFICULTY[tier]
    sample = random.sample(candidates, min(DIFFICULTY_SAMPLE_SIZE, len(candidates)))
    used = set(used_words)
    graded = [(w, *grade_word(w, used)) for w in sample]
    if not conf["hanbang"]:
        graded = [g for g in graded if g[1] > 0]
        if not graded:
            return None
    elif random.random() < conf["hanbang"] and (dead_ends := [w for w in candidates if w in dead_end_words]):
        return random.choice(dead_ends)
    graded.sort(key=lambda g: abs(g[2] - conf["target"]))
    return random.choice(graded[: conf["variety"]])[0]
