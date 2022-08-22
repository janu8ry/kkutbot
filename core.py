import json
import logging
import os
import random
import shutil
import time
from datetime import datetime, timedelta
from typing import Type, Any, Optional, Callable, TypeVar, Union

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from koreanbots import Koreanbots
from koreanbots.integrations.discord import DiscordpyKoreanbots
from topgg import DBLClient
from motor.motor_asyncio import AsyncIOMotorDatabase  # noqa

from config import config
from tools.db import db, write
from tools.utils import format_date

logger = logging.getLogger("kkutbot")


class FormattingDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class KkutbotContext(commands.Context):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def send(
            self,
            content: Optional[str] = None,
            *,
            tts: bool = False,
            embed: Optional[discord.Embed] = None,
            embeds: Optional[list[discord.Embed]] = None,
            file: Optional[discord.File] = None,
            files: Optional[list[discord.File]] = None,
            stickers: Optional[discord.Sticker] = None,
            delete_after: Optional[float] = None,
            nonce: Optional[int] = None,
            allowed_mentions: Optional[discord.AllowedMentions] = None,
            reference: Union[discord.Message, discord.MessageReference, discord.PartialMessage, None] = None,
            mention_author: Optional[bool] = None,
            view: Optional[discord.ui.View] = None,
            suppress_embeds: bool = False,
            ephemeral: bool = False,
            escape_emoji_formatting: bool = False
    ) -> discord.Message:
        if (escape_emoji_formatting is False) and (self.command.qualified_name.split(" ")[0] != "jishaku"):
            content = content.format_map(FormattingDict(self.bot.dict_emojis())) if content else None
        return await super().send(content=content,
                                  tts=tts,
                                  embed=embed,
                                  embeds=embeds,
                                  file=file,
                                  files=files,
                                  stickers=stickers,
                                  delete_after=delete_after,
                                  nonce=nonce,
                                  allowed_mentions=allowed_mentions,
                                  reference=reference,
                                  mention_author=mention_author,
                                  view=view,
                                  suppress_embeds=suppress_embeds,
                                  ephemeral=ephemeral
                                  )

    async def reply(self, content: Optional[str] = None, mention_author: bool = False, **kwargs: Any) -> discord.Message:
        if (not kwargs.get("escape_emoji_formatting", False)) and (self.command.qualified_name.split(" ")[0] != "jishaku"):
            content = content.format_map(FormattingDict(self.bot.dict_emojis())) if content else None
        if self.interaction is None:
            return await self.send(
                content, reference=self.message, mention_author=mention_author, **kwargs
            )
        else:
            return await self.send(content, mention_author=mention_author, **kwargs)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class Kkutbot(commands.AutoShardedBot):
    __slots__ = ("koreanbots", "koreanbots_api", "dbl", "db", "scheduler", "started_at")

    def __init__(self) -> None:
        super().__init__(
            command_prefix=config(f"prefix.{'test' if config('test') else 'main'}"),
            help_command=None,
            intents=intents,
            activity=discord.Game("봇 로딩"),
            owner_id=610625541157945344,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            strip_after_prefix=True
        )
        self.db: AsyncIOMotorDatabase = db
        self.koreanbots: DiscordpyKoreanbots
        self.koreanbots_api: Koreanbots
        self.dbl: DBLClient
        self.started_at: int

        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.scheduler.add_job(self.update_presence, "interval", minutes=5)
        self.scheduler.add_job(self.reset_alerts, "cron", hour=0, minute=0, second=0)
        self.scheduler.add_job(self.reset_quest, "cron", hour=0, minute=0, second=0)
        if not config('test'):
            self.scheduler.add_job(self.backup_log, "cron", hour=0, minute=5, second=0)
            self.scheduler.add_job(self.backup_data, "cron", hour=5, minute=5, second=0)

    async def setup_hook(self) -> None:
        self.started_at = round(time.time())  # noqa
        self.koreanbots = DiscordpyKoreanbots(self, config("token.koreanbots"), run_task=not config("test"), include_shard_count=True)  # noqa
        self.koreanbots_api = Koreanbots(api_key=config("token.koreanbots"))  # noqa
        self.dbl = DBLClient(self, config("token.dbl"), autopost=not config("test"), post_shard_count=not config("test"))  # noqa
        self.scheduler.start()

    def run_bot(self) -> None:
        super().run(config(f"token.{'test' if config('test') else 'main'}"))

    async def try_reload(self, name: str) -> None:
        name = f"cogs.{name}"
        try:
            await self.reload_extension(name)
        except commands.ExtensionNotLoaded:
            await self.load_extension(name)
        logger.info(f"카테고리 '{name}'을(를) 불러왔습니다!")

    async def update_presence(self) -> None:
        await self.change_presence(activity=discord.Game(f"{self.command_prefix}도움 | {len(self.guilds)} 서버에서 활동"))

    @staticmethod
    async def reset_alerts() -> None:
        await write("general", "attendance", 0)
        await db.user.update_many({"alerts.attendance": True}, {"$set": {"alerts.attendance": False}})
        await db.user.update_many({"alerts.reward": True}, {"$set": {"alert.reward": False}})

    async def backup_data(self) -> None:  # TODO: 백업 이미지 변경
        for filename in os.listdir("/storage/mgob"):
            if filename.endswith(".gz"):
                date = format_date(datetime.now() - timedelta(days=1))
                fp = f"/storage/{date}.gz"
                os.replace(f"/storage/mgob/{filename}", fp)
                shutil.rmtree("/storage/mgob")
                await (self.get_channel(config("backup_channel.data"))).send(file=discord.File(fp=fp))
                logger.info("몽고DB 데이터 백업 완료!")

    async def backup_log(self) -> None:
        fp_before = f"logs/{format_date(datetime.now())}.log.gz"
        fp_after = f"logs/{format_date(datetime.now() - timedelta(days=1))}.log.gz"
        os.replace(fp_before, fp_after)
        await (self.get_channel(config("backup_channel.log"))).send(file=discord.File(fp=fp_after))
        logger.info("로그 백업 완료!")

    @staticmethod
    async def reset_quest() -> None:
        with open("static/quests.json", "r", encoding="utf-8") as f:
            quests = list(json.load(f).items())
        random.shuffle(quests)
        quest_data = {}
        for k, v in dict(quests[:3]).items():
            [t_start, t_end] = [int(t) for t in v["target"].split("-")]
            target = random.randint(t_start, t_end)
            v["name"] = v["name"].format(target)
            v["target"] = target
            v["reward"][0] = round(target * float(v["reward"][0].lstrip("*")))
            quest_data[k.replace(".", "/")] = v
        await write(None, "quests", quest_data)

    async def reload_all(self) -> None:
        for cogname in os.listdir("cogs"):
            if cogname.endswith(".py"):
                await self.try_reload(cogname[:-3])

    @staticmethod
    def dict_emojis() -> dict[str, str]:
        return {k: f"<:{k}:{v}>" for k, v in config("emojis").items()}

    async def if_koreanbots_voted(self, user: discord.User) -> bool:
        data = await self.koreanbots_api.is_voted_bot(user.id, 703956235900420226 if config("test") else self.user.id)
        return data.voted


F = TypeVar('F', bound=Callable[..., Any])


def command(name: Optional[str] = None, cls: Type[commands.Command] = commands.Command, **attrs: Any) -> Callable[[F], Any]:
    def decorator(func: F) -> commands.Command:
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
    def __init__(self, **kwargs: Any) -> None:
        if not kwargs.get("escape_emoji_formatting", False):
            if title := kwargs.get("title"):
                kwargs["title"] = title.format_map(FormattingDict(Kkutbot.dict_emojis()))
            if description := kwargs.get("description"):
                kwargs["description"] = description.format_map(FormattingDict(Kkutbot.dict_emojis()))
        super().__init__(**kwargs)

    def add_field(self, *, name: str, value: str, inline: bool = True, escape_emoji_formatting: bool = False) -> discord.Embed:
        if escape_emoji_formatting is False:
            name = name.format_map(FormattingDict(Kkutbot.dict_emojis()))
            value = value.format_map(FormattingDict(Kkutbot.dict_emojis()))
        return super().add_field(name=name, value=value, inline=inline)


discord.Embed = KkutbotEmbed
