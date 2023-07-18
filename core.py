import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Annotated, Any, Callable, Optional, Sequence, Type, TypeVar, Union

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from beanie.operators import Set
from discord.ext import commands
from koreanbots.integrations.discord import DiscordpyKoreanbots
from motor.motor_asyncio import AsyncIOMotorDatabase  # noqa
from topgg import DBLClient

from config import config
from database import Client
from database.models import User

logger = logging.getLogger("kkutbot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class FormattingDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class KkutbotContext(commands.Context):
    def __init__(self, bot: "Kkutbot", **kwargs: Any) -> None:
        super().__init__(bot=bot, **kwargs)
        self.bot: "Kkutbot" = bot

    async def send(
            self,
            content: Optional[str] = None,
            *,
            tts: bool = False,
            embed: Optional[discord.Embed] = None,
            embeds: Optional[Sequence[discord.Embed]] = None,
            file: Optional[discord.File] = None,
            files: Optional[Sequence[discord.File]] = None,
            stickers: Optional[Sequence[Union[discord.GuildSticker, discord.StickerItem]]] = None,
            delete_after: Optional[float] = None,
            nonce: Optional[Union[str, int]] = None,
            allowed_mentions: Optional[discord.AllowedMentions] = None,
            reference: Optional[Union[discord.Message, discord.MessageReference, discord.PartialMessage]] = None,
            mention_author: Optional[bool] = None,
            view: Optional[discord.ui.View] = None,
            suppress_embeds: bool = False,
            ephemeral: bool = False,
            silent: bool = False,
            escape_emoji_formatting: bool = False
    ) -> discord.Message:
        if (escape_emoji_formatting is False) and (self.command.qualified_name.split(" ")[0] != "jishaku"):
            content = content.format_map(FormattingDict(self.bot.dict_emojis())) if content else None
        return await super().send(content=content,  # noqa
                                  tts=tts,
                                  embed=embed,
                                  file=file,
                                  files=files,
                                  nonce=nonce,
                                  delete_after=delete_after,
                                  allowed_mentions=allowed_mentions,
                                  reference=reference,
                                  mention_author=mention_author,
                                  view=view,
                                  embeds=embeds,
                                  stickers=stickers,
                                  suppress_embeds=suppress_embeds,
                                  ephemeral=ephemeral,
                                  silent=silent
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


class Kkutbot(commands.AutoShardedBot):
    __slots__ = ("koreanbots", "koreanbots_api", "dbl", "db", "scheduler", "started_at")

    def __init__(self) -> None:
        super().__init__(
            command_prefix=getattr(config.prefix, "test" if config.is_test else "main"),
            help_command=None,
            intents=intents,
            activity=discord.Game("봇 로딩"),
            owner_id=610625541157945344,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            strip_after_prefix=True
        )
        self.guild_multi_games: list[int] = []
        self.koreanbots = Annotated[DiscordpyKoreanbots, None]
        self.dbl = Annotated[DBLClient, None]
        self.started_at = Annotated[int, None]
        self.db: Client = Client()

        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.scheduler.add_job(self.update_presence, "interval", minutes=5)
        self.scheduler.add_job(self.reset_alerts, "cron", hour=0, minute=0, second=0)
        self.scheduler.add_job(self.reset_quest, "cron", hour=0, minute=0, second=0)
        if not config.is_test:
            self.scheduler.add_job(self.backup_log, "cron", hour=0, minute=5, second=0)
            self.scheduler.add_job(self.backup_data, "cron", hour=5, minute=5, second=0)

    async def setup_hook(self) -> None:
        self.started_at = round(time.time())
        self.koreanbots = DiscordpyKoreanbots(self, config.token.koreanbots, run_task=not config.is_test, include_shard_count=True)
        self.dbl = DBLClient(self, config.token.dbl, autopost=not config.is_test, post_shard_count=not config.is_test)
        self.scheduler.start()
        await self.db.setup_db()

    def run_bot(self) -> None:
        super().run(getattr(config.token, "test" if config.is_test else "main"))

    async def get_context(self, origin: Union[discord.Message, discord.Interaction], /, *, cls=KkutbotContext) -> KkutbotContext:
        return await super().get_context(origin, cls=cls)

    async def is_owner(self, user: discord.User, /) -> bool:
        if user.id in config.admin:
            return True
        return await super().is_owner(user)

    async def try_reload(self, name: str) -> None:
        path = f"extensions.{name}"
        try:
            await self.reload_extension(path)
        except commands.ExtensionNotLoaded:
            await self.load_extension(path)
        logger.info(f"카테고리 '{name}'을(를) 불러왔습니다!")

    async def update_presence(self) -> None:
        await self.change_presence(activity=discord.Game(f"{self.command_prefix}도움 | {len(self.guilds)} 서버에서 활동"))

    def add_aliases(self, name: str, aliases: list[str]) -> None:
        cmd = self.get_command(name)
        cmd.aliases = list(cmd.aliases)
        cmd.aliases.extend(aliases)
        cmd.aliases = tuple(cmd.aliases)
        if parent := cmd.parent:
            parent.remove_command(cmd.name)
            parent.add_command(cmd)
        else:
            self.remove_command(name)
            self.add_command(cmd)

    async def reset_alerts(self) -> None:
        public = await self.db.get_public()
        public.attendance = 0
        await User.find(User.alerts.attendance == True).update(Set({User.alerts.attendance: False}))  # noqa
        await User.find(User.alerts.reward == True).update(Set({User.alerts.reward: False}))  # noqa

    async def backup_data(self) -> None:
        for filename in os.listdir("backup"):
            if filename[:10].isdecimal():
                date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                fp = f"backup/{date}.gz"
                os.replace(f"backup/{filename}", fp)
                await (self.get_channel(config.channels.backup_data)).send(file=discord.File(fp=fp))
                logger.info("몽고DB 데이터 백업 완료!")

    async def backup_log(self) -> None:
        fp_before = f"logs/{datetime.now().strftime('%Y-%m-%d')}.log.gz"
        fp_after = f"logs/{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}.log.gz"
        os.replace(fp_before, fp_after)
        await (self.get_channel(config.channels.backup_log)).send(file=discord.File(fp=fp_after))
        logger.info("로그 백업 완료!")

    async def reset_quest(self) -> None:
        public = await self.db.get_public()
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
        public.quests = quest_data
        await self.db.save(public)

    async def reload_all(self) -> None:
        for package in os.listdir("extensions"):
            if os.path.isdir(f"extensions/{package}"):
                await self.try_reload(package)

    @staticmethod
    def dict_emojis() -> dict[str, str]:
        return {k: f"<:{k}:{v}>" for k, v in config.emojis.items()}

    async def if_koreanbots_voted(self, user: discord.User) -> bool:
        data = await self.koreanbots.is_voted_bot(user.id, 703956235900420226)  # noqa
        return data.voted


F = TypeVar("F", bound=Callable[..., Any])


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
