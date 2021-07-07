import asyncio
import os
import sys
import warnings

from tools.db import db


async def mode1():
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


def mode2():
    os.mkdir("logs")
    os.mkdir("backup")


if __name__ == "__main__":
    mode = ""
    if len(sys.argv) == 2:
        mode = sys.argv[1]
    while True:
        if mode:
            mode = input("""
  끝봇 설정
============
1. DB 업데이트
2. 디렉토리 세팅
============
>>> """)
        if mode == "1":
            asyncio.get_event_loop().run_until_complete(mode1())
            sys.exit()
        elif mode == "2":
            mode2()
            sys.exit()
        else:
            warnings.warn("잘못된 모드입니다. 다시 선택해 주세요.")
