import asyncio
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from config import MainDBData, TestDBData, config  # noqa

dbconfig: MainDBData | TestDBData = getattr(config.mongo, "test" if config.is_test else "main")
db_options: dict[str, Any] = {}

if all([username := dbconfig.username, password := dbconfig.password]):
    db_options["username"] = username
    db_options["password"] = password
    db_options["authSource"] = "admin"

_client = AsyncIOMotorClient(host=dbconfig.host, port=dbconfig.port, **db_options)
db = _client[dbconfig.db]


def _coerce_scalars(doc: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {k: int(v) for k in keys if isinstance(v := doc.get(k), float)}


def _coerce_dict(doc: dict[str, Any], path: str) -> dict[str, Any]:
    target: Any = doc
    for part in path.split("."):
        target = target.get(part) if isinstance(target, dict) else None
    if not isinstance(target, dict):
        return {}
    return {f"{path}.{k}": int(v) for k, v in target.items() if isinstance(v, float)}


FLOAT_FIELDS: dict[str, dict[str, list[str]]] = {
    "user": {
        "scalars": ["registered", "latest_reward", "latest_usage"],
        "dicts": ["attendance", "quest.cache"],
    },
    "guild": {
        "scalars": ["invited", "latest_usage"],
        "dicts": [],
    },
    "public": {
        "scalars": ["latest_usage"],
        "dicts": [],
    },
}

SOLO_TIER_CRITERIA: list[tuple[str, int, int]] = [
    ("마스터", 80, 200),
    ("골드", 70, 100),
    ("실버", 55, 50),
    ("브론즈", 40, 30),
    ("뉴비", 30, 15),
]

NEW_TIER_MAP: dict[str, tuple[str, int]] = {
    "마스터": ("다이아몬드", 3),
    "골드": ("플래티넘", 3),
    "실버": ("골드", 3),
    "브론즈": ("실버", 2),
    "뉴비": ("브론즈", 1),
}


def _winrate(win: int, times: int) -> float:
    return 0 if (times == 0 or win == 0) else round(win / times * 100, 2)


def _place_solo(win: int, times: int) -> tuple[str, int]:
    wr = _winrate(win, times)
    for name, w, t in SOLO_TIER_CRITERIA:
        if wr >= w and times >= t:
            return NEW_TIER_MAP[name]
    return ("브론즈", 3) if times >= 5 else ("언랭크", 0)


async def _migrate_floats() -> None:
    for name, fields in FLOAT_FIELDS.items():
        collection: AsyncIOMotorCollection = db[name]
        fixed = 0
        async for doc in collection.find():
            update = _coerce_scalars(doc, fields["scalars"])
            for path in fields["dicts"]:
                update |= _coerce_dict(doc, path)
            if update:
                await collection.update_one({"_id": doc["_id"]}, {"$set": update})
                fixed += 1
        print(f"{name}: {fixed}개 문서의 float 필드를 int로 변환")


async def _migrate_tiers() -> None:
    fixed = 0
    async for doc in db.user.find({}, {"game.rank_solo.win": 1, "game.rank_solo.times": 1}):
        rs = doc.get("game", {}).get("rank_solo", {})
        tier, division = _place_solo(rs.get("win", 0), rs.get("times", 0))
        await db.user.update_one(
            {"_id": doc["_id"]},
            {"$set": {"game.rank_solo.tier": tier, "game.rank_solo.division": division, "game.rank_solo.lp": 0}},
        )
        fixed += 1
    print(f"user: {fixed}개 문서의 솔로 티어를 신규 체계로 배치")


async def main() -> None:
    await _migrate_floats()
    await _migrate_tiers()


if __name__ == "__main__":
    target_db = "테스트" if config.is_test else "메인(운영)"
    answer = input(f"'{dbconfig.db}' [{target_db}] DB에 마이그레이션을 실행합니다. 계속하려면 'y'를 입력하세요: ")
    if answer.strip().lower() == "y":
        asyncio.run(main())
    else:
        print("취소되었습니다.")
