import asyncio

from tools.db import db


async def main() -> None:
    await db.user.update_many({}, {
        "$rename": {
            "info": "bio"
        }
    })
    for user in await (db.user.find()).to_list(None):
        ts = round(user["latest_usage"])
        db_set = {
            "latest_usage": ts
        }
        await db.user.update_one({"_id": user["_id"]}, {"$set": db_set})

    await db.unused.update_many({}, {
        "$rename": {
            "info": "bio"
        }
    })
    for unused in await (db.unused.find()).to_list(None):
        ts = round(unused["latest_usage"])
        db_set = {
            "latest_usage": ts
        }
        await db.unused.update_one({"_id": unused["_id"]}, {"$set": db_set})

    for guild in await (db.guild.find()).to_list(None):
        ts = round(guild["latest_usage"])
        db_set = {
            "latest_usage": ts
        }
        await db.guild.update_one({"_id": guild["_id"]}, {"$set": db_set})


asyncio.get_event_loop().run_until_complete(main())
