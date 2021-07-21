import io
import itertools
import logging
import os.path
import re
import sys
import traceback

import discord
import jishaku.repl.repl_builtins
import psutil
from discord.ext import commands
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.features.root_command import natural_size
from jishaku.flags import (JISHAKU_FORCE_PAGINATOR, JISHAKU_USE_BRAILLE_J,
                           SCOPE_PREFIX)
from jishaku.functools import AsyncSender
from jishaku.modules import ExtensionConverter, package_version
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.repl import AsyncCodeExecutor

import core
from tools.config import config
from tools.db import db, read, write

logger = logging.getLogger("kkutbot")


def get_var_dict_from_ctx(ctx: commands.Context, prefix: str = '_'):
    """
    Returns the dict to be used in REPL for a given Context.
    """

    raw_var_dict = {
        'author': ctx.author,
        'bot': ctx.bot,
        'channel': ctx.channel,
        'ctx': ctx,
        'find': discord.utils.find,
        'get': discord.utils.get,
        'guild': ctx.guild,
        'http_get_bytes': jishaku.repl.repl_builtins.http_get_bytes,
        'http_get_json': jishaku.repl.repl_builtins.http_get_json,
        'http_post_bytes': jishaku.repl.repl_builtins.http_post_bytes,
        'http_post_json': jishaku.repl.repl_builtins.http_post_json,
        'message': ctx.message,
        'msg': ctx.message,
        'db': db,
        'read': read,
        'write': write,
        'config': config
    }

    return {f'{prefix}{k}': v for k, v in raw_var_dict.items()}


class CustomJSK(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """jishaku의 커스텀 확장 명령어들이 있는 카테고리입니다."""

    filepath_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")  # noqa

    @Feature.Command(name="jishaku", aliases=["ㅈ", "jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: commands.Context):
        """
            The Jishaku debug and diagnostic commands.

            This command on its own gives a status brief.
            All other functionality is within its subcommands.
        """

        summary = [
            f"Jishaku `{package_version('jishaku')}`, discord.py `{package_version('discord.py')}`\n",
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

                    summary.append(f"PID {pid} (`{name}`) 에서 {thread_count}개의 스레드로 실행중입니다.")
                except psutil.AccessDenied:
                    pass

                summary.append("")  # blank line
        except psutil.AccessDenied:
            summary.append(
                "psutil이 설치되어 있지만, 권한이 부족하여 기능을 사용할 수 없습니다."
            )
            summary.append("")  # blank line

        cache_summary = f"{len(self.bot.guilds)}개의 서버와 {await self.bot.db.user.count_documents({})}명의 사용자"

        # Show shard settings to summary
        if len(self.bot.shards) > 20:
            summary.append(
                f"This bot is automatically sharded ({len(self.bot.shards)} shards of {self.bot.shard_count})"
                f" and can see {cache_summary}."
            )
        else:
            summary.append(
                f"샤드 수는 {self.bot.shard_count}개이며,"
                f" {cache_summary}와 활동하고 있습니다."
            )

        # Show websocket latency in milliseconds
        summary.append(f"평균 웹소켓 핑: {round(self.bot.latency * 1000, 2)}ms")

        await ctx.send("\n".join(summary))

    @Feature.Command(parent="jsk", name="pip")
    async def jsk_pip(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh pip3'. Invokes the system shell.
        """

        return await ctx.invoke(self.jsk_shell, argument=Codeblock(argument.language, "pip3 " + argument.content))

    @Feature.Command(parent="jsk", name="docker")
    async def jsk_docker(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh docker'. Invokes the system shell.
        """

        return await ctx.invoke(
            self.jsk_shell, argument=Codeblock(argument.language, "docker " + argument.content)
        )

    @Feature.Command(parent="jsk", name="file")
    async def jsk_file(self, ctx: commands.Context, path: str):
        """
        Sends local file to discord channel.
        """
        match = self.filepath_regex.search(path)

        if not match:  # should never happen
            return await ctx.send("Couldn't parse this input.")

        if not os.path.exists(path) or os.path.isdir(path):
            return await ctx.send(f"`{path}`: No file by that name.")

        size = os.path.getsize(path)

        if size <= 0:
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file with no size stat"
                                  f" (it may be empty, endless or inaccessible).")

        if size > 128 * (1024 ** 2):
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file >128MB.")

        return await ctx.send(file=discord.File(path))

    @Feature.Command(parent="jsk", name="py", aliases=["python", "ㅍ"])
    async def jsk_python(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Direct evaluation of Python code.
        """

        arg_dict = get_var_dict_from_ctx(ctx, SCOPE_PREFIX)
        arg_dict["_"] = self.last_result

        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):
                        if result is None:
                            continue

                        self.last_result = result  # noqa

                        if isinstance(result, discord.File):
                            send(await ctx.send(file=result))
                        elif isinstance(result, discord.Embed):
                            send(await ctx.send(embed=result))
                        elif isinstance(result, PaginatorInterface):
                            send(await result.send_to(ctx))
                        else:
                            if not isinstance(result, str):
                                # repr all non-strings
                                result = repr(result)

                            if len(result) <= 2000:
                                if result.strip() == '':
                                    result = "\u200b"

                                send(await ctx.send(result.replace(self.bot.http.token, "[token omitted]")))

                            elif len(result) < 50_000 and not ctx.author.is_on_mobile() and not JISHAKU_FORCE_PAGINATOR:  # File "full content" preview limit
                                # Discord's desktop and web client now supports an interactive file content
                                #  display for files encoded in UTF-8.
                                # Since this avoids escape issues and is more intuitive than pagination for
                                #  long results, it will now be prioritized over PaginatorInterface if the
                                #  resultant content is below the filesize threshold
                                send(await ctx.send(file=discord.File(
                                    filename="output.py",
                                    fp=io.BytesIO(result.encode('utf-8'))
                                )))

                            else:
                                # inconsistency here, results get wrapped in codeblocks when they are too large
                                #  but don't if they're not. probably not that bad, but noting for later review
                                paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

                                paginator.add_line(result)

                                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                                send(await interface.send_to(ctx))

        finally:
            scope.clear_intersection(arg_dict)

    @Feature.Command(parent="jsk", name="load", aliases=["reload", "ㄹ"])
    async def jsk_load(self, ctx: commands.Context, *extensions: ExtensionConverter):
        """
        Loads or reloads the given extension names.

        Reports any extensions that failed to load.
        """

        paginator = WrappedPaginator(prefix='', suffix='')

        # 'jsk reload' on its own just reloads jishaku
        if ctx.invoked_with == 'reload' and not extensions:
            extensions = [['jishaku']]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.reload_extension, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions else
                (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                method(extension)
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

    @Feature.Command(parent="jsk", name="shutdown", aliases=["logout", "ㅈ"])
    async def jsk_shutdown(self, ctx: commands.Context):
        """
        Logs this bot out.
        """

        ellipse_character = "\N{BRAILLE PATTERN DOTS-356}" if JISHAKU_USE_BRAILLE_J else "\N{HORIZONTAL ELLIPSIS}"

        await ctx.send(f"Logging out now{ellipse_character}")
        logger.info("봇이 정상적으로 종료되었습니다!")
        await ctx.bot.close()


def setup(bot: core.Kkutbot):
    bot.add_cog(CustomJSK(bot=bot))
