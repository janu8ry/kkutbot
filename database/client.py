import logging
import time
from typing import Any

import discord
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import MainDBData, TestDBData, config, get_nested_dict  # noqa

from .models import Guild, Public, User

__all__ = ["Client"]


logger = logging.getLogger("kkutbot")

dbconfig: MainDBData | TestDBData = getattr(config.mongo, "test" if config.is_test else "main")
type UserType = discord.User | discord.Member
type DocumentType = User | Guild | Public


class Client:
    def __init__(self) -> None:
        self.host = dbconfig.host
        self.port = dbconfig.port
        self.db = dbconfig.db
        self.username = dbconfig.username
        self.password = dbconfig.password
        self.client: AsyncIOMotorDatabase = None  # type: ignore

    async def setup_db(self) -> None:
        db_options = {}
        if all([username := self.username, password := self.password]):
            db_options["username"] = username
            db_options["password"] = password
            db_options["authSource"] = "admin"
        motor_client = AsyncIOMotorClient(host=self.host, port=self.port, **db_options)
        motor_client.append_metadata = motor_client.delegate.append_metadata
        self.client = motor_client[self.db]
        await init_beanie(database=self.client, document_models=[User, Guild, Public])  # type: ignore
        logger.info("DB 연결 완료!")

    @staticmethod
    async def get_user(user: UserType) -> User:
        """
        Gets a user model from the database.
        Returns an unregistered temporary model if the user is not in the database.
        Parameters
        ----------
        user : UserType
            Target User object to get data from
        Returns
        -------
        User
            User model from database
        """
        document = await User.get(user.id)
        global_name = user.global_name or user.name
        if document:
            if document.name != user.name or document.global_name != global_name:
                document.name = user.name
                document.global_name = global_name
                await document.save_changes()
        else:
            document = User(id=user.id, name=user.name, global_name=global_name)

        return document

    @staticmethod
    async def get_guild(guild: discord.Guild) -> Guild:
        """
        Gets a guild model from the database.
        Returns an uninvited temporary model if the guild is not in the database.
        Parameters
        ----------
        guild : discord.Guild
            Target Guild object to get data from
        Returns
        -------
        Guild
            Guild model from database
        """
        document = await Guild.get(guild.id)
        if not document:
            document = Guild(id=guild.id)

        return document

    @staticmethod
    async def count_users() -> int:
        """
        Counts the total number of users in the database.
        Returns
        -------
        int
            Total user count in the database
        """
        return await User.count()

    @staticmethod
    async def count_guilds() -> int:
        """
        Counts the total number of guilds in the database.
        Returns
        -------
        int
            Total guild count in the database
        """
        return await Guild.count()

    @staticmethod
    async def get_public() -> Public:
        document = await Public.get("public")
        if not document:
            document = Public(id="public")

        return document

    @staticmethod
    async def save(document: User | Guild | Public) -> DocumentType:
        if isinstance(document, User) and not document.registered:
            document.registered = round(time.time())
            await document.insert()
            return document
        elif isinstance(document, Guild) and not document.invited and document.command_used <= 1:
            document.invited = round(time.time())
            await document.insert()
            return document
        elif isinstance(document, Public) and not document.announcements and document.command_used <= 1:
            await document.insert()
            return document
        else:
            await document.save_changes()
            return document

    async def read_user(self, target: int, path: str | None = None) -> Any:
        main_data: dict[str, Any] | None = await self.client.user.find_one({"_id": getattr(target, "id", target)})
        if path is None or main_data is None:
            return main_data
        return get_nested_dict(main_data, path.split("."))
