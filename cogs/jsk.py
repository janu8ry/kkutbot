import asyncio
import io
import os
import re

import discord
from discord.ext import commands
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.flags import SCOPE_PREFIX
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedFilePaginator, WrappedPaginator
from jishaku.repl import AsyncCodeExecutor
from jishaku.repl.repl_builtins import (http_get_bytes, http_get_json,
                                        http_post_bytes, http_post_json)

from ext.core import Kkutbot
from ext.db import add, db, read, read_hanmaru, write


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
        'http_get_bytes': http_get_bytes,
        'http_get_json': http_get_json,
        'http_post_bytes': http_post_bytes,
        'http_post_json': http_post_json,
        'message': ctx.message,
        'msg': ctx.message,
        'discord': discord,
        'asyncio': asyncio,
        'db': db,
        'read': read,
        'write': write,
        'add': add,
        'read_hanmaru': read_hanmaru
    }

    return {f'{prefix}{k}': v for k, v in raw_var_dict.items()}


class CustomJSK(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """jishaku의 커스텀 확장 명령어들이 있는 카테고리입니다."""

    filepath_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")  # noqa

    @Feature.Command(parent="jsk", name="poetry")
    async def jsk_poetry(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh poetry'. Invokes the system shell.
        """

        return await ctx.invoke(
            self.jsk_shell, argument=Codeblock(argument.language, "poetry " + argument.content)
        )

    @Feature.Command(parent="jsk", name="pyenv")
    async def jsk_pyenv(self, ctx: commands.Context, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh pyenv'. Invokes the system shell.
        """

        return await ctx.invoke(
            self.jsk_shell, argument=Codeblock(argument.language, "pyenv " + argument.content)
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

    @Feature.Command(parent="jsk", name="py", aliases=["python"])
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

                            elif len(result) < 50_000:  # File "full content" preview limit
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

    @Feature.Command(parent="jsk", name="cat")
    async def jsk_cat(self, ctx: commands.Context, argument: str):  # pylint: disable=too-many-locals
        """
        Read out a file, using syntax highlighting if detected.
        Lines and linespans are supported by adding '#L12' or '#L12-14' etc to the end of the filename.
        """

        match = self.filepath_regex.search(argument)

        if not match:  # should never happen
            return await ctx.send("Couldn't parse this input.")

        path = match.group(1)

        line_span = None

        if match.group(2):
            start = int(match.group(2))
            line_span = (start, int(match.group(3) or start))

        if not os.path.exists(path) or os.path.isdir(path):
            return await ctx.send(f"`{path}`: No file by that name.")

        size = os.path.getsize(path)

        if size <= 0:
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file with no size stat"
                                  f" (it may be empty, endless or inaccessible).")

        if size > 128 * (1024 ** 2):
            return await ctx.send(f"`{path}`: Cowardly refusing to read a file >128MB.")

        try:
            with open(path, "rb") as file:
                paginator = WrappedFilePaginator(file, line_span=line_span, max_size=1985)
                interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                await interface.send_to(ctx)
        except UnicodeDecodeError:
            return await ctx.send(f"`{path}`: Couldn't determine the encoding of this file.")
        except ValueError as exc:
            return await ctx.send(f"`{path}`: Couldn't read this file, {exc}")


def setup(bot: Kkutbot):
    bot.add_cog(CustomJSK(bot=bot))
