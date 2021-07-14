import re
import os.path

import discord
from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES
from jishaku.codeblocks import Codeblock, codeblock_converter
from discord.ext import commands
from jishaku.features.baseclass import Feature

import core


class CustomJSK(*STANDARD_FEATURES, OPTIONAL_FEATURES):
    """jishaku의 커스텀 확장 명령어들이 있는 카테고리입니다."""

    filepath_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")  # noqa

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
