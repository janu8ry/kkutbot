import json
import random
from enum import Enum, auto

__all__ = ["get_transition", "get_word", "choose_first_word", "is_hanbang", "WordCheck", "check_word", "word_error_message"]


with open("static/wordlist.json", "r", encoding="utf-8") as f:
    wordlist: dict[str, list[str]] = json.load(f)

with open("static/transition.json", "r", encoding="utf-8") as f:
    transition: dict[str, list[str]] = json.load(f)

all_words: list[str] = [w for words in wordlist.values() for w in words]
kkd_words: list[str] = [w for w in all_words if len(w) == 3]


def get_transition(word: str) -> list[str]:
    if word[-1] in transition:
        return transition[word[-1]]
    else:
        return [word[-1]]


def get_word(word: str) -> list[str]:
    du = get_transition(word)
    return_list = []
    for x in du:
        if x in wordlist:
            return_list += wordlist[x]
    return return_list


def choose_first_word(kkd: bool = False) -> str:
    candidates = kkd_words if kkd else all_words
    while True:
        bot_word = random.choice(candidates)
        if len(get_word(bot_word)) >= 3:
            return bot_word


def is_hanbang(word: str, used_words: list[str], kkd: bool = False) -> bool:
    if kkd:
        words = [w for w in get_word(word) if len(w) == 3]
    else:
        words = get_word(word)
    if not [w for w in words if w not in used_words]:
        return True
    return False


class WordCheck(Enum):
    OK = auto()
    SURRENDER = auto()
    SURRENDER_DENIED = auto()
    ALREADY_USED = auto()
    WRONG_START = auto()
    WRONG_LENGTH = auto()
    NOT_A_WORD = auto()
    HANBANG_FIRST_ROUND = auto()


def check_word(user_word: str, current_word: str, used_words: list[str], *, first_round: bool, can_surrender: bool, kkd: bool = False) -> WordCheck:
    if user_word in ("ㅈㅈ", "gg", "GG"):
        return WordCheck.SURRENDER if can_surrender else WordCheck.SURRENDER_DENIED
    if user_word in used_words:
        return WordCheck.ALREADY_USED
    if user_word[0] not in get_transition(current_word):
        return WordCheck.WRONG_START
    if kkd and len(user_word) != 3:
        return WordCheck.WRONG_LENGTH
    if user_word not in get_word(current_word):
        return WordCheck.NOT_A_WORD
    if first_round and is_hanbang(user_word, used_words, kkd=kkd):
        return WordCheck.HANBANG_FIRST_ROUND
    return WordCheck.OK


def word_error_message(result: WordCheck, user_word: str, current_word: str) -> str:
    du = get_transition(current_word)
    messages = {
        WordCheck.SURRENDER_DENIED: "{denied} 5턴 이상 진행해야 포기할 수 있습니다.",
        WordCheck.ALREADY_USED: f"{{denied}} **{user_word}** (은)는 이미 사용한 단어입니다.",
        WordCheck.WRONG_START: f"{{denied}} **{'** 또는 **'.join(du)}** (으)로 시작하는 단어를 입력해 주세요.",
        WordCheck.WRONG_LENGTH: "{denied} 세글자 단어만 사용 가능합니다.",
        WordCheck.NOT_A_WORD: f"{{denied}} **{user_word}** (은)는 없는 단어입니다.",
        WordCheck.HANBANG_FIRST_ROUND: "{denied} 첫번째 회차에서는 한방단어를 사용할 수 없습니다.",
    }
    return messages[result]
