import asyncio
import time
from typing import Union
from typing_extensions import TypeAlias

import discord
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection  # noqa

from config import MainDBData, TestDBData, config, get_nested_dict  # noqa

TargetObject: TypeAlias = Union[discord.User, discord.Member, discord.ClientUser, discord.Guild, None, int, str]


dbconfig: Union[MainDBData, TestDBData] = getattr(config.mongo, "test" if config.is_test else "main")
db_options = {}

if all([username := dbconfig.user, password := dbconfig.password]):
    db_options["username"] = username
    db_options["password"] = password
    db_options["authSource"] = "admin"

_client = AsyncIOMotorClient(
    host=dbconfig.ip, port=dbconfig.port, **db_options
)

db = _client[dbconfig.db]


async def main() -> None:
    await db.user.update_many({}, {
        "$rename": {
            "info": "bio"
        },
        "$unset": {
            "banned": 1,
            "last_command": 1,
            "last_reward": 1,
            "mails": 1,
            "alerts.mails": 1
        }
    })
    for user in await (db.user.find()).to_list(None):
        if isinstance(user["latest_usage"], float):
            ts = round(user["latest_usage"])
            db_set = {
                "latest_usage": ts
            }
            await db.user.update_one({"_id": user["_id"]}, {"$set": db_set})

    await db.unused.update_many({}, {
        "$rename": {
            "info": "bio"
        },
        "$unset": {
            "banned": 1,
            "last_command": 1,
            "last_reward": 1,
            "mails": 1,
            "alerts.mails": 1
        }
    })
    for unused in await (db.unused.find()).to_list(None):
        if isinstance(unused["latest_usage"], float):
            ts = round(unused["latest_usage"])
            db_set = {
                "latest_usage": ts
            }
            await db.unused.update_one({"_id": unused["_id"]}, {"$set": db_set})

    for unused in await (db.unused.find()).to_list(None):
        await db.user.insert_one(unused)
        await db.unused.delete_one({"_id": unused["_id"]})

    for guild in await (db.guild.find()).to_list(None):
        db_set = {}
        update = False
        if isinstance(guild["latest_usage"], float):
            ts = round(guild["latest_usage"])
            db_set["latest_usage"] = ts
            update = True
        if isinstance(guild["invited"], float):
            ts = round(guild["invited"])
            db_set["invited"] = ts
            update = True
        if update:
            await db.guild.update_one({"_id": guild["_id"]}, {"$set": db_set})

    public = await db.general.find_one({"_id": "general"})
    public["_id"] = "public"
    await db.public.insert_one(public)
    await db.public.insert_one({"_id": "test", "latest": time.time()})
    await db.general.drop()


asyncio.get_event_loop().run_until_complete(main())
