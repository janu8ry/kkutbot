import asyncio
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from config import Mongo, config  # noqa

dbconfig: Mongo = config.mongo
db_options: dict[str, Any] = {}

if all([username := dbconfig.username, password := dbconfig.password]):
    db_options["username"] = username
    db_options["password"] = password
    db_options["authSource"] = "admin"

_client = AsyncIOMotorClient(host=dbconfig.host, port=dbconfig.port, **db_options)
db = _client[dbconfig.db]


async def remove_public_reward() -> None:
    result = await db["public"].update_many({"reward": {"$exists": True}}, {"$unset": {"reward": ""}})
    print(f"public.reward 필드 제거: {result.modified_count}개 문서")


async def main() -> None:
    await remove_public_reward()


if __name__ == "__main__":
    target_db = "테스트" if config.is_test else "메인(운영)"
    answer = input(f"'{dbconfig.db}' [{target_db}] DB에 마이그레이션을 실행합니다. 계속하려면 'y'를 입력하세요: ")
    if answer.strip().lower() == "y":
        asyncio.run(main())
    else:
        print("취소되었습니다.")
