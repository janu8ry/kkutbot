import os
import re

import discord
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature

from ext.core import Kkutbot, KkutbotContext


class CustomJSK(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """jishaku의 커스텀 확장 명령어들이 있는 카테고리입니다."""

    filepath_regex = re.compile(r"(?:\.\/+)?(.+?)(?:#L?(\d+)(?:\-L?(\d+))?)?$")

    @Feature.Command(parent="jsk", name="poetry")
    async def jsk_poetry(self, ctx: KkutbotContext, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh poetry'. Invokes the system shell.
        """

        return await ctx.invoke(
            self.jsk_shell, argument=Codeblock(argument.language, "poetry " + argument.content)
        )

    @Feature.Command(parent="jsk", name="pyenv")
    async def jsk_pyenv(self, ctx: KkutbotContext, *, argument: codeblock_converter):
        """
        Shortcut for 'jsk sh pyenv'. Invokes the system shell.
        """

        return await ctx.invoke(
            self.jsk_shell, argument=Codeblock(argument.language, "pyenv " + argument.content)
        )

    @Feature.Command(parent="jsk", name="file")
    async def jsk_file(self, ctx: KkutbotContext, path: str):
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


def setup(bot: Kkutbot):
    bot.add_cog(CustomJSK(bot=bot))
