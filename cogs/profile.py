from datetime import datetime

import discord
from discord.ext import commands
from discord.utils import escape_markdown as e_mk

from core import Kkutbot, KkutbotContext
from tools.config import config
from tools.converter import KkutbotUserConverter
from tools.db import read
from tools.utils import get_tier, get_winrate
from tools.views import InfoEdit


class Profile(commands.Cog, name="사용자"):
    """사용자의 프로필에 관련된 명령어들입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="프로필", usage="ㄲ프로필 <유저>", aliases=("ㅍ", "ㅍㄹㅍ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.bot_has_permissions(external_emojis=True)
    async def profile(self, ctx: KkutbotContext, *, user: KkutbotUserConverter()):  # noqa
        """대상의 티어, 포인트, 승률 등의 프로필을 확인합니다.
        자신의 프로필을 확인한 경우, 아래 버튼을 눌러 소개말을 변경할 수 있습니다!

        <예시>
        ㄲ프로필 - 자신의 프로필을 확인합니다.
        ㄲ프로필 @가나다 - '가나다'의 프로필을 확인합니다.
        """
        embed = discord.Embed(
            title=f"{{profile}} {e_mk(str(user))}",
            description=f"```yaml\n{await read(user, 'info')}```\n"
                        f":star: 현 시즌 티어 - **{await get_tier(user, 'rank_solo')}** | **{await get_tier(user, 'rank_online')}**\n​",
            color=config('colors.general')
        )
        embed.add_field(name="{points} **포인트**", value=f"{await read(user, 'points')}")
        embed.add_field(name="{starter} **승률**", value=f"{await get_winrate(user, 'rank_solo')}% | {await get_winrate(user, 'rank_online')}%")
        embed.add_field(name="{medals} **메달**", value=f"{await read(user, 'medals')}")
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"더 자세한 정보는 'ㄲ통계' 명령어로 확인할 수 있어요!{' ' * 83}​")
        if user.id == ctx.author.id:
            view = InfoEdit(ctx)
            view.message = await ctx.reply(embed=embed, view=view)
        else:
            await ctx.reply(embed=embed)

    @commands.command(name="통계", usage="ㄲ통계 <유저>", aliases=("상세정보", "ㅌ", "ㅌㄱ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def stats(self, ctx: KkutbotContext, *, user: KkutbotUserConverter()):  # noqa
        """대상의 자세한 통계를 확인합니다.

        <예시>
        ㄲ통계 - 자신의 통계를 확인합니다.
        ㄲ통계 @가나다 - 가나다의 통계를 확인합니다.
        """
        embed = discord.Embed(
            title=f"{{stats}} {e_mk(str(user))} 님의 통계",
            description=f"가입일 : `{str(await read(user, 'registered'))[:10]}`\n"
                        f"마지막 사용일 : `{str(datetime.fromtimestamp(await read(user, 'latest_usage')))[:10]}`",
            color=config('colors.general')
        )

        for k, v in config('modelist').items():
            embed.add_field(name=f"🔸 {k}",
                            value=f"`{await read(user, f'game.{v}.win')}` / `{await read(user, f'game.{v}.times')}`회 승리 "
                                  f"(`{await read(user, f'game.{v}.winrate')}%`)\n"
                                  f"최고 점수 : `{await read(user, f'game.{v}.best')}`"
                            )
        embed.add_field(
            name="🔸 기타", value=f"출석 횟수 : `{await read(user, 'attendance_times')}`\n명령어 사용 횟수 : `{await read(user, 'command_used')}`"
        )
        embed.set_footer(text=f"티어 정보는 웹사이트에서 확인할 수 있어요.{' ' * 100}​​​")
        await ctx.reply(embed=embed)


async def setup(bot: Kkutbot):
    await bot.add_cog(Profile(bot))
