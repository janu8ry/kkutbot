import json

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import dbl
from dhooks import Webhook
import koreanbots
import UniqueBotsKR

# from ext import hanmaru
from ext.db import write, db, config


class Kkutbot(commands.AutoShardedBot):
    __version__ = "1.7.0a"
    description = "끝봇은 끝말잇기가 주 기능인 인증된 디스코드 봇입니다."
    version_info = "개발중"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dblpy = dbl.DBLClient(self, config('token.dbl'), autopost=not config('test'))
        self.koreanbots = koreanbots.Client(self, config('token.koreanbots'), postCount=not config('test'))
        self.uniquebots = UniqueBotsKR.client(self, config('token.uniquebots'), autopost=not config('test'))
        self.webhook = Webhook.Async(config('webhook_url'))
        # self.hanmaru = hanmaru.Handler(self)
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.reset_daily_alert, 'cron', hour=0, minute=0, second=1)
        self.scheduler.add_job(self.reset_daily, 'cron', day_of_week=0, hour=0, minute=0, second=0, misfire_grace_time=1000)
        self.scheduler.add_job(self.update_presence, 'interval', seconds=10)
        self.scheduler.start()

    async def log(self, msg: str, embed: discord.Embed = None):
        await self.webhook.send(msg, embed=embed)

    async def if_koreanbots_voted(self, user: discord.User) -> bool:
        try:
            voteinfo = await self.koreanbots.getVote(user.id)
        except koreanbots.NotFound:
            return False
        else:
            if voteinfo.response['voted']:
                return True
            else:
                return False

    def try_reload(self, name: str):
        try:
            self.reload_extension(f"cogs.{name}")
        except commands.ExtensionNotLoaded:
            try:
                self.load_extension(f"cogs.{name}")
            except commands.ExtensionNotFound:
                self.load_extension(name)

    async def reset_daily_alert(self):  # noqa
        write('general', 'daily', 0)
        db.user.update_many({'alert.daily': True}, {'$set': {'alert.daily': False}})

    async def reset_daily(self):  # noqa
        week_daily = {'0': False, '1': False, '2': False, '3': False, '4': False, '5': False, '6': False}
        db.user.update_many(None, {'$set': {'daily': week_daily}})

    async def update_presence(self):
        await self.change_presence(activity=discord.Game(f"ㄲ도움 | {len(self.guilds)} 서버에서 끝말잇기"))

    @staticmethod
    def wordlist() -> dict:
        with open('general/wordlist.json', 'r', encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def DUlaw() -> dict:
        with open('general/DUlaw.json', 'r', encoding="utf-8") as f:
            return json.load(f)
