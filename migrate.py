import asyncio

from ext.db import db


async def main():
    await db.user.update_many({}, {
        "$set": {"last_vote": 0},
        "$unset": {"start_point": 1}
    })
    await db.unused.update_many({}, {
        "$set": {"last_vote": 0},
        "$unset": {"start_point": 1}
    })

asyncio.get_event_loop().run_until_complete(main())
