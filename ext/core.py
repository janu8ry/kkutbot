from typing import Type

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
        self.db = db  # mongoDB
        self.dblpy = dbl.DBLClient(self, config('token.dbl'), autopost=not config('test'))   # top.gg
        self.koreanbots = koreanbots.Client(self, config('token.koreanbots'), postCount=not config('test'))  # koreanbots
        self.uniquebots = UniqueBotsKR.client(self, config('token.uniquebots'), autopost=not config('test'))  # uniquebots
        self.webhook = Webhook.Async(config(f'webhook.{"test" if config("test") else "main"}'))  # logger webhook
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
        """|coro|

        Sends a message to the destination with the content given.

        The content must be a type that can convert to a string through ``str(content)``.
        If the content is set to ``None`` (the default), then the ``embed`` parameter must
        be provided.

        To upload a single file, the ``file`` parameter should be used with a
        single :class:`~discord.File` object. To upload multiple files, the ``files``
        parameter should be used with a :class:`list` of :class:`~discord.File` objects.
        **Specifying both parameters will lead to an exception**.

        If the ``embed`` parameter is provided, it must be of type :class:`~discord.Embed` and
        it must be a rich embed type.

        Parameters
        ------------
        content: :class:`str`
            The content of the message to send.
        tts: :class:`bool`
            Indicates if the message should be sent using text-to-speech.
        embed: :class:`~discord.Embed`
            The rich embed for the content.
        file: :class:`~discord.File`
            The file to upload.
        files: List[:class:`~discord.File`]
            A list of files to upload. Must be a maximum of 10.
        nonce: :class:`int`
            The nonce to use for sending this message. If the message was successfully sent,
            then the message will have a nonce with this value.
        delete_after: :class:`float`
            If provided, the number of seconds to wait in the background
            before deleting the message we just sent. If the deletion fails,
            then it is silently ignored.
        allowed_mentions: :class:`~discord.AllowedMentions`
            Controls the mentions being processed in this message. If this is
            passed, then the object is merged with :attr:`~discord.Client.allowed_mentions`.
            The merging behaviour only overrides attributes that have been explicitly passed
            to the object, otherwise it uses the attributes set in :attr:`~discord.Client.allowed_mentions`.
            If no object is passed at all then the defaults given by :attr:`~discord.Client.allowed_mentions`
            are used instead.

            .. versionadded:: 1.4

        reference: Union[:class:`~discord.Message`, :class:`~discord.MessageReference`]
            A reference to the :class:`~discord.Message` to which you are replying, this can be created using
            :meth:`~discord.Message.to_reference` or passed directly as a :class:`~discord.Message`. You can control
            whether this mentions the author of the referenced message using the :attr:`~discord.AllowedMentions.replied_user`
            attribute of ``allowed_mentions`` or by setting ``mention_author``.

            .. versionadded:: 1.6

        mention_author: Optional[:class:`bool`]
            If set, overrides the :attr:`~discord.AllowedMentions.replied_user` attribute of ``allowed_mentions``.

            .. versionadded:: 1.6

        escape_emoji_formatting: :class:`bool`
            If `False`, formats emoji name to custom emoji before sending message, if `True`, sends the raw string.

        Raises
        --------
        ~discord.HTTPException
            Sending the message failed.
        ~discord.Forbidden
            You do not have the proper permissions to send the message.
        ~discord.InvalidArgument
            The ``files`` list is not of the appropriate size,
            you specified both ``file`` and ``files``,
            or the ``reference`` object is not a :class:`~discord.Message`
            or :class:`~discord.MessageReference`.

        Returns
        ---------
        :class:`~discord.Message`
            The message that was sent."""
        if escape_emoji_formatting is False:
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

    async def reply(self, content=None, **kwargs):  # same as above
        content = content.format(**self.bot.emojis) if content else None
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
