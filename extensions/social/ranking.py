from discord.ext import commands

from core import Kkutbot, KkutbotContext

from .views import RankMenu


class Ranking(commands.Cog, name="랭킹"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="랭킹", usage="<:ranking:985439871004995634>", aliases=("ㄹ", "리더보드", "순위", "ㄹㅋ"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def ranking(self, ctx: KkutbotContext):
        """
        여러 분야의 랭킹을 확인합니다.

        끝말잇기 랭킹의 경우, 랭킹에 등재되려면 해당 모드를
        30회 이상 플레이 해야 합니다.

        --분야
        - 일반: 포인트, 메달, 출석 횟수, 명령어 사용 횟수
        - 끝말잇기: 솔로 모드, 쿵쿵따 모드

        --사용법
        `/랭킹`을 사용하여 전체 분야의 Top5 랭킹을 확인합니다.
        이후 아래 메뉴를 통해 특정 분야의 Top 15 랭킹을 확인합니다.
        """
        view = RankMenu(ctx)
        view.message = await ctx.reply(embed=await view.get_home_embed(), view=view)
