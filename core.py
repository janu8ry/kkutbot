import os
import logging
import subprocess
from datetime import date
from typing import Type

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp

from tools import webupdater
from tools.config import config
from tools.db import db, dbconfig, username, password


logger = logging.getLogger("kkutbot")


class KkutbotContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def send(
        self,
        content=None,
        *,
        tts=False,
        embed=None,
        file=None,
        files=None,
        delete_after=None,
        nonce=None,
        allowed_mentions=None,
        reference=None,
        mention_author=None,
        escape_emoji_formatting=False,
    ) -> discord.Message:
        if escape_emoji_formatting is False:
            content = content.format(**self.bot.dict_emojis()) if content else None
        return await super().send(
            content=content,
            tts=tts,
            embed=embed,
            file=file,
            files=files,
            delete_after=delete_after,
            nonce=nonce,
            allowed_mentions=allowed_mentions,
            reference=reference,
            mention_author=mention_author,
        )

    async def reply(self, content=None, **kwargs) -> discord.Message:
        if not kwargs.get("escape_emoji_formatting", False):
            content = content.format(**self.bot.dict_emojis()) if content else None
        return await super().reply(content=content, **kwargs)


class Kkutbot(commands.AutoShardedBot):
    __version__ = "2.0.0-alpha"
    __slots__ = ()
    description = "끝봇은 끝말잇기가 주 기능인 인증된 디스코드 봇입니다."
    version_info = "개발중"

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(
                config(f"prefix.{'test' if config('test') else 'main'}")
            ),
            help_command=None,  # disables the default help command
            intents=discord.Intents.default(),
            activity=discord.Game("봇 로딩"),
            owner_id=610625541157945344,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            strip_after_prefix=True,  # allows 'ㄲ ' prefix
        )
        self.webclient = webupdater.Client(
            bot=self,
            koreanbots_token=config("token.koreanbots"),
            topgg_token=config("token.topgg"),
            post=not config("test"),
        )
        self.db = db

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.update_presence, "interval", minutes=1)
        if not config("test"):
            self.scheduler.add_job(self.backup, "cron", hour=5, minute=0, second=0)
        self.scheduler.start()

    def run_bot(self):
        super().run(config(f"token.{'test' if config('test') else 'main'}"))

    def try_reload(self, name: str):
        name = f"cogs.{name}"
        try:
            self.reload_extension(name)
        except commands.ExtensionNotLoaded:
            self.load_extension(name)
        logger.info(f"카테고리 '{name}'을(를) 불러왔습니다!")

    async def update_presence(self):
        await self.change_presence(
            activity=discord.Game(f"ㄲ도움 | {len(self.guilds)} 서버에서 끝말잇기")
        )

    def reload_all(self):
        for cogname in os.listdir("cogs"):
            if cogname.endswith(".py"):
                self.try_reload(cogname[:-3])

    async def on_error(self, event_method, *args, **kwargs):
        if not config("test"):
            raise

    @staticmethod
    def dict_emojis():
        return {k: f"<:{k}:{v}>" for k, v in config("emojis").items()}

    @staticmethod
    async def if_koreanbots_voted(user: discord.User) -> bool:
        async with aiohttp.ClientSession() as session, session.get(
            f"https://koreanbots.dev/api/v2/bots/703956235900420226/vote?userID={user.id}",
            headers={"Authorization": config("token.koreanbots")},
        ) as response:
            data = await response.json()
        return data["data"]["voted"]

    async def backup(self):
        logger.debug("DB 백업 준비중...")
        today = date.today().strftime("%Y-%m-%d")
        fp = os.path.join(os.getcwd(), "backup", f"{today}.archive")
        cmd = f"mongodump -h {dbconfig('ip')}:{dbconfig('port')} --db {dbconfig('db')} --gzip --archive={fp}"
        if all([username, password]):
            cmd += f" --authenticationDatabase admin -u {username} -p {password}"
        try:
            subprocess.run(cmd, check=True, shell=True)
        except subprocess.CalledProcessError as error:
            logger.error(f"DB 백업에 실패했습니다.\n에러 내용: {error}")
            return
        os.remove(fp)
        logger.debug("DB 백업 완료!")
        await (self.get_channel(config("backup_channel"))).send(
            file=discord.File(fp=fp)
        )


def command(name: str = None, cls: Type[commands.Command] = None, **attrs):
    def decorator(func):
        if isinstance(func, commands.Command):
            raise TypeError("Callback is already a command.")
        if ("user" in func.__annotations__) and (attrs.get("rest_is_raw") is not False):
            rest_is_raw = attrs.pop("rest_is_raw", True)
        else:
            rest_is_raw = attrs.pop("rest_is_raw", False)
        return cls(func, name=name, rest_is_raw=rest_is_raw, **attrs)

    return decorator


commands.command = command


class KkutbotEmbed(discord.Embed):
    def __init__(self, **kwargs):
        if not kwargs.get("escape_emoji_formatting", False):
            if title := kwargs.get("title"):
                kwargs["title"] = title.format(**Kkutbot.dict_emojis())
            if description := kwargs.get("description"):
                kwargs["description"] = description.format(**Kkutbot.dict_emojis())
        super().__init__(**kwargs)

    def add_field(self, *, name, value, inline=True, escape_emoji_formatting=False):
        if escape_emoji_formatting is False:
            name = name.format(**Kkutbot.dict_emojis()) if name else None
            value = value.format(**Kkutbot.dict_emojis()) if value else None
        return super().add_field(name=name, value=value, inline=inline)


discord.Embed = KkutbotEmbed
