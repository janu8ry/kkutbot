from typing import Callable

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dhooks import Webhook
import dbl
import koreanbots
import UniqueBotsKR

# from ext import hanmaru
from ext.db import write, db, config


class Kkutbot(commands.AutoShardedBot):
    __version__ = "1.7.0a"
    __slots__ = ("db", "dblpy", "koreanbots", "uniquebots", "webhook", "hanmaru", "scheduler")
    description = "끝봇은 끝말잇기가 주 기능인 인증된 디스코드 봇입니다."
    version_info = "개발중"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.dblpy = dbl.DBLClient(self, config('token.dbl'), autopost=not config('test'))
        self.koreanbots = koreanbots.Client(self, config('token.koreanbots'), postCount=not config('test'))
        self.uniquebots = UniqueBotsKR.client(self, config('token.uniquebots'), autopost=not config('test'))
        self.webhook = Webhook.Async(config(f'webhook.{"test" if config("test") else "main"}'))
        # self.hanmaru = hanmaru.Handler(self)
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.reset_daily_alert, 'cron', hour=0, minute=0, second=1)
        self.scheduler.add_job(self.reset_daily, 'cron', day_of_week=0, hour=0, minute=0, second=0, misfire_grace_time=1000)
        self.scheduler.add_job(self.update_presence, 'interval', seconds=10)
        self.scheduler.start()

    async def log(self, msg: str, embed: discord.Embed = None, nomention=True):
        if nomention:
            msg = discord.utils.escape_mentions(msg)
        await self.webhook.send(msg, embed=embed)

    async def if_koreanbots_voted(self, user: discord.User) -> bool:
        try:
            voteinfo = await self.koreanbots.getVote(user.id)
        except koreanbots.NotFound:
            return False
        else:
            return voteinfo.response['voted']

    def try_reload(self, name: str):
        try:
            self.reload_extension(f"cogs.{name}")
        except commands.ExtensionNotLoaded:
            try:
                self.load_extension(f"cogs.{name}")
            except commands.ExtensionNotFound:
                self.load_extension(name)

    async def update_presence(self):
        await self.change_presence(activity=discord.Game(f"ㄲ도움 | {len(self.guilds)} 서버에서 끝말잇기"))

    @property
    def emojis(self):
        return {k: f"<:{k}:{v}>" for k, v in config('emojis').items()}

    @staticmethod
    async def reset_daily_alert():
        write('general', 'daily', 0)
        db.user.update_many({'alert.daily': True}, {'$set': {'alert.daily': False}})

    @staticmethod
    async def reset_daily():
        week_daily = {'0': False, '1': False, '2': False, '3': False, '4': False, '5': False, '6': False}
        db.user.update_many(None, {'$set': {'daily': week_daily}})


class KkutbotContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def send(self,
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
                   mention_author=None
                   ) -> discord.Message:
        content = content.format(**self.bot.emojis) if content else None
        return await super().send(content=content,
                                  tts=tts,
                                  embed=embed,
                                  file=file,
                                  files=files,
                                  delete_after=delete_after,
                                  nonce=nonce,
                                  allowed_mentions=allowed_mentions,
                                  reference=reference,
                                  mention_author=mention_author
                                  )

    async def reply(self, content=None, **kwargs):
        content = content.format(**self.bot.emojis) if content else None
        return await super().reply(content=content, **kwargs)


class KkutbotCommand(commands.Command):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)


def command(name=None, cls=None, **attrs):
    cls = cls or KkutbotCommand

    def decorator(func):
        if isinstance(func, commands.Command):
            raise TypeError('Callback is already a command.')
        if ('user' in func.__annotations__) and (attrs.get('rest_is_raw') is not False):
            rest_is_raw = attrs.pop('rest_is_raw', True)
        else:
            rest_is_raw = attrs.pop('rest_is_raw', False)
        return cls(func, name=name, rest_is_raw=rest_is_raw, **attrs)

    return decorator


commands.command = command
