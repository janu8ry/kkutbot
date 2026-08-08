import time
from contextlib import asynccontextmanager

import discord
from discord.ext import commands

from core import Kkutbot
from database.models import User
from tools import fmt

from .ladder import get_difficulty_tier
from .models import ENTRY_FEE, MultiGame, SoloGame
from .views import HostGuildGame


class Game(commands.Cog, name="게임"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @staticmethod
    async def get_playable_user(ctx: commands.Context) -> User | None:
        user = await ctx.bot.db.get_user(ctx.author)
        if user.points < ENTRY_FEE:
            await ctx.reply(
                fmt(
                    f"{{denied}} 참가비 `{ENTRY_FEE}`{{points}}가 부족하여 플레이할 수 없습니다.\n"
                    "`/출석`, `/포인트`, `/퀘스트` 명령어를 사용해서 포인트를 획득해 보세요!"
                )
            )
            return None
        return user

    async def acquire_game(self, ctx: commands.Context) -> bool:
        if ctx.author.id in self.bot.playing_games:
            await ctx.reply(fmt("{denied} 이미 진행 중인 끝말잇기 게임이 있습니다."))
            return False
        self.bot.playing_games.add(ctx.author.id)
        return True

    @asynccontextmanager
    async def game_session(self, ctx: commands.Context):
        try:
            yield
        finally:
            self.bot.playing_games.discard(ctx.author.id)

    @commands.hybrid_command(name="끝말잇기", usage="📔", aliases=("ㄲ", "끝", "ㄲㅁㅇㄱ", "ㄲ1", "끝1", "ㄲㅁㅇㄱ1"))
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    async def play_solo(self, ctx: commands.Context):
        """
        끝말잇기 솔로 랭크 게임을 플레이합니다.

        게임을 플레이하려면 최소 30포인트가 필요합니다.

        --기본 규칙
        상대방이 제시한 단어의 마지막 글자로 시작하는 단어를 제시합니다.
        이를 계속 반복하다가 한쪽이 단어를 잇지 못하게 되면 상대방의 승리!
        첫 차례에 한방단어는 사용 불가합니다.
        이미 사용한 단어, 한글자 단어, 사전에 없는 단어는 사용할 수 없습니다.
        게임 도중에 "ㅈㅈ" 또는 "gg"를 입력하면 게임을 포기할 수 있습니다.

        --랭크 시스템
        티어는 언랭크부터 마스터까지 7개 티어로 나뉘며,
        각 티어는 다시 3개의 디비전(III → II → I)으로 세분화됩니다.
        처음 5판은 배치 고사로, 성적에 따라 시작 티어가 결정됩니다.
        승리시 LP를 얻고 패배하면 LP를 잃습니다.
        100LP에 도달하면 상위 티어로 승급,
        0LP에서 패배시 이전 티어로 강등됩니다.
        난이도는 티어에 맞춰 조정되어, 티어가 높을수록 강한 봇과 대결합니다!
        마스터 티어는 디비전 없이 LP가 누적되며, 이 LP로 순위가 매겨집니다.

        --포인트 획득 방식
        승리시에는 상대방과 플레이어가 주고받은 단어의 개수에 비례해
        포인트를 획득하고, 패배 또는 포기시에는 30포인트가 차감됩니다.

        --기타
        단어 목록: 표준국어대사전 기반, 단어수 약 31만개

        --사용법
        `/끝말잇기`를 사용하여 솔로 랭크 게임을 플레이합니다.
        `ㄲㄲ1`을 사용하여 바로 플레이 할 수 있습니다.
        """
        if not await self.acquire_game(ctx):
            return
        async with self.game_session(ctx):
            if (user := await self.get_playable_user(ctx)) is None:
                return
            game = SoloGame(ctx, kkd=False, tier=get_difficulty_tier(user.game.rank_solo), placement=user.game.rank_solo.tier == "언랭크")
            await game.run()

    @commands.hybrid_command(name="다인전", usage="{server}", aliases=("ㄲ2", "끝2", "ㄲㅁㅇㄱ2", "ㄷㅇㅈ", "멀티", "ㅁ"))
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def play_multi(self, ctx: commands.Context):
        """
        서버 멤버들과 끝말잇기 다인전 게임을 플레이합니다.

        기본 게임 규칙은 랭크 게임과 동일하지만,
        티어제와 LP 변동이 없는 친선전 모드입니다. 승패 부담 없이 즐겨보세요!
        최소 2인부터 최대 5인까지 플레이 가능합니다.

        --사용법
        `/다인전`을 사용하여 다인전 게임을 플레이합니다.
        `ㄲㄲ2`를 사용하여 바로 플레이 할 수 있습니다.
        """
        if not await self.acquire_game(ctx):
            return
        async with self.game_session(ctx):
            if await self.get_playable_user(ctx) is None:
                return
            if isinstance(ctx.channel, discord.DMChannel):
                raise commands.errors.NoPrivateMessage

            multi_game = MultiGame(ctx, hosting_time=round(time.time()))
            view = HostGuildGame(ctx, game=multi_game)
            view.message = await ctx.reply(embed=await multi_game.hosting_embed(), view=view)
            multi_game.msg = view.message
            try:
                await view.wait()
                if view.value == "stop":
                    return
                if view.value != "start":
                    if len(multi_game.players) < 2:
                        await ctx.channel.send(f"❌ 플레이어 수가 부족하여 **{multi_game.host.display_name}**님의 게임을 종료합니다.")
                        return
                    await ctx.channel.send(f"✅ 대기 시간이 초과되어 **{multi_game.host.display_name}**님의 게임을 시작합니다.")
                await multi_game.run()
            finally:
                for player in multi_game.players:
                    self.bot.playing_games.discard(player.id)

    @commands.hybrid_command(name="쿵쿵따", usage="3️⃣", aliases=("ㄲ3", "끝3", "ㄲㅁㅇㄱ3", "쿵"))
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    async def play_kkd(self, ctx: commands.Context):
        """
        끝말잇기 쿵쿵따 모드를 플레이합니다.

        기본 게임 규칙은 랭크 게임과 동일하지만,
        티어제와 LP 변동이 없는 자유 모드입니다.

        세글자 단어만 사용할 수 있습니다!

        --사용법
        `/쿵쿵따`를 사용하여 쿵쿵따 게임을 플레이합니다.
        `ㄲㄲ3`을 사용하여 바로 플레이 할 수 있습니다.
        """
        if not await self.acquire_game(ctx):
            return
        async with self.game_session(ctx):
            if await self.get_playable_user(ctx) is None:
                return
            game = SoloGame(ctx, kkd=True)
            await game.run()
