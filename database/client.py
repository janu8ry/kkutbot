import logging
import time
from typing import Any

import discord
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import MainDBData, TestDBData, config, get_nested_dict  # noqa

from .models import Guild, Public, User

__all__ = ["Client"]

type UserType = discord.User | discord.Member | discord.ClientUser | int
type DocumentType = User | Guild | Public

logger = logging.getLogger("kkutbot")

dbconfig: MainDBData | TestDBData = getattr(config.mongo, "test" if config.is_test else "main")


class Client:
    def __init__(self) -> None:
        self.ip = dbconfig.ip
        self.port = dbconfig.port
        self.db = dbconfig.db
        self.user = dbconfig.user
        self.password = dbconfig.password
        self.client: AsyncIOMotorDatabase | None = None

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
    async def get_user(user: UserType, *, safe: bool = True) -> User | None:
        """
        gets a user model from the database.
        Parameters
        ----------
        user : UserType
            Target User object to get data
        safe : bool
            return model with id and name if safe=True
        Returns
        -------
        Optional[User]
            User model from the database
        """
        if isinstance(user, int):
            document: User = await User.get(user)
        else:
            document: User = await User.get(user.id)
        if document:
            if document.name and document.name != user.name:
                document.name = user.name
                await document.save_changes()
        elif safe:
            document = User(id=user.id, name=user.name)

        return document

    @staticmethod
    async def get_guild(guild: discord.Guild | int, *, safe: bool = True) -> Guild | None:
        """
        gets a user model from the database.
        Parameters
        ----------
        guild : Union[discord.Guild, int]
            target Guild object to get data
        safe : bool
            return model with id and name if safe=True
        Returns
        -------
        Optional[Guild]
            Guild model from the database
        """
        if isinstance(guild, int):
            document: Guild = await Guild.get(guild)
        else:
            document: Guild = await Guild.get(guild.id)
        if not document and safe:
            document = Guild(id=guild.id)

        return document

    @staticmethod
    async def count_users() -> int:
        """
        counts total user in database
        Returns
        -------
        int
            total user count in the database
        """
        return await User.count()

    @staticmethod
    async def count_guilds() -> int:
        """
        counts total guild in database
        Returns
        -------
        int
            total guild count in the database
        """
        return await Guild.count()

    @staticmethod
    async def get_public() -> Public:
        document: Public = await Public.get("public")
        if not document:
            document = Public(id="public")

        return document

    @staticmethod
    async def save(document: User | Guild | Public) -> DocumentType:
        if isinstance(document, User) and not document.registered:
            document.registered = round(time.time())
            await document.insert()
        elif isinstance(document, Guild) and not document.invited and document.command_used <= 1:
            document.invited = round(time.time())
            await document.insert()
        elif isinstance(document, Public) and not document.announcements and document.command_used <= 1:
            await document.insert()
        else:
            await document.save_changes()
        return document

    async def read_user(self, target: int, path: str | None = None) -> Any:
        main_data: dict[Any, Any] = await self.client.user.find_one({"_id": getattr(target, "id", target)})
        if path is None:
            return main_data
        return get_nested_dict(main_data, path.split("."))
