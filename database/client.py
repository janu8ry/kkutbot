import logging
import time

import discord
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import Mongo, config  # noqa

from .models import Announcement, Guild, Public, User

__all__ = ["Client"]


logger = logging.getLogger("kkutbot")

dbconfig: Mongo = config.mongo
type UserType = discord.User | discord.Member
type DocumentType = User | Guild | Public


class Client:
    def __init__(self) -> None:
        self.client: AsyncIOMotorDatabase = None  # type: ignore

    async def setup_db(self) -> None:
        logger.info(f"{'테스트' if config.is_test else '프로덕션'} DB에 연결중...({dbconfig.host}:{dbconfig.port}/{dbconfig.db})")
        db_options = {}
        if dbconfig.username and dbconfig.password:
            db_options["username"] = dbconfig.username
            db_options["password"] = dbconfig.password
            db_options["authSource"] = "admin"
            logger.info("암호 인증으로 연결합니다. (authSource: admin)")
        else:
            logger.info("인증 없이 연결합니다.")
        motor_client = AsyncIOMotorClient(host=dbconfig.host, port=dbconfig.port, **db_options)
        motor_client.append_metadata = motor_client.delegate.append_metadata
        self.client = motor_client[dbconfig.db]
        await init_beanie(database=self.client, document_models=[User, Guild, Public, Announcement])  # type: ignore
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
    async def get_public() -> Public:
        document = await Public.get("public")
        if not document:
            document = Public(id="public")

        return document

    @staticmethod
    async def save(document: DocumentType) -> DocumentType:
        if document.get_saved_state() is None:
            if isinstance(document, User):
                document.registered = round(time.time())
            elif isinstance(document, Guild):
                document.invited = round(time.time())
            await document.insert()
        else:
            await document.save_changes()
        return document
