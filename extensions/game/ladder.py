import math
import random
from collections import Counter, defaultdict
from typing import Any

from database.models import RankGameBase

from .words import all_words, choose_first_word, dead_end_words, dead_ends_after, get_reply_stats, get_transition, word_weight

__all__ = [
    "get_win_lp",
    "get_lose_lp",
    "update_ladder",
    "get_difficulty_tier",
    "get_bot_surrender_threshold",
    "choose_bot_word",
    "choose_opening_word",
    "get_rank_progress",
    "TIER_EMOJIS",
    "PLACEMENT_GAMES",
]

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
DEFAULT_LOSE_LP = 15
LOSE_LP: dict[str, int] = {"플래티넘": 16, "다이아몬드": 18, "마스터": 20}

PLACEMENT_MAP: dict[int, tuple[str, int]] = {
    0: ("브론즈", 3),
    1: ("브론즈", 2),
    2: ("브론즈", 1),
    3: ("실버", 2),
    4: ("골드", 3),
    5: ("플래티넘", 3),
}
PLACEMENT_DIFFICULTY = ("브론즈", "실버", "골드", "플래티넘", "플래티넘")
#   surrender : 봇의 응답 후보 단어 개수가 이 값 이하일 경우 유저의 승리로 처리
#   target    : 유저가 답할 수 있는 단어 개수의 중심값. 후보 단어의 길이별로 가중치 적용
#   hanbang   : 한방단어 확률
#   pressure  : 이미 사용한 끝글자를 다시 고를 가중치 (1 + pressure × 소비 횟수)
#   dodge     : 한방단어가 존재하지 않는 단어를 낼 확률
DIFFICULTY: dict[str, dict[str, Any]] = {
    "브론즈": {"surrender": 4, "target": 700, "hanbang": 0.0, "pressure": 0.0, "dodge": 0.0},
    "실버": {"surrender": 3, "target": 400, "hanbang": 0.0, "pressure": 0.0, "dodge": 0.0},
    "골드": {"surrender": 2, "target": 250, "hanbang": 0.0, "pressure": 0.0, "dodge": 0.1},
    "플래티넘": {"surrender": 1, "target": 175, "hanbang": 0.005, "pressure": 0.1, "dodge": 0.3},
    "다이아몬드": {"surrender": 0, "target": 100, "hanbang": 0.01, "pressure": 0.3, "dodge": 0.6},
    "마스터": {"surrender": 0, "target": 60, "hanbang": 0.02, "pressure": 0.7, "dodge": 0.9},
}
SIGMA = 0.5  # target에서 단어 개수의 퍼짐 정도
OPENING_SAMPLE_SIZE = 1000


def get_rank_display(rank: RankGameBase, emoji: bool = True) -> str:
    tier = rank.tier if rank.tier in TIER_EMOJIS else UNRANKED
    name = tier if (tier == UNRANKED or rank.division == 0) else f"{tier} {'I' * rank.division}"
    return f"{name} {TIER_EMOJIS[tier]}" if emoji else name


def get_rank_progress(rank: RankGameBase) -> str:
    if rank.tier not in TIER_EMOJIS or rank.tier == UNRANKED:
        return get_rank_display(rank)
    return f"{get_rank_display(rank)} | `{rank.lp}` LP"


def get_win_lp(score: int) -> int:
    return 20 + max(0, min(5, (score - 11) // 4))


def get_lose_lp(tier: str) -> int:
    return LOSE_LP.get(tier, DEFAULT_LOSE_LP)


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
        lose_lp = get_lose_lp(rank.tier)
        if rank.lp >= lose_lp:
            rank.lp -= lose_lp
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


def grade_word(word: str, used: set[str], heads: Counter[str], head_weights: defaultdict[str, float]) -> tuple[int, float]:
    """(응답 가능한 단어 수, 길이 가중 점수). 음절별 집계에서 사용된 단어만 빼므로 사전 전체를 훑지 않는다."""
    replies, score = get_reply_stats(word)
    group = get_transition(word)
    for char in group:
        replies -= heads[char]
        score -= head_weights[char]
    if word[0] in group and word not in used:
        replies -= 1
        score -= word_weight(word)
    return replies, score


def choose_bot_word(candidates: list[str], used_words: list[str], tier: str) -> str | None:
    conf = DIFFICULTY[tier]
    if random.random() < conf["hanbang"] and (dead_ends := [w for w in candidates if w in dead_end_words]):
        return random.choice(dead_ends)
    used = set(used_words)
    heads = Counter(w[0] for w in used)
    head_weights: defaultdict[str, float] = defaultdict(float)
    for word in used:
        head_weights[word[0]] += word_weight(word)
    graded = [(w, *grade_word(w, used, heads, head_weights)) for w in candidates]
    graded = [g for g in graded if g[1] > 0]
    if not graded:
        return None
    if random.random() < conf["dodge"]:
        graded = [g for g in graded if not (dead_ends_after(g[0]) - used)] or graded

    # 끝글자로 묶어 뽑는다. 단어 단위로 추첨하면 '법'처럼 그 글자로 끝나는 단어가 많은 쪽이
    # 사전 수록량만큼 과대 대표되어, 티어마다 같은 글자가 반복 출제된다.
    groups: defaultdict[str, list[tuple[str, int, float]]] = defaultdict(list)
    for g in graded:
        groups[g[0][-1]].append(g)
    center, pressure = math.log(conf["target"]), conf["pressure"]
    keys = list(groups)
    weights = [math.exp(-((math.log(max(groups[k][0][2], 1.0)) - center) ** 2) / (2 * SIGMA**2)) * (1.0 + pressure * heads[k]) for k in keys]
    if not any(weights):
        return random.choice(graded)[0]
    return random.choice(groups[random.choices(keys, weights)[0]])[0]


def choose_opening_word(tier: str, kkd: bool = False) -> str:
    if kkd:
        return choose_first_word(kkd=True)
    pool = [w for w in random.sample(all_words, OPENING_SAMPLE_SIZE) if w not in dead_end_words]
    return choose_bot_word(pool, [], tier) or choose_first_word()
