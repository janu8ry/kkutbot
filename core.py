import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta

import discord
from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from beanie.operators import Set
from discord.ext import commands
from koreanbots.client import Koreanbots
from sentry_sdk import capture_exception
from topgg import DBLClient

from config import config
from database import Client
from database.models import User

logger = logging.getLogger("kkutbot")

intents = discord.Intents(message_content=True, members=True, guilds=True, emojis=True, messages=True, reactions=True, typing=True)


class Kkutbot(commands.AutoShardedBot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=getattr(config.prefix, "test" if config.is_test else "main"),
            help_command=None,
            intents=intents,
            activity=discord.Game("봇 로딩중..."),
            owner_id=610625541157945344,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, replied_user=False),
            strip_after_prefix=True,
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
            chunk_guilds_at_startup=False,
        )
        self.playing_games: set[int] = set()
        self.koreanbots: Koreanbots = None  # type: ignore
        self.dbl: DBLClient = None  # type: ignore
        self.started_at: int = None  # type: ignore
        self.db: Client = Client()

        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.scheduler.add_listener(self.on_job_error, EVENT_JOB_ERROR)
        self.scheduler.add_job(self.update_presence, "interval", minutes=5)
        self.scheduler.add_job(self.reset_alerts, "cron", hour=0, minute=0, second=0)
        self.scheduler.add_job(self.reset_quest, "cron", hour=0, minute=0, second=0)
        if not config.is_test:
            self.scheduler.add_job(self.backup_data, "cron", hour=0, minute=0, second=0)
            self.scheduler.add_job(self.backup_log, "cron", hour=0, minute=5, second=0)
            self.scheduler.add_job(self.update_koreanbots, "interval", minutes=30)

    @staticmethod
    def on_job_error(event: JobExecutionEvent) -> None:
        logger.error(f"스케줄러 작업 '{event.job_id}' 실행에 실패했습니다.", exc_info=event.exception)
        capture_exception(event.exception)

    async def setup_hook(self) -> None:
        self.started_at = round(time.time())
        self.koreanbots = Koreanbots(config.token.koreanbots)
        self.dbl = DBLClient(self, config.token.dbl, autopost=not config.is_test, post_shard_count=not config.is_test)
        self.scheduler.start()
        await self.db.setup_db()

    def run_bot(self) -> None:
        super().run(getattr(config.token, "test" if config.is_test else "main"), log_level=logging.WARNING)

    async def is_owner(self, user: discord.User, /) -> bool:
        if user.id in config.admin:
            return True
        return await super().is_owner(user)

    async def try_reload(self, name: str) -> None:
        if name.rpartition(".")[2].startswith("_"):
            return
        try:
            await self.reload_extension(name)
        except commands.ExtensionNotLoaded:
            await self.load_extension(name)
        logger.info(f"카테고리 '{name.split('.')[1]}'을(를) 불러왔습니다!")

    async def update_presence(self) -> None:
        await self.change_presence(activity=discord.Game(f"/도움 | {len(self.guilds)} 서버에서 활동중"))

    def add_aliases(self, name: str, aliases: list[str]) -> None:
        cmd = self.get_command(name)
        if not isinstance(cmd, commands.Command):
            raise TypeError
        cmd.aliases = (*cmd.aliases, *aliases)
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
        await self.db.save(public)

    @staticmethod
    async def dump_data(fp: str) -> str | None:
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        db = config.mongo
        try:
            process = await asyncio.create_subprocess_exec(
                "mongodump",
                f"--host={db.host}:{db.port}",
                f"--db={db.db}",
                f"--username={db.username}",
                f"--password={db.password}",
                "--authenticationDatabase=admin",
                "--gzip",
                f"--archive={fp}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return "mongodump 실행 파일을 찾을 수 없습니다."
        _, stderr = await process.communicate()
        return stderr.decode(errors="replace").strip() if process.returncode != 0 else None

    async def backup_data(self) -> None:
        fp = f"backup/{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}.gz"
        if error := await self.dump_data(fp):
            logger.error(f"몽고DB 데이터 백업을 실패했습니다: {error}")
            return
        logger.info("몽고DB 데이터 백업 완료!")
        ch = self.get_channel(config.channels.backup_data)
        if isinstance(ch, discord.TextChannel):
            await ch.send(file=discord.File(fp=fp))
            logger.info("백업 채널에 데이터 업로드 완료!")
        else:
            logger.info("백업 채널에 데이터 업로드를 실패했습니다.")

    async def backup_log(self) -> None:
        fp = f"logs/{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}.log.gz"
        if not os.path.isfile(fp):
            logger.info("백업할 로그가 없어 로그 백업을 건너뜁니다.")
            return
        ch = self.get_channel(config.channels.backup_log)
        if isinstance(ch, discord.TextChannel):
            await ch.send(file=discord.File(fp=fp))
            logger.info("로그 백업 완료!")
        else:
            logger.info("로그 백업을 실패했습니다.")

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
                await self.try_reload(f"extensions.{package}")

    async def update_koreanbots(self) -> None:
        await self.koreanbots.update_bot_info(self.application_id, len(self.guilds), self.shard_count or 1)  # type: ignore

    def emoji(self, name: str) -> discord.Emoji:
        emoji_id = config.emojis.get(name)
        if emoji_id is None:
            raise KeyError
        result = self.get_emoji(emoji_id)
        if result is None:
            raise ValueError
        return result

    async def if_koreanbots_voted(self, user: discord.User | discord.Member) -> bool:
        try:
            response = await self.koreanbots.get_user_is_voted_bot(config.bot_id, user.id)
            return response.data.voted
        except TypeError:
            return False
