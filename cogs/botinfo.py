import discord
from discord.ext import commands

from core import Kkutbot, KkutbotContext
from tools.config import config
from tools.views import BotInvite, HelpMenu, ServerInvite


class BotInfo(commands.Cog, name="일반"):
    """봇의 기본 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="도움", usage="ㄲ도움", aliases=("도움말", "help", "ㄷㅇ", "ㄷ", "정보", "봇정보", "ㅈㅂ"))
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def help(self, ctx: KkutbotContext):
        """끝봇의 명령어 목록을 확인합니다."""
        embed = discord.Embed(
            title="{help} 끝봇 도움말",
            description="끝봇은 끝말잇기가 주 기능인 디스코드 봇입니다!\n\n"
                        f"**개발자**: `{(await self.bot.application_info()).owner}`\n"
                        f"**서버 /사용자 수**: `{len(self.bot.guilds)}`개/`{await self.bot.db.user.count_documents({})}`명\n"
                        f"**업타임**: <t:{self.bot.started_at}:R>\n\n"
                        "개발에 도움을 주신 `서진#5826`님,\n프로필 사진을 만들어 주신 `! Tim23#1475` 님께 감사드립니다!\n"
                        "Icon made from [flaticon](https://www.flaticon.com)",
            color=config('colors.help')
        )
        embed.add_field(
            name="기타 링크",
            value=f"[웹사이트]({config('links.blog')})  [koreanbots]({config('links.koreanbots')})  [github]({config('links.github')})  [개인정보처리방침]({config('links.privacy-policy')})"
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="아래 메뉴를 클릭해서 명령어 도움말을 확인해 보세요!")
        view = HelpMenu(ctx=ctx, home_embed=embed)
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.command(name="초대", usage="ㄲ초대", aliases=("링크", "ㅊㄷ", "ㄹㅋ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def kkutbot_invite(self, ctx: KkutbotContext):
        """끝봇을 초대할 때 필요한 링크를 확인합니다."""
        embed = discord.Embed(title="{invitation}  끝봇 초대하기",
                              description="끝봇을 사용하고 싶다면 아래 버튼을 클릭하여\n"
                                          "끝봇을 당신의 서버에 초대하세요!\n\n"
                                          f"끝봇을 서버에 초대할 경우, [약관]({config('links.privacy-policy')})에 동의한 것으로 간주됩니다.",
                              color=config('colors.general')
                              )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed, view=BotInvite())

    @commands.command(name="커뮤니티", usage="ㄲ커뮤니티", aliases=("지원", "서버", "디스코드", "디코", "ㅋㅁㄴㅌ", "ㄷㅋ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def community_invite(self, ctx: KkutbotContext):
        """끝봇 공식 커뮤니티에 참가하기 위한 초대장을 확인합니다."""
        embed = discord.Embed(title="{invitation} 끝봇 커뮤니티 참가하기",
                              description="끝봇 커뮤니티에 참가하여, \n"
                                          "주요 공지사항을 확인하고, 건의사항이나 버그를 제보하고,\n"
                                          "다른 유저들과 교류해 보세요!",
                              color=config('colors.general')
                              )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed, view=ServerInvite())


async def setup(bot: Kkutbot):
    await bot.add_cog(BotInfo(bot))
