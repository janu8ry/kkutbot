import asyncio

from tools.db import db
from tools.utils import get_timestamp

announcements = [
    {
        "title": "끝봇 1.0 출시",
        "value": """```cs
'끝말잇기 멀티플레이' 추가
'유저 차단'(봇 관리자 전용) 추가
'공지 채널 설정'(서버 관리자 전용) 추가
'핑' 명령어 리뉴얼
'위키 기능 삭제'
'도움' 명령어 리뉴얼
'가입' 명령어 삭제 (명령어 입력하면 자동 가입)
'끝말잇기' UI 조금 수정
'두음법칙' 버그 수정
기타 여러 '버그 수정'
'코드 최적화'
```
끝봇이 드디어 베타에서 정식 버전으로 업데이트 되었습니다!
많은 관심 부탁드립니다!""",
        "time": get_timestamp("2020-07-30")
    }, {
        "title": "끝봇 1.1 업데이트",
        "value": """```cs
끝말잇기에서 '--' 제거
'티어' 명령어 추가
끝말잇기 멀티플레이 'ui 개선'
소개말 수정
랭킹에 '차단', '스탭'인 유저 안보이도록 변경
'지원금' 명령어 추가
명령어들의 '다른 이름' 추가
'최적화'
끝말잇기 '단어리스트' 에 단어 추가
'몇몇 버그 수정'
```
모바일에서 끝말잇기를 즐기기 힘들게 하고, 초보자분들에게 진입장벽이 되는
``--`` 를 사용하지 않아도 끝말잇기를 플레이할 수 있게 개선했습니다.
많은 사용 부탁드립니다!""",
        "time": get_timestamp("2020-09-15")
    }, {
        "title": "끝봇 1.2 업데이트",
        "value": """```cs
여러 명령어 '버그 수정'
명령어 처리 속도 향상
'카테고리 세분화'
명령어 '안정성' 증가
'버전' 명령어를 '정보' 명령어에 통합
'출석', '지원금' 보상 조정

<끝말잇기>
-멀티플레이 모드 삭제
-쿵쿵따 모드 추가
-버그 대폭 개선
```""",
        "time": get_timestamp("2020-10-30")
    }, {
        "title": "끝봇 1.3 업데이트",
        "value": """```cs
'출석' 명령어 리뉴얼
 - '주간 출석': 일주일동안 매일 출석하고 추가 보상을 획득하세요!

사용 가능한 신규 접두사 'ㄲ' 추가
출석/지원금 '알림' 추가

'티어' 기준 상향
'두음법칙' 버그 수정
'공지' 관련 버그 수정
```
""",
        "time": get_timestamp("2020-12-09")
    }, {
        "title": "끝봇 1.4 업데이트",
        "value": """```cs
끝말잇기 '난이도 조정'
 - 첫 회차에 한방단어가 안나오도록 수정

'메일' 명령어 추가
- 읽지 않은 '전체공지', '알림' 등을 확인해 보세요

끝말잇기 모드 선택시 '취소 버튼' 추가
'끝말잇기 쿵쿵따' 모드 '보상', '난이도' 조정
'채널 공지' 삭제
```""",
        "time": get_timestamp("2020-12-22")
    }, {
        "title": "끝봇 1.5 업데이트",
        "value": """```cs
'서버원들과 함께하는 다인전' 추가
 - 서버원들과 함께 끝말잇기를 즐겨보세요!

첫번째 차례에서 '한방단어' 사용 불가하도록 패치
'끝말잇기' 도배성 개선

'단어 리스트' 개편
'다른 서버'의 끝봇 유저 '프로필' 확인 가능하도록 패치
```""",
        "time": get_timestamp("2020-12-30")
    }, {
        "title": "끝봇 1.6 업데이트",
        "value": """```cs
'끝말잇기 리뉴얼'
 - 레이아웃 변경, 통계 세분화
 - 'ㄲㄲ <번호>' 로 한번에 모드 선택 가능

'랭킹 업데이트'
 - 이름이 긴 유저는 닉네임이 잘려서 표시됩니다.
 - 끝말잇기 상세 랭킹 추가

'정책 변경'
 - 오랫동안 끝봇을 사용하지 않을 경우 프로필이 숨김처리 되어 랭킹에 나오지 않으며, 프로필도 조회할 수 없게 됩니다. 숨김처리 된지 한달 이내에 명령어를 다시 사용한 경우 원상복구 되며, 그렇지 않을 경우 데이터가 영구 삭제됩니다. 

'버그 수정'
 - 모바일 ui 깨짐현상 개선
 - 랭킹 집계 속도 감소
 - DM 오류 수정

'티어 명령어 삭제'
 - 이제 티어 정보는 공식 홈페이지 (kkutbot.github.io)에서 확인 가능합니다.
```""",
        "time": get_timestamp("2021-03-04")
    }, {
        "title": "끝봇 1.7 업데이트",
        "value": """```cs
'퀘스트' 명령어 추가
 - 매일 퀘스트를 완료하고 포인트, 메달 등의 보상을 확득하세요!

'티어 변경' 알림
 - 끝말잇기 게임 종료시, 티어가 '승급' / '강등'되었다면 알림 메시지가 나옵니다!

끝말잇기 '포기' 기능 추가
 - 이제 끝말잇기 게임 도중에 "ㅈㅈ" 또는 "GG"를 입력하면 게임을 포기할 수 있습니다!

'명령어 별칭' 다수 추가
 - 이제 명령어의 '초성'만 입력해도 명령어를 사용할 수 있습니다!
   예) ㄲ출석 -> ㄲㅊㅅ, ㄲ도움 -> ㄲㄷㅇ

끝말잇기 '힌트' 기능 추가
 - 끝말잇기 게임에서 패배시, 제시할 수 있었던 단어 '최대 3개'를 힌트로 보여줍니다!

'출석' 명령어 개선
 - 이미 출석을 했어도 명령어 입력시 자신의 '주간 출석 현황'을 확인할 수 있습니다!

명령어 '응답 속도' 개선
 - 최근 급격한 유저 수 증가로 인해 심해졌던 렉을 개선했습니다.
```""",
        "time": get_timestamp("2021-05-11")
    }
]


