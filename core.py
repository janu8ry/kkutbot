import logging
import os
from typing import Type

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from koreanbots import Koreanbots
from koreanbots.integrations.discord import DiscordpyKoreanbots
from topgg import DBLClient

from tools.config import config
from tools.db import db

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
            embeds=None,
            file=None,
            files=None,
            stickers=None,
            delete_after=None,
            nonce=None,
            allowed_mentions=None,
            reference=None,
            mention_author=None,
            view=None,
            suppress_embeds=False,
            ephemeral=False,
            escape_emoji_formatting=False
    ) -> discord.Message:
        if (escape_emoji_formatting is False) and (getattr(self.command, "name") != "jishaku"):
            content = content.format(**self.bot.dict_emojis()) if content else None
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

    async def reply(self, content=None, **kwargs) -> discord.Message:
        if (not kwargs.get('escape_emoji_formatting', False)) and (getattr(self.command, "name") != "jishaku"):
            content = content.format(**self.bot.dict_emojis()) if content else None
        return await super().reply(content=content, **kwargs)


class Kkutbot(commands.AutoShardedBot):
    __version__ = "2.0.0-alpha"
    __slots__ = ("webclient", "db", "scheduler")
    description = "끝봇은 끝말잇기가 주 기능인 인증된 디스코드 봇입니다."
    version_info = "개발중"

    def __init__(self):
        super().__init__(
            command_prefix=config(f"prefix.{'test' if config('test') else 'main'}"),
            help_command=None,  # disables the default help command
            intents=discord.Intents.default(),
            activity=discord.Game("봇 로딩"),
            owner_id=610625541157945344,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            strip_after_prefix=True  # allows 'ㄲ ' prefix
        )
        self.koreanbots = None
        self.dbl = None
        self.db = db

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.update_presence, 'interval', minutes=1)
        self.scheduler.start()

    def setup_hook(self) -> None:
        self.koreanbots = DiscordpyKoreanbots(self, config("token.koreanbots"), run_task=not config("test"), include_shard_count=True)
        self.dbl = DBLClient(self, config("token.dbl"), autopost=not config("test"), post_shard_count=True)

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
        await self.change_presence(activity=discord.Game(f"ㄲ도움 | {len(self.guilds)} 서버에서 끝말잇기"))

    def reload_all(self):
        for cogname in os.listdir("cogs"):
            if cogname.endswith(".py"):
                self.try_reload(cogname[:-3])

    @staticmethod
    def dict_emojis():
        return {k: f"<:{k}:{v}>" for k, v in config('emojis').items()}

    async def if_koreanbots_voted(self, user: discord.User) -> bool:
        data = await Koreanbots().is_voted_bot(user.id, self.user.id)
        return data.voted


def command(name: str = None, cls: Type[commands.Command] = None, **attrs):
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


discord.Embed = KkutbotEmbed
