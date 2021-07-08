from dataclasses import dataclass, field
from datetime import datetime

__all__ = ("UserModel", "GuildModel", "GeneralModel")


@dataclass
class UserQuestStatusModel:
    date: int = 0
    completed: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UserQuestModel:
    status: UserQuestStatusModel = UserQuestStatusModel()
    cache: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            status=UserQuestStatusModel.from_dict(data=data.get("status")),
            cache=data.get("cache"),
        )


@dataclass
class BaseGameModel:
    times: int = 0
    win: int = 0
    best: int = 0
    winrate: int = 0

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class BaseRankGameModel(BaseGameModel):
    tier: str = "언랭크"


@dataclass
class SoloRankGameModel(BaseRankGameModel):
    pass


@dataclass
class OnlineRankGameModel(BaseRankGameModel):
    pass


@dataclass
class KkdGameModel(BaseGameModel):
    pass


@dataclass
class GuildGameModel(BaseGameModel):
    pass


@dataclass
class MultiOnlineGameModel(BaseGameModel):
    pass


@dataclass
class ApmalGameModel(BaseGameModel):
    pass


@dataclass
class UserGameStatusModel:
    rank_solo: SoloRankGameModel = SoloRankGameModel()
    rank_online: OnlineRankGameModel = OnlineRankGameModel()
    kkd: KkdGameModel = KkdGameModel()
    guild_multi: GuildGameModel = GuildGameModel()
    online_multi: MultiOnlineGameModel = MultiOnlineGameModel()
    apmal: ApmalGameModel = ApmalGameModel()

    @classmethod
    def from_dict(cls, data):
        return cls(
            rank_solo=SoloRankGameModel.from_dict(data.get("rank_solo")),
            rank_online=OnlineRankGameModel.from_dict(data.get("rank_online")),
            kkd=KkdGameModel.from_dict(data.get("kkd")),
            guild_multi=GuildGameModel.from_dict(data.get("guild_multi")),
            online_multi=MultiOnlineGameModel.from_dict(data.get("online_multi")),
            apmal=ApmalGameModel.from_dict(data.get("apmal")),
        )


@dataclass
class AlertModel:
    daily: bool = False
    heart: bool = False
    mail: bool = True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UserModel:
    id: int = None
    name: str = None
    registered: datetime = None
    info: str = "소개말이 없습니다."
    points: int = 1000
    medals: int = 0
    latest_reward: int = 0
    attendance: list = field(default_factory=list)
    quest: UserQuestModel = UserQuestModel()
    game: UserGameStatusModel = UserGameStatusModel()
    attendance_times: int = 0
    command_used: int = 0
    banned: bool = False
    latest_usage: int = None
    mails: list = field(default_factory=list)
    alerts: AlertModel = AlertModel()

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("_id"),
            name=data.get("name"),
            registered=data.get("registered"),
            info=data.get("info"),
            points=data.get("points"),
            medals=data.get("medals"),
            latest_reward=data.get("latest_reward"),
            attendance=data.get("attendance"),
            quest=UserQuestModel.from_dict(data.get("quest")),
            game=UserGameStatusModel.from_dict(data.get("game")),
            attendance_times=data.get("attendance_times"),
            command_used=data.get("command_used"),
            banned=data.get("banned"),
            latest_usage=data.get("latest_usage"),
            mails=data.get("mails"),
            alerts=AlertModel.from_dict(data.get("alerts")),
        )


@dataclass
class GuildModel:
    id: int = None
    invited: int = None
    latest_usage: int = None
    command_used: int = 0


@dataclass
class GeneralModel:
    id: str = "general"
    attendance: int = 0
    command_used: int = 0
    latest_command = None
    commands: dict = field(default_factory=dict)
    quests: dict = field(default_factory=dict)