async def main():
    await db.user.update_many({}, {
        "$rename": {
            "alert": "alerts",
            "daily": "attendance",
            "mail": "mails",
        }
    })
    await db.user.update_many({}, {  # noqa
        "$rename": {
            "_name": "name",
            "register_date": "registered",
            "info_word": "info",
            "last_vote": "latest_reward",
            "daily_times": "attendance_times",
            "last_command": "latest_usage",
            "alerts.daily": "alerts.attendance",
            "alerts.heart": "alerts.reward",
            "alerts.mail": "alerts.mails",
            "game.rank_multi": "game.rank_online",
            "game.apmal": "game.long"
        },
        "$set": {
            "attendance": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0},
            "alerts.announcements": True,
            "banned": {"isbanned": False, "since": 0, "period": 0, "reason": None},
            "mails": {}
        },
        "$unset": {
            "alerts.start_point": 1
        }
    })
    for user in await (db.user.find()).to_list(None):
        t = {"alerts.reward": False, "registered": round(user["registered"].timestamp())}
        await db.user.update_one({"_id": user["_id"]}, {"$set": t})

    await db.unused.update_many({}, {
        "$rename": {
            "alert": "alerts",
            "daily": "attendance",
            "mail": "mails"
        }
    })
    await db.unused.update_many({}, {  # noqa
        "$rename": {
            "_name": "name",
            "register_date": "registered",
            "info_word": "info",
            "last_vote": "latest_reward",
            "daily_times": "attendance_times",
            "last_command": "latest_usage",
            "alerts.daily": "alerts.attendance",
            "alerts.heart": "alerts.reward",
            "alerts.mail": "alerts.mails",
            "game.rank_multi": "game.rank_online",
            "game.apmal": "game.long"
        },
        "$set": {
            "attendance": {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0},
            "alerts.announcements": True,
            "banned": {"isbanned": False, "since": 0, "period": 0, "reason": None},
            "mails": {}
        },
        "$unset": {
            "alerts.start_point": 1
        }
    })
    for user in await (db.unused.find()).to_list(None):
        t = {"alerts.reward": False, "registered": round(user["registered"].timestamp())}
        await db.user.update_one({"_id": user["_id"]}, {"$set": t})

    await db.guild.update_many({}, {
        "$rename": {
            "last_command": "latest_usage"
        }
    })
    for guild in await (db.guild.find()).to_list(None):
        t = {}
        if "invited" in guild:
            if isinstance(guild["invited"], str):
                t["invited"] = get_timestamp(guild["invited"][:10])
            else:
                t["invited"] = round(guild["invited"].timestamp())
        else:
            t["invited"] = None
        if "latest_usage" not in guild:
            t["latest_usage"] = None
        if "command_used" not in guild:
            t["command_used"] = 0
        await db.guild.update_one({"_id": guild["_id"]}, {"$set": t})

    await db.general.update_one({"_id": "general"}, {
        "$rename": {
            "daily": "attendance",
            "last_command": "latest_usage",
            "quest": "quests"
        },
        "$set": {
            "reward": 0,
            "announcements": announcements
        }
    })


asyncio.get_event_loop().run_until_complete(main())
