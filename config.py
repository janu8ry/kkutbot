import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv

__all__ = ["get_nested_dict", "get_nested_property", "config"]


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\$\{([^}]+)\}", lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    return value


load_dotenv()

with open("config.yml", encoding="utf-8") as f:
    config_data = _expand_env(yaml.safe_load(f))

for file in os.listdir("static"):
    if file not in ("wordlist.json", "transition.json", "quests.json"):
        with open(f"static/{file}", "r", encoding="utf-8") as f:
            config_data[file[:-5]] = json.load(f)


def get_nested_dict(data: dict[str, Any], path: list[str]) -> Any:
    """
    Gets a value from a nested dictionary.
    Parameters
    ----------
    data : dict[str, Any]
        Target dictionary to get the value from
    path : list[str]
        List of keys to retrieve the value
    Returns
    -------
    Any
        Value from the targeted dictionary
    """
    for i in path:
        data = data.get(i, None)
    return data


def get_nested_property(data: Any, path: list[str]) -> Any:
    """
    Gets a property from a nested dataclass.
    Parameters
    ----------
    data : Any
        Target dataclass to get the value from
    path : list[str]
        List of properties to retrieve the value
    Returns
    -------
    Any
        Value from the targeted dataclass
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
    general: int = field(default_factory=lambda: _config("colors.general"))
    error: int = field(default_factory=lambda: _config("colors.error"))
    help: int = field(default_factory=lambda: _config("colors.help"))


@dataclass(frozen=True)
class MainDBData:
    host: str = field(default_factory=lambda: _config("mongo.main.host"))
    port: int = field(default_factory=lambda: _config("mongo.main.port"))
    db: str = field(default_factory=lambda: _config("mongo.main.db"))
    username: str = field(default_factory=lambda: _config("mongo.main.username"))
    password: str = field(default_factory=lambda: _config("mongo.main.password"))


@dataclass(frozen=True)
class TestDBData:
    host: str = field(default_factory=lambda: _config("mongo.test.host"))
    port: int = field(default_factory=lambda: _config("mongo.test.port"))
    db: str = field(default_factory=lambda: _config("mongo.test.db"))
    username: str = field(default_factory=lambda: _config("mongo.test.username"))
    password: str = field(default_factory=lambda: _config("mongo.test.password"))


@dataclass(frozen=True)
class Scheduler:
    hour: str = field(default_factory=lambda: _config("mongo.scheduler.hour"))
    minute: str = field(default_factory=lambda: _config("mongo.scheduler.minute"))


@dataclass(frozen=True)
class Mongo:
    main: MainDBData = MainDBData()
    test: TestDBData = TestDBData()
    scheduler: Scheduler = Scheduler()


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
class Sentry:
    dsn: str = field(default_factory=lambda: _config("sentry.dsn"))
    url: str = field(default_factory=lambda: _config("sentry.url"))


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
    version: str = field(default_factory=lambda: _config("version"))
    bot_id: int = field(default_factory=lambda: _config("bot_id"))
    prefix: Prefix = Prefix()
    token: Token = Token()
    colors: Color = Color()
    admin: list[int] = field(default_factory=lambda: _config("admin"))
    mongo: Mongo = Mongo()
    channels: Channels = Channels()
    sentry: Sentry = Sentry()
    links: Links = Links()
    default_data: dict[str, dict[str, Any]] = field(default_factory=lambda: _config("default_data"))
    emojis: dict[str, int] = field(default_factory=lambda: _config("emojis"))
    modelist: dict[str, str] = field(default_factory=lambda: _config("modelist"))
    perms: dict[str, str] = field(default_factory=lambda: _config("perms"))
    tierlist: dict[str, dict[str, Any]] = field(default_factory=lambda: _config("tierlist"))


config: Config = Config()
