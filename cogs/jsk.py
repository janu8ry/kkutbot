import itertools
import logging
import os.path
import re
import sys
import traceback
import typing

import discord
import jishaku.repl.repl_builtins
import psutil
from discord.ext import commands
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.features.root_command import natural_size
from jishaku.flags import Flags
from jishaku.functools import AsyncSender
from jishaku.modules import ExtensionConverter, package_version
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.repl import AsyncCodeExecutor
from jishaku.shell import ShellReader
from jishaku.types import ContextA

try:
    from importlib.metadata import distribution, packages_distributions
except ImportError:
    from importlib_metadata import distribution, packages_distributions

import core
from tools.config import config
from tools.db import db, read, write

logger = logging.getLogger("kkutbot")

Flags.NO_UNDERSCORE = True
Flags.FORCE_PAGINATOR = True


def get_var_dict_from_ctx(ctx: commands.Context, prefix: str = "_"):
    """
    Returns the dict to be used in REPL for a given Context.
    """

    raw_var_dict = {
        "author": ctx.author,
        "bot": ctx.bot,
        "channel": ctx.channel,
        "ctx": ctx,
        "find": discord.utils.find,
        "get": discord.utils.get,
        "guild": ctx.guild,
        "http_get_bytes": jishaku.repl.repl_builtins.http_get_bytes,
        "http_get_json": jishaku.repl.repl_builtins.http_get_json,
        "http_post_bytes": jishaku.repl.repl_builtins.http_post_bytes,
        "http_post_json": jishaku.repl.repl_builtins.http_post_json,
        "message": ctx.message,
        "msg": ctx.message,
        "db": db,
        "read": read,
        "write": write,
        "config": config,
        "logger": logger
    }

    return {f"{prefix}{k}": v for k, v in raw_var_dict.items()}


