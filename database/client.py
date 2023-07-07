import logging
import time
from typing import Union, Annotated, Optional
from typing_extensions import TypeAlias

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import discord

from config import config, get_nested_dict, MainDBData, TestDBData  # noqa
from .models import User, Guild, Public  # type: ignore

__all__ = ["Client"]


logger = logging.getLogger("kkutbot")

dbconfig: Union[MainDBData, TestDBData] = getattr(config.mongo, "test" if config.is_test else "main")
UserType: TypeAlias = Union[discord.User, discord.Member, discord.ClientUser, int]
DocumentType: TypeAlias = Union[User, Guild, Public]


class Client:
    def __init__(self) -> None:
        self.ip = dbconfig.ip
        self.port = dbconfig.port
        self.db = dbconfig.db
        self.user = dbconfig.user
        self.password = dbconfig.password
        self.client = Annotated[AsyncIOMotorClient, None]

    async def setup_db(self) -> None:
        db_options = {}
        if all([username := self.user, password := self.password]):
            db_options["username"] = username
            db_options["password"] = password
            db_options["authSource"] = "admin"
        self.client = AsyncIOMotorClient(host=self.ip, port=self.port, **db_options)[self.db]
        logger.info("DB 연결 완료!")
        await init_beanie(database=self.client, document_models=[User, Guild, Public])
        logger.info("Beaine 설정 완료!")

    @staticmethod
    async def get_user(user: UserType, *, safe: bool = True) -> Optional[User]:
        """
        gets user model from database.
        Parameters
        ----------
        user : UserType
            Target User object to get data
        safe : bool
            return model with id and name if safe=True
        Returns
        -------
        Optional[User]
            User model from database
        """
        if isinstance(user, int):
            document: User = await User.get(user)  # type: ignore
        else:
            document: User = await User.get(user.id)  # type: ignore
        if document:
            if document.name and document.name != user.name:
                document.name = user.name
                await document.save_changes()
        elif safe:
            document = User(id=user.id, name=user.name)

        return document

    @staticmethod
    async def get_guild(guild: Union[discord.Guild, int], *, safe: bool = True) -> Optional[Guild]:
        """
        gets user model from database.
        Parameters
        ----------
        guild : Union[discord.Guild, int]
            target Guild object to get data
        safe : bool
            return model with id and name if safe=True
        Returns
        -------
        Optional[Guild]
            Guild model from database
        """
        if isinstance(guild, int):
            document: Guild = await Guild.get(guild)  # type: ignore
        else:
            document: Guild = await Guild.get(guild.id)  # type: ignore
        if not document and safe:
            document = Guild(id=guild.id, name=guild.name)

        return document

    @staticmethod
    async def count_users() -> int:
        """
        counts total user in database
        Returns
        -------
        int
            total user count in database
        """
        return await User.count()

    @staticmethod
    async def count_guilds() -> int:
        """
        counts total guild in database
        Returns
        -------
        int
            total guild count in database
        """
        return await Guild.count()

    @staticmethod
    async def get_public() -> Public:
        document: Public = await Public.get("public")  # type: ignore
        if not document:
            document = Public(id="public")

        return document

    @staticmethod
    async def save(document: Union[User, Guild, Public]) -> DocumentType:
        if isinstance(document, User) and not document.registered:
            document.registered = round(time.time())
            await document.insert()
            return document
        elif isinstance(document, Guild) and not document.invited:
            document.invited = round(time.time())
            await document.insert()
            return document
        elif isinstance(document, Public) and not document.announcements:
            await document.insert()
            return document
        else:
            await document.save_changes()
            return document
