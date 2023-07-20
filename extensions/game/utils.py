import json
import random


__all__ = ["get_transition", "get_word", "choose_first_word", "is_hanbang"]


with open("static/wordlist.json", "r", encoding="utf-8") as f:
    wordlist: dict[str, list[str]] = json.load(f)

with open("static/transition.json", "r", encoding="utf-8") as f:
    transition: dict[str, list[str]] = json.load(f)


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
