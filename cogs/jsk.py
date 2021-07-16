import os.path
import re
import sys

import discord
import jishaku.repl.repl_builtins
import psutil
from discord.ext import commands
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature
from jishaku.features.root_command import natural_size
from jishaku.modules import package_version

import core
from tools.config import config
from tools.db import db, read, write


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


def setup(bot: core.Kkutbot):
    bot.add_cog(CustomJSK(bot=bot))
