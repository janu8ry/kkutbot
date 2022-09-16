import json
import os
from typing import Any, List
from dataclasses import dataclass

import yaml

__all__ = ["get_nested_dict", "config"]

with open("config.yml", encoding="utf-8") as f:
    config_data = yaml.safe_load(f)

for file in os.listdir("static"):
    if file not in ("wordlist.json", "transition.json", "quests.json"):
        with open(f"static/{file}", "r", encoding="utf-8") as f:
            config_data[file[:-5]] = json.load(f)


def get_nested_dict(data: dict[str, Any], path: List[str]) -> Any:
    """
    gets value in nested dictionary.
    Parameters
    ----------
    data : dict
        Target dictionary to get value
    path : list[str]
        list of keys to get value
    Returns
    -------
    Any
        value in targeted dictionary
    """
    for i in path:
        data = data.get(i, None)
    return data


def _config(query: str) -> Any:
    if not query:
        return config_data
    else:
        return get_nested_dict(config_data, query.split("."))


@dataclass(frozen=True)
class Prefix:
    main: str = _config("prefix.main")
    test: str = _config("prefix.test")


@dataclass(frozen=True)
class Token:
    main: str = _config("token.main")
    test: str = _config("token.test")
    koreanbots: str = _config("token.koreanbots")
    dbl: str = _config("token.dbl")


@dataclass(frozen=True)
class Color:
    general: int = 0x4374D9
    error: int = 0xCC3D3D
    help: int = 0x47C83E


@dataclass(frozen=True)
class MainDBData:
    ip: str = _config("mongo.main.ip")
    port: int = _config("mongo.main.port")
    db: str = _config("mongo.main.db")
    user: str = _config("mongo.main.user")
    password: str = _config("mongo.main.password")


@dataclass(frozen=True)
class TestDBData:
    ip: str = _config("mongo.test.ip")
    port: int = _config("mongo.test.port")
    db: str = _config("mongo.test.db")
    user: str = _config("mongo.test.user")
    password: str = _config("mongo.test.password")


@dataclass(frozen=True)
class Mongo:
    main: MainDBData = MainDBData()
    test: TestDBData = TestDBData()


@dataclass(frozen=True)
class Channels:
    backup_data: int = 838371534690844672
    backup_log: int = 987017719545229463
    error_log: int = 1016347873253793832


@dataclass(frozen=True)
class InviteLink:
    bot: str = _config("links.invite.bot")
    server: str = _config("links.invite.server")


@dataclass(frozen=True)
class Links:
    invite: InviteLink = InviteLink()
    privacy_policy: str = _config("links.privacy-policy")
    terms_of_service: str = _config("links.terms-of-service")
    koreanbots: str = _config("links.koreanbots")
    dbl: str = _config("links.dbl")
    github: str = _config("links.github")
    website: str = _config("links.website")


@dataclass(frozen=True)
class Config:
    is_test: bool = _config("testmode")
    prefix: Prefix = Prefix()
    token: Token = Token()
    colors: Color = Color()
    admin: list[int] = _config("admin")
    mongo: Mongo = Mongo()
    channels: Channels = Channels()
    links: Links = Links()
    default_data: dict[str, dict[str, Any]] = _config("default_data")
    emojis: dict[str, int] = _config("emojis")
    modelist: dict[str, str] = _config("modelist")
    perms: dict[str, str] = _config("perms")
    tierlist: dict[str, dict[str, Any]] = _config("tierlist")


config: Config = Config()
