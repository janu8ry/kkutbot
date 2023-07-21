import discord
from discord.ext import commands

from config import config
from core import Kkutbot, KkutbotContext

from .views import InviteMenu


class Invite(commands.Cog, name="초대"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="초대", usage="{invitation}", aliases=("링크", "ㅊㄷ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def kkutbot_invite(self, ctx: KkutbotContext):
        """
        끝봇과 서포트 서버의 초대링크를 확인합니다.

        --사용법
        `/초대`을 사용하여 끝봇의 초대링크와 서포트 서버의 초대링크를 확인합니다.
        """
        embed = discord.Embed(title="{invitation} 끝봇 초대하기",
                              description="끝봇을 사용하고 싶다면 아래 버튼을 클릭하여\n"
                                          "끝봇을 당신의 서버에 초대하세요!\n\n"
                                          "끝봇의 커뮤니티 서버에 참가하면 끝봇의 다양한 소식들을 빠르게 확인할 수 있습니다!\n\n"
                                          f"끝봇을 서버에 초대할 경우, [약관]({config.links.privacy_policy})에 동의한 것으로 간주됩니다.",
                              color=config.colors.general
                              )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed, view=InviteMenu())
