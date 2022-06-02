from tools.db import db


async def main():
    await db.user.update_many({}, {
        "$rename": {
            "_name": "name",
            "register_date": "registered",
            "info_word": "info",
            "last_vote": "latest_reward",
            "daily_times": "attendance",
            "last_command": "latest_usage",
            "mail": "mails",
            "alert.daily": "alert.attendance",
            "alert.mail": "alert.mails",
            "alert": "alerts",
            "game.rank_multi": "game.rank_online",
            "game.apmal": "game.long"
        },
        "$unset": {
            "alerts.start_point": 1
        }
    })

    await db.unused.update_many({}, {
        "$rename": {
            "_name": "name",
            "register_date": "registered",
            "info_word": "info",
            "last_vote": "latest_reward",
            "daily_times": "attendance",
            "last_command": "latest_usage",
            "mail": "mails",
            "alert.daily": "alert.attendance",
            "alert.mail": "alert.mails",
            "alert": "alerts",
            "game.rank_multi": "game.rank_online",
            "game.apmal": "game.long"
        },
        "$unset": {
            "alerts.start_point": 1
        }
    })
