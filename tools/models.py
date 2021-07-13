import asyncio
import inspect
from dataclasses import dataclass
from datetime import datetime

from .db import write

__all__ = ("UserModel", "GuildModel", "GeneralModel")


@dataclass
class BaseModel:
    _id: int
    _col: str

    def __setattr__(self, key, value):
        if not inspect.stack()[1].function == "__init__":
            asyncio.get_event_loop().create_task(
                write(self._id, self._col, self._path + key, value)  # noqa
            )
        super().__setattr__(key, value)

    @classmethod
    def from_path(cls, path: str):
        data = cls
        for i in path.split("."):
            data = getattr(data, i)
        return data


@dataclass
class UserQuestStatusModel(BaseModel):
    date: int
    completed: list
    _path: str = "quest.status."


@dataclass
class UserQuestModel(BaseModel):
    status: UserQuestStatusModel
    cache: dict
    _path: str = "quest."


@dataclass
class BaseGameModel(BaseModel):
    times: int
    win: int
    best: int
    winrate: int


@dataclass
class BaseRankGameModel(BaseGameModel):
    tier: str


@dataclass
class SoloRankGameModel(BaseRankGameModel):
    _path: str = "game.rank_solo."


@dataclass
class OnlineRankGameModel(BaseRankGameModel):
    _path: str = "game.rank_online."


@dataclass
class KkdGameModel(BaseGameModel):
    _path: str = "game.kkd."


@dataclass
class GuildGameModel(BaseGameModel):
    _path: str = "game.guild_multi."


@dataclass
class MultiOnlineGameModel(BaseGameModel):
    _path: str = "game.online_multi."


@dataclass
class ApmalGameModel(BaseGameModel):
    _path: str = "game.apmal."


@dataclass
class UserGameStatusModel(BaseModel):
    rank_solo: SoloRankGameModel
    rank_online: OnlineRankGameModel
    kkd: KkdGameModel
    guild_multi: GuildGameModel
    online_multi: MultiOnlineGameModel
    apmal: ApmalGameModel
    _path: str = "game."


@dataclass
class AlertModel(BaseModel):
    reward: int
    mail: int
    _path: str = "alerts."


@dataclass
class UserModel(BaseModel):
    _id: int
    name: str
    registered: datetime
    info: str
    points: int
    medals: int
    latest_reward: int
    quest: UserQuestModel
    game: UserGameStatusModel
    reward_times: int
    command_used: int
    banned: bool
    latest_usage: float
    mails: list
    alerts: AlertModel


@dataclass
class GuildModel(BaseModel):
    _id: int
    invited: int
    latest_usage: float
    command_used: int


@dataclass
class GeneralModel(BaseModel):
    _id: str
    attendance: int
    command_used: int
    latest_command: float
    commands: dict
    quests: dict
