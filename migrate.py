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


async def main() -> None:
    print("실행할 마이그레이션 작업이 없습니다.")


if __name__ == "__main__":
    target_db = "테스트" if config.is_test else "메인(운영)"
    answer = input(f"'{dbconfig.db}' [{target_db}] DB에 마이그레이션을 실행합니다. 계속하려면 'y'를 입력하세요: ")
    if answer.strip().lower() == "y":
        asyncio.run(main())
    else:
        print("취소되었습니다.")
