import discord
from discord.ext import commands

from config import config
from core import Kkutbot
from database.models import User
from tools import fmt

from .views import HelpMenu


class Help(commands.Cog, name="일반"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="도움", usage="{help}", aliases=("도움말", "help", "ㄷㅇ", "ㄷ", "정보", "봇정보", "ㅈㅂ"))
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def help(self, ctx: commands.Context):
        """
        끝봇의 명령어 목록을 확인합니다.

        --사용법
        `/도움`을 사용하여 도움말을 확인합니다.
        """
        embed = discord.Embed(
            title=fmt("{help} 끝봇 도움말"),
            description="🔸 끝봇은 끝말잇기가 주 기능인 디스코드 봇입니다!\n\n"
            f"🔹 **개발자**: `{(await self.bot.application_info()).team.owner}`\n"
            f"🔹 **서버 / 사용자 수**: `{len(self.bot.guilds)}`개 / `{await User.count()}`명\n"
            f"🔹 **업타임**: ~ <t:{self.bot.started_at}:R>부터\n\n"
            "개발에 도움을 주신 `seojin_park`님,\n프로필 사진을 만들어 주신 `! Tim23#1475` 님께 감사드립니다!\n"
            "Icon made from [flaticon](https://www.flaticon.com)",
            color=config.colors.help,
        )
        embed.add_field(
            name="🔹 기타 링크",
            value=f"[웹사이트]({config.links.website}) | [Koreanbots]({config.links.koreanbots}) | [Github]({config.links.github}) | [개인정보처리방침]({config.links.privacy_policy})",
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="아래 메뉴를 클릭해서 명령어 도움말을 확인해 보세요!")
        view = HelpMenu(ctx=ctx, home_embed=embed)
        view.message = await ctx.reply(embed=embed, view=view)
