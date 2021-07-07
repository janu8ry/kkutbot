import asyncio

from tools.db import db


async def main():
    await db.user.update_many({}, {
        "$rename": {
            "_name": "name",
            "register_date": "registered",
            "info_word": "info",
            "last_reward": "latest_reward",
            "daily_times": "attendance_times",
            "last_command": "latest_usage",
            "mail": "mails",
            "alert": "alerts"
        },
        "$set": {
            "attendance": []
        },
        "$unset": {
            "daily": 1
        }
    })

    await db.unused.update_many({}, {
        "$rename": {
            "_name": "name",
            "register_date": "registered",
            "info_word": "info",
            "last_reward": "latest_reward",
            "daily_times": "attendance_times",
            "last_command": "latest_usage",
            "mail": "mails",
            "alert": "alerts",
            "game.rank_multi": "game.rank_online"
        },
        "$set": {
            "attendance": []
        },
        "$unset": {
            "daily": 1
        }
    })

    await db.guild.update_many({}, {
        "$rename": {
            "last_usage": "latest_usage"
        }
    })

    await db.general.update_one({"_id": "general"}, {
        "$rename": {
            "daily": "attendance",
            "last_usage": "latest_usage",
            "quest": "quests"
        }
    })

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
