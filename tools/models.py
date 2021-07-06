from dataclasses import dataclass


@dataclass
class UserQuestStatusModel:
    date: int
    completed: list

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UserQuestModel:
    status: UserQuestStatusModel
    cache: dict

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            status=UserQuestStatusModel.from_dict(data=data.get('status')),
            cache=data.get('cache')
            )


@dataclass
class BaseGameModel:
    times: int
    win: int
    best: int
    winrate: int

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class BaseRankGameModel(BaseGameModel):
    tier: str


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
    rank_solo: SoloRankGameModel
    rank_online: OnlineRankGameModel
    kkd: KkdGameModel
    guild_multi: GuildGameModel
    online_multi: MultiOnlineGameModel
    apmal: ApmalGameModel

    @classmethod
    def from_dict(cls, data):
        return cls(
            rank_solo=SoloRankGameModel.from_dict(data.get('rank_solo')),
            rank_online=OnlineRankGameModel.from_dict(data.get('rank_online')),
            kkd=KkdGameModel.from_dict(data.get('kkd')),
            guild_multi=GuildGameModel.from_dict(data.get('guild_multi')),
            online_multi=MultiOnlineGameModel.from_dict(data.get('online_multi')),
            apmal=ApmalGameModel.from_dict(data.get('apmal'))
        )


@dataclass
class AlertModel:
    daily: bool
    heart: bool
    mail: bool

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UserModel:
    id: int
    name: str
    registered: int
    info: str
    points: int
    medals: int
    latest_reward: int
    attendance: list
    quest: UserQuestModel
    game: UserGameStatusModel
    attendance_times: int
    command_used: int
    banned: bool
    latest_usage: int
    mails: list
    alerts: AlertModel

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('_id'),
            name=data.get('name'),
            registered=data.get('registered'),
            info=data.get('info'),
            points=data.get('points'),
            medals=data.get('medals'),
            latest_reward=data.get('latest_reward'),
            attendance=data.get('attendance'),
            quest=UserQuestModel.from_dict(data.get('quest')),
            game=UserGameStatusModel.from_dict(data.get('game')),
            attendance_times=data.get('attendance_times'),
            command_used=data.get('command_used'),
            banned=data.get('banned'),
            latest_usage=data.get('latest_usage'),
            mails=data.get('mails'),
            alerts=AlertModel.from_dict(data.get('alerts'))
        )



