import os
import logging

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tools import webupdater
from tools.config import config


logger = logging.getLogger("kkutbot")


class KkutbotContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Kkutbot(commands.AutoShardedBot):
    __version__ = "2.0.0-alpha"
    __slots__ = ()
    description = "끝봇은 끝말잇기가 주 기능인 인증된 디스코드 봇입니다."
    version_info = "개발중"

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        self.webclient = webupdater.Client(
            bot=self,
            koreanbots_token=config("token.koreanbots"),
            topgg_token=config("token.topgg"),
            post=not config("test")
        )

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.update_presence, 'interval', minutes=1)
        self.scheduler.start()

    async def get_context(self, message: discord.Message, *, cls=KkutbotContext) -> KkutbotContext:
        return await super().get_context(message=message, cls=cls)

    def try_reload(self, name: str):
        name = f"cogs.{name}"
        try:
            self.reload_extension(name)
        except commands.ExtensionNotLoaded:
            self.load_extension(name)

    async def update_presence(self):
        await self.change_presence(activity=discord.Game(f"ㄲ도움 | {len(self.guilds)} 서버에서 끝말잇기"))

    def reload_all(self):
        for cogname in os.listdir("cogs"):
            if cogname.endswith(".py"):
                self.try_reload(cogname[:-3])
                logger.info(f"카테고리 '{cogname[:-3]}'을(를) 불러왔습니다!")

    @staticmethod
    def dict_emojis():
        return {k: f"<:{k}:{v}>" for k, v in config('emojis').items()}
