from typing import Any, Optional

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel, Field

__all__ = ["User", "Guild", "Public"]


attendance = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "times": 0}


class QuestStatus(BaseModel):
    date: int = 0
    completed: list[str] = Field(default_factory=list)


class Quest(BaseModel):
    status: QuestStatus = Field(default_factory=QuestStatus)
    cache: dict[str, int] = Field(default_factory=dict)
    total: int = 0


class GameBase(BaseModel):
    times: int = 0
    win: int = 0
    best: int = 0
    winrate: float = 0.0


class RankGameBase(GameBase):
    tier: str = "언랭크"


class SoloRankGame(RankGameBase):
    pass


class OnlineRankGame(RankGameBase):
    pass


class LongGame(GameBase):
    pass


class KkdGame(GameBase):
    pass


class GuildMultiGame(GameBase):
    pass


class OnlineMultiGame(GameBase):
    pass


class Game(BaseModel):
    rank_solo: SoloRankGame = Field(default_factory=SoloRankGame)
    rank_online: OnlineRankGame = Field(default_factory=OnlineRankGame)
    long: LongGame = Field(default_factory=LongGame)
    kkd: KkdGame = Field(default_factory=KkdGame)
    guild_multi: GuildMultiGame = Field(default_factory=GuildMultiGame)
    online_multi: OnlineMultiGame = Field(default_factory=OnlineMultiGame)


class Alerts(BaseModel):
    attendance: bool = False
    reward: bool = False
    announcements: bool = True


class User(Document):
    id: int  # type: ignore
    name: str
    registered: Optional[int] = None
    bio: str = "소개말이 없습니다."
    points: Indexed(int, pymongo.DESCENDING) = 1000  # type: ignore
    medals: int = 0
    latest_reward: Optional[int] = None
    attendance: dict[str, int] = Field(default_factory=attendance.copy)
    quest: Quest = Field(default_factory=Quest)
    game: Game = Field(default_factory=Game)
    command_used: int = 0
    latest_usage: Optional[int] = None
    alerts: Alerts = Field(default_factory=Alerts)

    class Settings:
        name = "user"
        use_state_management = True
        state_management_replace_objects = True
        validate_on_save = True


class Guild(Document):
    id: int  # type: ignore
    invited: Optional[int] = None
    latest_usage: Optional[int] = None
    command_used: Indexed(int, pymongo.DESCENDING) = 0  # type: ignore

    class Settings:
        name = "guild"
        use_state_management = True
        state_management_replace_objects = True
        validate_on_save = True


class Public(Document):
    id: str  # type: ignore
    attendance: int = 0
    reward: int = 0
    command_used: int = 0
    latest_usage: Optional[int] = None
    commands: dict[str, int] = Field(default_factory=dict)
    quests: dict[str, dict[str, Any]] = Field(default_factory=dict)
    announcements: list[dict[str, Any]] = Field(default_factory=list)

    class Settings:
        name = "public"
        use_state_management = True
        state_management_replace_objects = True
        validate_on_save = True
