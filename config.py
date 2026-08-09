import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

__all__ = ["get_nested_dict", "Mongo", "config"]

load_dotenv()

IS_TEST = os.environ.get("TESTMODE", "true").strip().lower() != "false"


def base_url(secure: bool = False) -> str:
    return f"http{'s' if secure else ''}://{'localhost' if IS_TEST else os.environ.get('HOST_URL') or 'localhost'}"


with open("static/emojis.json", "r", encoding="utf-8") as f:
    EMOJIS: dict[str, int] = json.load(f)


def get_nested_dict(data: Mapping[str, Any], path: list[str]) -> Any:
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
    result: Any = data
    for i in path:
        result = result.get(i, None)
    return result


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key) or default


@dataclass(frozen=True)
class Prefix:
    main: str = "ㄲ"
    test: str = "ㅌㄲ"


@dataclass(frozen=True)
class Token:
    main: str = field(default_factory=lambda: _env("BOT_TOKEN_MAIN"))
    test: str = field(default_factory=lambda: _env("BOT_TOKEN_TEST"))
    koreanbots: str = field(default_factory=lambda: _env("TOKEN_KOREANBOTS"))
    dbl: str = field(default_factory=lambda: _env("TOKEN_DBL"))


@dataclass(frozen=True)
class Color:
    blue: int = 0x4374D9
    red: int = 0xCC3D3D
    green: int = 0x47C83E


@dataclass(frozen=True)
class Mongo:
    host: str = field(default_factory=lambda: _env("MONGO_HOST", "localhost" if IS_TEST else "mongo"))
    port: int = field(default_factory=lambda: int(_env("MONGO_PORT", "27017")))
    db: str = field(default_factory=lambda: _env("MONGO_DB", "kkutbot"))
    username: str = field(default_factory=lambda: _env("MONGO_USERNAME"))
    password: str = field(default_factory=lambda: _env("MONGO_PASSWORD"))


@dataclass(frozen=True)
class Channels:
    backup_data: int = 838371534690844672
    backup_log: int = 987017719545229463
    error_log: int = 1016347873253793832


@dataclass(frozen=True)
class Sentry:
    dsn: str = field(default_factory=lambda: _env("SENTRY_DSN"))
    url: str = field(default_factory=lambda: _env("SENTRY_URL"))


@dataclass(frozen=True)
class InviteLink:
    bot: str = (
        "https://discord.com/oauth2/authorize?client_id=703956235900420226&scope=bot+applications.commands"
        "&permissions=387136&response_type=code&redirect_uri=https%3A%2F%2Fdiscord.gg%2Fz8tRzwf"
    )
    server: str = "https://discord.gg/z8tRzwf"


@dataclass(frozen=True)
class Links:
    invite: InviteLink = InviteLink()
    privacy_policy: str = "https://github.com/janu8ry/kkutbot/blob/main/privacy.md"
    terms_of_service: str = "https://github.com/janu8ry/kkutbot/blob/main/privacy.md"
    koreanbots: str = "https://koreanbots.dev/bots/703956235900420226"
    dbl: str = "https://top.gg/bot/703956235900420226"
    github: str = "https://github.com/janu8ry/kkutbot"
    website: str = "https://kkutbot.github.io"
    portainer: str = f"{base_url(secure=True)}:9443"
    dbgate: str = f"{base_url()}:8081"
    logs: str = f"{base_url()}:8082/explore"


@dataclass(frozen=True)
class Config:
    is_test: bool = IS_TEST
    version: str = "3.0"
    bot_id: int = 703956235900420226
    admin: tuple[int, ...] = (610625541157945344, 394116972176080916)
    prefix: Prefix = Prefix()
    token: Token = Token()
    colors: Color = Color()
    mongo: Mongo = Mongo()
    channels: Channels = Channels()
    sentry: Sentry = Sentry()
    links: Links = Links()
    emojis: dict[str, int] = field(default_factory=lambda: EMOJIS)


config: Config = Config()
