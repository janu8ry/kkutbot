import json
import logging
import os
import random
import time
from datetime import datetime, timedelta

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from beanie.operators import Set
from discord.ext import commands
from koreanbots.integrations.discord import DiscordpyKoreanbots
from topgg import DBLClient

from config import config
from database import Client
from database.models import User
from tools.overides import KkutbotContext

logger = logging.getLogger("kkutbot")

intents = discord.Intents(
    message_content=True,
    members=True,
    guilds=True,
    emojis=True,
    messages=True,
    reactions=True,
    typing=True
)


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
            strip_after_prefix=True,
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            chunk_guilds_at_startup=False
        )
        self.guild_multi_games: list[int] = []
        self.koreanbots: DiscordpyKoreanbots | None = None
        self.dbl: DBLClient | None = None
        self.started_at: int | None = None
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

    async def get_context(self, origin: discord.Message | discord.Interaction, /, *, cls=KkutbotContext) -> KkutbotContext:
        return await super().get_context(origin, cls=cls)

    async def is_owner(self, user: discord.User, /) -> bool:
        if user.id in config.admin:
            return True
        return await super().is_owner(user)

    async def try_reload(self, name: str) -> None:
        if name == "__pycache__":
            return
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
        await self.db.save(public)

    async def backup_data(self) -> None:
        files = []
        for filename in os.listdir("backup"):
            if filename[:10].isdecimal():
                files.append(filename)
        files.sort(key=lambda f: int(f[:10]), reverse=True)
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        fp = f"backup/{date}.gz"
        os.replace(f"backup/{files[0]}", fp)
        await (self.get_channel(config.channels.backup_data)).send(file=discord.File(fp=fp))
        logger.info("몽고DB 데이터 백업 완료!")
        for filename in files[1:]:
            os.remove(f"backup/{filename}")

    async def backup_log(self) -> None:
        fp = f"logs/{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}.log.gz"
        await (self.get_channel(config.channels.backup_log)).send(file=discord.File(fp=fp))
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

    async def if_koreanbots_voted(self, user: discord.User) -> bool:
        data = await self.koreanbots.is_voted_bot(user.id, 703956235900420226)
        return data.voted
