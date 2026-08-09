import asyncio
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from config import Mongo, config  # noqa

dbconfig: Mongo = config.mongo
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


COMMAND_MERGE: dict[str, str] = {
    "끝말잇기1": "끝말잇기",
    "끝말잇기2": "다인전",
    "끝말잇기3": "쿵쿵따",
    "통계": "프로필",
    "정보": "프로필",
    "소개말": "프로필",
    "지원금": "포인트",
    "메일": "공지",
    "커뮤니티": "도움",
}
COMMAND_DROP: set[str] = {"핑", "슬롯", "뱝", "재생"}

MAX_ORDINAL = datetime.max.toordinal()
GAME_MODES = ("rank_solo", "rank_online", "long", "kkd", "guild_multi", "online_multi")
RANK_MODES = ("rank_solo", "rank_online")
UNRANKED_SOLO = {"times": 0, "win": 0, "best": 0, "winrate": 0.0, "streak": 0, "tier": "언랭크", "division": 0, "lp": 0}
LEGACY_COLLECTIONS = ("general", "unused")


async def _migrate_command_stats() -> None:
    public = await db.public.find_one({"_id": "public"})
    if not public:
        print("public 문서가 없어 명령어 통계 마이그레이션을 건너뜁니다")
        return
    commands: dict[str, int] = public.get("commands") or {}
    new: dict[str, int] = {}
    for name, count in commands.items():
        if name.startswith("jishaku") or name.startswith("_") or name in COMMAND_DROP:
            continue
        target = COMMAND_MERGE.get(name, name)
        new[target] = new.get(target, 0) + count
    await db.public.update_one({"_id": "public"}, {"$set": {"commands": new}})
    print(f"public: 명령어 통계를 {len(new)}개로 정리")


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
    placed = reset = 0
    async for doc in db.user.find({}, {"game.rank_solo.win": 1, "game.rank_solo.times": 1}):
        rs = doc.get("game", {}).get("rank_solo", {})
        tier, division = _place_solo(rs.get("win", 0), rs.get("times", 0))
        if tier == "언랭크":
            update = {"game.rank_solo": UNRANKED_SOLO}
            reset += 1
        else:
            update = {"game.rank_solo.tier": tier, "game.rank_solo.division": division, "game.rank_solo.lp": 0}
            placed += 1
        await db.user.update_one({"_id": doc["_id"]}, {"$set": update})
    print(f"user: {placed}개 문서의 솔로 티어를 신규 체계로 배치, {reset}개 문서의 솔로 전적을 초기화")


async def _migrate_reward() -> None:
    fixed = 0
    async for doc in db.user.find({"latest_reward": {"$gt": 0, "$lte": MAX_ORDINAL}}, {"latest_reward": 1}):
        midnight = round(datetime.fromordinal(doc["latest_reward"]).timestamp())
        await db.user.update_one({"_id": doc["_id"]}, {"$set": {"latest_reward": midnight}})
        fixed += 1
    print(f"user: {fixed}개 문서의 latest_reward를 날짜 서수에서 타임스탬프로 변환")
    result = await db.user.update_many(
        {"reward": {"$exists": False}},
        [
            {
                "$set": {
                    "reward": {
                        "latest": {"$cond": [{"$gt": ["$latest_reward", 0]}, "$latest_reward", None]},
                        "streak": {"$ifNull": ["$reward_streak", 0]},
                    }
                }
            }
        ],
    )
    print(f"user: {result.modified_count}개 문서의 수령 정보를 reward 하위 문서로 이동")
    result = await db.user.update_many(
        {"$or": [{"latest_reward": {"$exists": True}}, {"reward_streak": {"$exists": True}}]},
        {"$unset": {"latest_reward": "", "reward_streak": ""}},
    )
    print(f"user: {result.modified_count}개 문서에서 구 latest_reward/reward_streak 필드 제거")


async def _migrate_global_name() -> None:
    result = await db.user.update_many(
        {"global_name": {"$exists": False}},
        [{"$set": {"global_name": "$name"}}],
    )
    print(f"user: {result.modified_count}개 문서에 global_name(=name) 추가")