class CustomJSK(*STANDARD_FEATURES, *OPTIONAL_FEATURES, name="지샤쿠"):
    """jishaku의 커스텀 확장 명령어들이 있는 카테고리입니다."""

    filepath_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")  # noqa

    @Feature.Command(name="jishaku", aliases=["ㅈ", "jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: ContextA):
        """
        The Jishaku debug and diagnostic commands.
        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """

        # Try to locate what vends the `discord` package
        distributions: typing.List[str] = [
            dist for dist in packages_distributions()['discord']  # type: ignore
            if any(
                file.parts == ('discord', '__init__.py')  # type: ignore
                for file in distribution(dist).files  # type: ignore
            )
        ]

        if distributions:
            dist_version = f'{distributions[0]} `{package_version(distributions[0])}`'
        else:
            dist_version = f'unknown `{discord.__version__}`'

        summary = [
            f"Jishaku `{package_version('jishaku')}`",
            f"{dist_version}",
            f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
            f"봇은 <t:{self.load_time.timestamp():.0f}:R>에 로딩되었고, "
            f"카테고리는 <t:{self.start_time.timestamp():.0f}:R>에 로딩되었습니다.",
            ""
        ]

        try:
            proc = psutil.Process()

            with proc.oneshot():
                try:
                    mem = proc.memory_full_info()
                    summary.append(f"`{natural_size(mem.rss)}`의 물리적 메모리와 "
                                   f"`{natural_size(mem.vms)}`의 가상 메모리, "
                                   f"`{natural_size(mem.uss)}`의 고유 메모리를 사용하고 있습니다.")
                except psutil.AccessDenied:
                    pass

                try:
                    name = proc.name()
                    pid = proc.pid
                    thread_count = proc.num_threads()

                    summary.append(f"PID {pid} (`{name}`) 에서 `{thread_count}` 개의 스레드에서 작동중입니다.")
                except psutil.AccessDenied:
                    pass

                summary.append("")  # blank line
        except psutil.AccessDenied:
            summary.append("psutil이 설치되어 있지만, 권한이 부족하여 기능을 사용할 수 없습니다.")
            summary.append("")  # blank line

        cache_summary = f"`{len(self.bot.guilds)}`개의 서버와 `{await self.bot.db.user.count_documents({})}`명의 사용자"

        if len(self.bot.shards) > 20:
            summary.append(
                f"This bot is automatically sharded ({len(self.bot.shards)} shards of {self.bot.shard_count})"
                f" and can see {cache_summary}."
            )
        else:
            summary.append(
                f"샤드 수는 `{self.bot.shard_count}`개이며,"
                f" {cache_summary}와 활동하고 있습니다."
            )

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:  # noqa
            message_cache = f"메시지 캐시가 `{self.bot._connection.max_messages}`(으)로 제한되어있습니다."  # noqa
        else:
            message_cache = "메시지 캐시가 비활성화 되어있습니다."

        remarks = {
            True: 'enabled',
            False: 'disabled',
            None: 'unknown'
        }

        *group, last = (
            f"{intent.replace('_', ' ')} 인텐트: `{'활성화' if remarks.get(getattr(self.bot.intents, intent, None)) == 'enabled' else '비활성화'}`"
            for intent in
            ('presences', 'members', 'message_content')
        )

        summary.append(message_cache)
        summary.append(f"{', '.join(group)}, {last}.")
        summary.append("")  # blank line

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        summary.append(f"평균 웹소켓 지연시간: `{round(self.bot.latency * 1000, 2)}`ms")

        await ctx.send("\n".join(summary))

    @Feature.Command(parent="jsk", name="shell", aliases=["bash", "sh", "powershell", "ps1", "ps", "cmd", "terminal", "실행", "ㅅ"])
    async def jsk_shell(self, ctx: ContextA, *, argument: codeblock_converter):  # type: ignore
        """
        Executes statements in the system shell.
        This uses the system shell as defined in $SHELL, or `/bin/bash` otherwise.
        Execution can be cancelled by closing the paginator.
        """

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                with ShellReader(argument.content, escape_ansi=not Flags.use_ansi(ctx)) as reader:
                    prefix = "```" + reader.highlight

                    paginator = WrappedPaginator(prefix=prefix, max_size=1975)
                    paginator.add_line(f"{reader.ps1} {argument.content}\n")

                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                    self.bot.loop.create_task(interface.send_to(ctx))

                    async for line in reader:
                        if interface.closed:
                            return
                        await interface.add_line(line)

                await interface.add_line(f"\n[status] Return code {reader.close_code}")

    @Feature.Command(parent="jsk", name="poetry", aliases=["ㅍㅌ"])
    async def jsk_pip(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for "jsk sh poetry". Invokes the system shell.
        """
        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        return await ctx.invoke(self.jsk_shell, argument=Codeblock(argument.language, "poetry " + argument.content))  # type: ignore

    @Feature.Command(parent="jsk", name="docker")
    async def jsk_docker(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for "jsk sh docker". Invokes the system shell.
        """
        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        return await ctx.invoke(self.jsk_shell, argument=Codeblock(argument.language, "docker " + argument.content))  # type: ignore

    @Feature.Command(parent="jsk", name="file", aliases=["파일", "ㅍㅇ"])
    async def jsk_file(self, ctx: commands.Context, path: str):
        """
        Sends local file to discord channel.
        """
        match = self.filepath_regex.search(path)

        if not match:  # should never happen
            return await ctx.send("파일 경로가 정확하지 않습니다.")

        if not os.path.exists(path) or os.path.isdir(path):
            return await ctx.send(f"`{path}`: 파일을 찾지 못했습니다.")

        size = os.path.getsize(path)

        if size <= 0:
            return await ctx.send(f"`{path}`: 크기가 0인 파일을 읽을 수 없습니다."
                                  f" (파일이 비어있거나, 접근 불가능할 수 있습니다.).")

        if size > 128 * (1024 ** 2):
            return await ctx.send(f"`{path}`: 파일의 용량이 128MB를 초과하여 전송할 수 없습니다.")

        return await ctx.send(file=discord.File(path))

    @Feature.Command(parent="jsk", name="py", aliases=["python", "ㅍ"])
    async def jsk_python(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Direct evaluation of Python code.
        """

        if typing.TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore

        arg_dict = get_var_dict_from_ctx(ctx, Flags.SCOPE_PREFIX)
        arg_dict["_"] = self.last_result

        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):  # type: ignore
                        send: typing.Callable[..., None]
                        result: typing.Any

                        if result is None:
                            continue

                        self.last_result = result  # noqa

                        send(await self.jsk_python_result_handling(ctx, result))

        finally:
            scope.clear_intersection(arg_dict)

    @Feature.Command(parent="jsk", name="load", aliases=["reload", "ㄹ"])
    async def jsk_load(self, ctx: ContextA, *extensions: ExtensionConverter):  # type: ignore
        """
        Loads or reloads the given extension names.
        Reports any extensions that failed to load.
        """

        extensions: typing.Iterable[typing.List[str]] = extensions  # type: ignore

        paginator = commands.Paginator(prefix='', suffix='')

        # 'jsk reload' on its own just reloads jishaku
        if ctx.invoked_with == 'reload' and not extensions:
            extensions = [['cogs.jsk']]
        elif ctx.invoked_with == 'ㄹ' and not extensions:
            extensions = [[f"cogs.{cogname[:-3]}" for cogname in os.listdir("cogs") if cogname.endswith(".py")]]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            await discord.utils.maybe_coroutine(method, extension)
            logger.info(f"카테고리 '{extension}'을(를) 불러왔습니다!")

            try:
                await discord.utils.maybe_coroutine(method, extension)
                logger.info(f"카테고리 '{extension}'을(를) 불러왔습니다!")
            except Exception as exc:  # pylint: disable=broad-except
                traceback_data = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```",
                    empty=True
                )
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.send(page)

    @Feature.Command(parent="jsk", name="shutdown", aliases=["logout", "종료", "로그아웃", "ㅈㄹ"])
    async def jsk_shutdown(self, ctx: ContextA):
        """
        Logs this bot out.
        """

        ellipse_character = "\N{BRAILLE PATTERN DOTS-356}" if Flags.USE_BRAILLE_J else "\N{HORIZONTAL ELLIPSIS}"

        await ctx.send(f"로그아웃합니다{ellipse_character}")
        logger.info("봇이 정상적으로 종료되었습니다!")
        await ctx.bot.close()


async def setup(bot: core.Kkutbot):
    await bot.add_cog(CustomJSK(bot=bot))
