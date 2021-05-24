import json
import os
import random
import shutil
import subprocess
import zipfile
from datetime import date
from typing import Type

import dbl
import discord
import koreanbots
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dhooks import Webhook
from discord.ext import commands

# from ext import hanmaru
from ext.db import config, db, dbconfig, password, username, write


class Kkutbot(commands.AutoShardedBot):
    __version__ = "1.7.0"
    __slots__ = ("db", "koreanbots", "dblpy", "webhook", "hanmaru", "scheduler")
    description = "끝봇은 끝말잇기가 주 기능인 인증된 디스코드 봇입니다."
    version_info = "신규 명령어 '퀘스트' 추가 & 끝말잇기 대폭 개선"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = db  # mongoDB
        self.koreanbots = koreanbots.Client(self, config('token.koreanbots'), postCount=not config('test'))  # koreanbots
        self.dblpy = dbl.DBLClient(self, config('token.dbl'), autopost=not config('test'))   # top.gg
        self.webhook = Webhook.Async(config(f'webhook.{"test" if config("test") else "main"}'))  # logger webhook
        # self.hanmaru = hanmaru.Handler(self)

        # schedulers
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.reset_daily, 'cron', day_of_week=0, hour=0, minute=0, second=0, misfire_grace_time=1000)
        self.scheduler.add_job(self.reset_daily_alert, 'cron', hour=0, minute=0, second=1)
        self.scheduler.add_job(self.reset_quest, 'cron', hour=0, minute=0, second=2)
        self.scheduler.add_job(self.update_presence, 'interval', minutes=1)
        if not config('test'):
            self.scheduler.add_job(self.backup, 'cron', hour=5, minute=0, second=0)
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
        name = f"cogs.{name}"
        try:
            self.reload_extension(name)
        except commands.ExtensionNotLoaded:
            self.load_extension(name)

    async def update_presence(self):
        await self.change_presence(activity=discord.Game(f"ㄲ도움 | {len(self.guilds)} 서버에서 끝말잇기"))

    async def backup(self):
        tmp = "./tmp"
        cmd = f"mongodump -h {dbconfig('ip')}:{dbconfig('port')} --db {dbconfig('db')} -o {tmp}"
        if all([username, password]):
            cmd += f" --authenticationDatabase admin -u {username} -p {password}"
        subprocess.run(cmd, shell=True)
        today = date.today().strftime("%Y-%m-%d")
        fp = os.path.join(os.getcwd(), 'backup', f'backup-{today}.zip')
        with zipfile.ZipFile(fp, 'w') as archive:
            for folder, _, files in os.walk(tmp):
                for file in files:
                    archive.write(os.path.join(folder, file), os.path.relpath(os.path.join(folder, file), '.'), compress_type=zipfile.ZIP_DEFLATED)
        shutil.rmtree(tmp)
        await (self.get_channel(config('backup_channel'))).send(file=discord.File(fp=fp))

    @staticmethod
    def dict_emojis():
        return {k: f"<:{k}:{v}>" for k, v in config('emojis').items()}

    @staticmethod
    async def reset_daily_alert():
        await write('general', 'daily', 0)
        await db.user.update_many({'alert.daily': True}, {'$set': {'alert.daily': False}})

    @staticmethod
    async def reset_daily():
        week_daily = {'0': False, '1': False, '2': False, '3': False, '4': False, '5': False, '6': False}
        await db.user.update_many(
            {},
            {
                '$set': {
                    'daily': week_daily
                }
            }
        )

    @staticmethod
    async def reset_quest():
        with open('general/quest.json', 'r', encoding="utf-8") as f:
            quests = list(json.load(f).items())
        random.shuffle(quests)
        quests = dict(quests)
        k = list(quests.keys())
        v = list(quests.values())
        await write(None, 'quest', {
            k[0].replace(".", "/"): v[0],
            k[1].replace(".", "/"): v[1],
            k[2].replace(".", "/"): v[2]
        })


class KkutbotContext(commands.Context):
    """Custom Context object for kkutbot."""
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
                   mention_author=None,
                   escape_emoji_formatting=False
                   ) -> discord.Message:
        if escape_emoji_formatting is False:
            content = content.format(**self.bot.dict_emojis()) if content else None
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

    async def reply(self, content=None, **kwargs) -> discord.Message:  # same as above
        if not kwargs.get('escape_emoji_formatting', False):
            content = content.format(**self.bot.dict_emojis()) if content else None
        return await super().reply(content=content, **kwargs)


class KkutbotCommand(commands.Command):
    """Custom Commands object for kkutbot."""
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)


def command(name: str = None, cls: Type[commands.Command] = None, **attrs):
    cls = cls or KkutbotCommand

    def decorator(func):
        if isinstance(func, commands.Command):
            raise TypeError('Callback is already a command.')
        if ('user' in func.__annotations__) and (attrs.get('rest_is_raw') is not False):
            rest_is_raw = attrs.pop('rest_is_raw', True)  # toggle 'rest_is_raw' option when command uses SpecialMemberConverter
        else:
            rest_is_raw = attrs.pop('rest_is_raw', False)
        return cls(func, name=name, rest_is_raw=rest_is_raw, **attrs)

    return decorator


commands.command = command  # replace 'command' decorator in 'discord.ext.commands' module


class KkutbotEmbed(discord.Embed):
    def __init__(self, **kwargs):
        if not kwargs.get('escape_emoji_formatting', False):
            if title := kwargs.get('title'):
                kwargs['title'] = title.format(**Kkutbot.dict_emojis())
            if description := kwargs.get('description'):
                kwargs['description'] = description.format(**Kkutbot.dict_emojis())
        super().__init__(**kwargs)

    def add_field(self, *, name, value, inline=True, escape_emoji_formatting=False):
        if escape_emoji_formatting is False:
            name = name.format(**Kkutbot.dict_emojis()) if name else None
            value = value.format(**Kkutbot.dict_emojis()) if value else None
        return super().add_field(name=name, value=value, inline=inline)


discord.Embed = KkutbotEmbed  # replace 'Embed' class in 'discord.embeds' module
