import json
import os
from typing import Any
from dataclasses import dataclass, field

import yaml

__all__ = ["get_nested_dict", "get_nested_property", "config"]

with open("config.yml", encoding="utf-8") as f:
    config_data = yaml.safe_load(f)

for file in os.listdir("static"):
    if file not in ("wordlist.json", "transition.json", "quests.json"):
        with open(f"static/{file}", "r", encoding="utf-8") as f:
            config_data[file[:-5]] = json.load(f)


def get_nested_dict(data: dict[str, Any], path: list[str]) -> Any:
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


def get_nested_property(data: Any, path: list[str]) -> Any:
    """
    gets property in nested dataclass.
    Parameters
    ----------
    data : Any
        Target dataclass to get value
    path : list[str]
        list of properties to get value
    Returns
    -------
    Any
        value in targeted dataclass
    """
    for i in path:
        data = getattr(data, i)
    return data


def _config(query: str) -> Any:
    if not query:
        return config_data
    else:
        return get_nested_dict(config_data, query.split("."))


@dataclass(frozen=True)
class Prefix:
    main: str = field(default_factory=lambda: _config("prefix.main"))
    test: str = field(default_factory=lambda: _config("prefix.test"))


@dataclass(frozen=True)
class Token:
    main: str = field(default_factory=lambda: _config("token.main"))
    test: str = field(default_factory=lambda: _config("token.test"))
    koreanbots: str = field(default_factory=lambda: _config("token.koreanbots"))
    dbl: str = field(default_factory=lambda: _config("token.dbl"))


@dataclass(frozen=True)
class Color:
    general: int = 0x4374D9
    error: int = 0xCC3D3D
    help: int = 0x47C83E


@dataclass(frozen=True)
class MainDBData:
    ip: str = field(default_factory=lambda: _config("mongo.main.ip"))
    port: int = field(default_factory=lambda: _config("mongo.main.port"))
    db: str = field(default_factory=lambda: _config("mongo.main.db"))
    user: str = field(default_factory=lambda: _config("mongo.main.user"))
    password: str = field(default_factory=lambda: _config("mongo.main.password"))


@dataclass(frozen=True)
class TestDBData:
    ip: str = field(default_factory=lambda: _config("mongo.test.ip"))
    port: int = field(default_factory=lambda: _config("mongo.test.port"))
    db: str = field(default_factory=lambda: _config("mongo.test.db"))
    user: str = field(default_factory=lambda: _config("mongo.test.user"))
    password: str = field(default_factory=lambda: _config("mongo.test.password"))


@dataclass(frozen=True)
class Mongo:
    main: MainDBData = MainDBData()
    test: TestDBData = TestDBData()


@dataclass(frozen=True)
class Channels:
    backup_data: int = field(default_factory=lambda: _config("channels.backup_data"))
    backup_log: int = field(default_factory=lambda: _config("channels.backup_log"))
    error_log: int = field(default_factory=lambda: _config("channels.error_log"))


@dataclass(frozen=True)
class InviteLink:
    bot: str = field(default_factory=lambda: _config("links.invite.bot"))
    server: str = field(default_factory=lambda: _config("links.invite.server"))


@dataclass(frozen=True)
class Links:
    invite: InviteLink = InviteLink()
    privacy_policy: str = field(default_factory=lambda: _config("links.privacy-policy"))
    terms_of_service: str = field(default_factory=lambda: _config("links.terms-of-service"))
    koreanbots: str = field(default_factory=lambda: _config("links.koreanbots"))
    dbl: str = field(default_factory=lambda: _config("links.dbl"))
    github: str = field(default_factory=lambda: _config("links.github"))
    website: str = field(default_factory=lambda: _config("links.website"))


@dataclass(frozen=True)
class Config:
    is_test: bool = field(default_factory=lambda: _config("testmode"))
    prefix: Prefix = Prefix()
    token: Token = Token()
    colors: Color = Color()
    admin: list[int] = field(default_factory=lambda: _config("admin"))
    mongo: Mongo = Mongo()
    channels: Channels = Channels()
    links: Links = Links()
    default_data: dict[str, dict[str, Any]] = field(default_factory=lambda: _config("default_data"))
    emojis: dict[str, int] = field(default_factory=lambda: _config("emojis"))
    modelist: dict[str, str] = field(default_factory=lambda: _config("modelist"))
    perms: dict[str, str] = field(default_factory=lambda: _config("perms"))
    tierlist: dict[str, dict[str, Any]] = field(default_factory=lambda: _config("tierlist"))


config: Config = Config()
