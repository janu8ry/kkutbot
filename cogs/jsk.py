from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature

from ext.core import Kkutbot, KkutbotContext


class CustomJSK(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """jishaku의 커스텀 확장 명령어들이 있는 카테고리입니다."""

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


def setup(bot: Kkutbot):
    bot.add_cog(CustomJSK(bot=bot))