async def _backfill_game_fields() -> None:
    defaults = {f"game.{mode}.streak": 0 for mode in GAME_MODES}
    for mode in RANK_MODES:
        defaults[f"game.{mode}.division"] = 0
        defaults[f"game.{mode}.lp"] = 0
    filled = 0
    for path, value in defaults.items():
        result = await db.user.update_many({path: {"$exists": False}}, {"$set": {path: value}})
        filled += result.modified_count
    print(f"user: 신규 게임 필드 {len(defaults)}종을 {filled}개 문서에 추가")


async def _reset_reward_alert() -> None:
    result = await db.user.update_many({"alerts.reward": True}, {"$set": {"alerts.reward": False}})
    print(f"user: {result.modified_count}개 문서의 포인트 알림 플래그를 초기화")


async def _migrate_winrate() -> None:
    fixed = 0
    for mode in GAME_MODES:
        path = f"game.{mode}.winrate"
        result = await db.user.update_many({path: {"$not": {"$type": "double"}}}, [{"$set": {path: {"$toDouble": f"${path}"}}}])
        fixed += result.modified_count
    print(f"user: winrate 필드 {fixed}개를 double로 변환")


async def _migrate_guild_invited() -> None:
    result = await db.guild.update_many(
        {"invited": None, "latest_usage": {"$ne": None}},
        [{"$set": {"invited": "$latest_usage"}}],
    )
    print(f"guild: {result.modified_count}개 문서의 invited를 latest_usage 값으로 채움")
    result = await db.guild.delete_many({"invited": None, "latest_usage": None})
    print(f"guild: 사용 기록이 없는 빈 문서 {result.deleted_count}개 삭제")


async def _backfill_user_latest_usage() -> None:
    result = await db.user.update_many(
        {"registered": {"$ne": None}, "latest_usage": None},
        [{"$set": {"latest_usage": "$registered"}}],
    )
    print(f"user: {result.modified_count}개 문서의 latest_usage를 registered 값으로 채움")


async def _drop_legacy_alert() -> None:
    result = await db.user.update_many({"alert": {"$exists": True}}, {"$unset": {"alert": ""}})
    print(f"user: 레거시 alert 필드를 {result.modified_count}개 문서에서 제거")


async def _migrate_announcements() -> None:
    if await db.announcement.estimated_document_count():
        print("announcement 컬렉션이 이미 존재하여 공지 이동을 건너뜁니다")
        return
    public = await db.public.find_one({"_id": "public"}, {"announcements": 1})
    items = (public or {}).get("announcements") or []
    if items:
        await db.announcement.insert_many([{"_id": item["time"], "title": item["title"], "value": item["value"]} for item in items])
    await db.public.update_one({"_id": "public"}, {"$unset": {"announcements": ""}})
    print(f"announcement: 공지 {len(items)}개를 별도 컬렉션으로 이동")


async def _drop_test_public() -> None:
    result = await db.public.delete_one({"_id": "test"})
    print(f"public: 레거시 'test' 문서 {result.deleted_count}개 삭제")


async def _drop_name_text_index() -> None:
    existing = await db.user.index_information()
    for name in [idx for idx, info in existing.items() if any(field == "_fts" for field, _ in info.get("key", []))]:
        await db.user.drop_index(name)
        print(f"user: 미사용 텍스트 인덱스 '{name}' 삭제")


async def _drop_legacy_collections() -> None:
    existing = await db.list_collection_names()
    for name in LEGACY_COLLECTIONS:
        if name in existing:
            await db.drop_collection(name)
            print(f"레거시 '{name}' 컬렉션 삭제")


async def main() -> None:
    await _migrate_floats()
    await _migrate_tiers()
    await _migrate_command_stats()
    await _migrate_reward()
    await _migrate_global_name()
    await _backfill_game_fields()
    await _migrate_winrate()
    await _reset_reward_alert()
    await _migrate_guild_invited()
    await _backfill_user_latest_usage()
    await _drop_legacy_alert()
    await _migrate_announcements()
    await _drop_test_public()
    await _drop_name_text_index()
    await _drop_legacy_collections()


if __name__ == "__main__":
    target_db = "테스트" if config.is_test else "메인(운영)"
    answer = input(f"'{dbconfig.db}' [{target_db}] DB에 마이그레이션을 실행합니다. 계속하려면 'y'를 입력하세요: ")
    if answer.strip().lower() == "y":
        asyncio.run(main())
    else:
        print("취소되었습니다.")
