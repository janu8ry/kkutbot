import asyncio
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from config import config
from core import Kkutbot
from tools import fmt

from .models import MultiGame, SoloGame
from .utils import get_transition, get_word, is_hanbang
from .views import HostGuildGame, SelectMode


class Game(commands.Cog, name="게임"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="끝말잇기", usage="📔", aliases=("ㄲ", "끝", "ㄲㅁㅇㄱ"))
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @app_commands.describe(mode="플레이 할 게임 모드를 선택합니다.")
    @app_commands.rename(mode="모드")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="솔로 랭킹전", value=1),
            app_commands.Choice(name="서버원들과 친선전", value=2),
            app_commands.Choice(name="쿵쿵따", value=3),
        ]
    )
    async def game(self, ctx: commands.Context, mode: app_commands.Choice[int] = None):
        """
        끝말잇기 게임을 플레이합니다.

        --게임 방법
        서로 번갈아가며 상대방이 마지막에 제시한 단어의 마지막 글자로 시작하는 단어를 제시합니다.
        이를 계속 반복하다가 어느 한쪽이 단어를 잇지 못하게 되면 상대방의 승리!
        첫 차례에 한방단어는 사용 불가합니다.
        이미 사용한 단어, 한글자 단어, 사전에 없는 단어는 사용 불가능합니다.

        게임 도중에 "ㅈㅈ" 또는 "gg"를 입력하면 게임을 포기할 수 있습니다.
        (*주의: 포기시 해당 게임은 패배로 처리됩니다.*)

        --점수 계산 방식
        승리시에는 상대방과 플레이어가 주고받은 단어의 개수에 비례해 포인트를 획득하고,
        패배 또는 포기시에는 30포인트가 차감됩니다.

        --기타
        단어DB 출처 : 표준국어대사전, 단어수 약 31만개
        티어 정보 확인 : [홈페이지](https://kkutbot.github.io/blog/끝말잇기-티어-정보)

        --게임 모드
        :one: 솔로 랭킹전
        -끝봇과 끝말잇기 대결을 합니다.

        :two: 서버원들과 친선전
        -같은 서버에 있는 유저들 여러 명과 끝말잇기 대결을 합니다.

        :three: 쿵쿵따
        -끝봇과 끝말잇기 대결을 합니다. 하지만 세글자 단어만 사용 가능합니다.

        3종류의 모드를 추가로 개발중입니다...

        --사용법
        `/끝말잇기`를 사용하여 원하는 게임 모드를 선택 후 플레이합니다.
        `/끝말잇기 <모드>`를 사용하여 원하는 게임 모드를 바로 플레이합니다.
        """

        def check(x: discord.Message | commands.Context) -> bool:
            return x.author == ctx.author and x.channel == ctx.channel

        user = await ctx.bot.db.get_user(ctx.author)
        if user.points <= 30:
            return await ctx.reply(
                fmt("{denyed} 포인트가 30점 미만이라 플레이할 수 없습니다.\n`/출석`, `/포인트`, `/퀘스트` 명령어를 사용해서 포인트를 획득해 보세요!")
            )
        if mode is None:
            embed = discord.Embed(title="📔 끝말잇기", description="🔸 끝말잇기 게임의 모드를 선택해 주세요.", color=config.colors.general)
            embed.add_field(name=":one:", value="- 솔로 랭킹전", inline=False)
            embed.add_field(name=":two:", value="- 서버원들과 친선전", inline=False)
            embed.add_field(name=":three:", value="- 쿵쿵따", inline=False)
            embed.set_footer(text="'/도움'을 사용하여 자세한 도움말을 확인해 보세요!")
            view = SelectMode(ctx)
            view.message = await ctx.reply(embed=embed, view=view)
            await view.wait()
            mode = view.value
        else:
            mode = mode.value
            if not (1 <= mode <= 3):
                return await ctx.reply(fmt("{denyed} 존재하지 않는 모드입니다."))

        if mode in (1, 3):
            is_kkd = mode == 3
            game = SoloGame(ctx, kkd=is_kkd)
            await game.send_info_embed(ctx)
            while True:
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=game.time_left)
                    user_word = msg.content
                except asyncio.TimeoutError:
                    await game.game_end("패배")
                    return
                else:
                    du = get_transition(game.bot_word)
                    if user_word in ("ㅈㅈ", "gg", "GG"):
                        if len(game.used_words) < 10:
                            await game.send_info_embed(msg, "{denyed} 5턴 이상 진행해야 포기할 수 있습니다.")
                            continue
                        else:
                            await game.game_end("포기")
                            return
                    elif user_word in game.used_words:
                        await game.send_info_embed(msg, f"{{denyed}} **{user_word}** (은)는 이미 사용한 단어입니다.")
                        continue
                    elif user_word[0] not in du:
                        await game.send_info_embed(msg, f"{{denyed}} **{'** 또는 **'.join(du)}** (으)로 시작하는 단어를 입력해 주세요.")
                        continue
                    elif len(user_word) != 3 and is_kkd:
                        await game.send_info_embed(msg, "{denyed} 세글자 단어만 사용 가능합니다.")
                        continue
                    elif user_word in get_word(game.bot_word):
                        if (game.score == 0) and is_hanbang(user_word, game.used_words, kkd=is_kkd):
                            await game.send_info_embed(msg, "{denyed} 첫번째 회차에서는 한방단어를 사용할 수 없습니다.")
                            continue
                        elif user_word[0] in du:
                            game.used_words.append(user_word)
                            game.score += 1
                    else:
                        await game.send_info_embed(msg, f"{{denyed}} **{user_word}** (은)는 없는 단어입니다.")
                        continue
                final_list = [x for x in get_word(user_word) if x not in game.used_words and (len(x) == 3 if is_kkd else True)]
                if not final_list:
                    await game.game_end("승리")
                    return
                else:
                    game.bot_word = random.choice(final_list)
                    game.used_words.append(game.bot_word)
                    game.begin_time = time.time()
                    game.score += 1
                    if is_hanbang(game.bot_word, game.used_words, kkd=is_kkd):
                        await game.game_end("패배")
                        return
                    else:
                        await game.send_info_embed(msg)

        elif mode == 2:
            if isinstance(ctx.channel, discord.DMChannel):
                raise commands.errors.NoPrivateMessage
            if ctx.channel.id in self.bot.guild_multi_games:
                return await ctx.reply(fmt("{denyed} 이 끝말잇기 모드는 하나의 채널에서 한개의 게임만 플레이 가능합니다."))

            self.bot.guild_multi_games.append(ctx.channel.id)
            game = MultiGame(ctx, hosting_time=round(time.time()))
            view = HostGuildGame(ctx, game=game)
            view.message = await ctx.reply(embed=game.hosting_embed(), view=view)
            game.msg = view.message
            is_timeout = await view.wait()
            if view.value == "stop" or is_timeout:
                self.bot.guild_multi_games.append(ctx.channel.id)
                return

            await game.update_embed(game.game_embed())
            game.begin_time = time.time()
            await game.send_info_embed()
            while True:
                try:
                    m = await self.bot.wait_for(
                        "message",
                        check=lambda _x: (
                            _x.author in game.players and _x.channel == ctx.channel and game.alive[game.turn % len(game.alive)] == _x.author
                        ),
                        timeout=game.time_left,
                    )
                    user_word = m.content
                except asyncio.TimeoutError:
                    await game.player_out()
                    if len(game.players) - len(game.final_score) == 1:
                        await game.game_end()
                        return
                    else:
                        await game.update_embed(game.game_embed())
                        await game.send_info_embed()

                else:
                    du = get_transition(game.word)
                    if user_word in ("ㅈㅈ", "gg", "GG"):
                        if game.turn < 5:
                            await game.send_info_embed("{denyed} 5턴 이상 진행해야 포기할 수 있습니다.")
                            continue
                        else:
                            await game.player_out(gg=True)
                            if len(game.players) - len(game.final_score) == 1:
                                await game.game_end()
                                return
                            else:
                                await game.update_embed(game.game_embed())
                                await game.send_info_embed()
                    elif user_word in game.used_words:
                        await game.send_info_embed(f"{{denyed}} **{user_word}** (은)는 이미 사용한 단어입니다.")
                        continue
                    elif user_word[0] not in du:
                        await game.send_info_embed(f"{{denyed}} **{'** 또는 **'.join(du)}** (으)로 시작하는 단어를 입력 해 주세요.")
                        continue
                    elif user_word in get_word(game.word):
                        if ((game.turn // len(game.alive)) == 0) and is_hanbang(user_word, game.used_words):
                            await game.send_info_embed("{denyed} 첫번째 회차에서는 한방단어를 사용할 수 없습니다.")
                            continue
                        elif user_word[0] in du:
                            game.used_words.append(user_word)
                            game.word = user_word
                            game.turn += 1
                            game.score += 1
                            await game.update_embed(game.game_embed())
                            game.begin_time = time.time()
                            if is_hanbang(game.word, game.used_words):
                                await game.player_out()
                                if len(game.players) - len(game.final_score) == 1:
                                    await game.game_end()
                                    return
                                else:
                                    await game.update_embed(game.game_embed())
                                    await game.send_info_embed()
                            else:
                                await game.send_info_embed()
                    else:
                        await game.send_info_embed(f"{{denyed}} **{user_word}** (은)는 없는 단어입니다.")
                        continue

        elif mode == 0:
            return await ctx.send("취소되었습니다.")

    @commands.command(name="끝말잇기1", usage="ㄲ끝말잇기1", aliases=("ㄲ1", "끝1", "ㄲㅁㅇㄱ1"), hidden=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def game1(self, ctx: commands.Context):
        """끝말잇기 '솔로 랭킹전' 모드를 플레이합니다."""
        await self.game(ctx, app_commands.Choice(name="솔로 랭킹전", value=1))

    @commands.command(name="끝말잇기2", usage="ㄲ끝말잇기2", aliases=("ㄲ2", "끝2", "ㄲㅁㅇㄱ2"), hidden=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def game2(self, ctx: commands.Context):
        """끝말잇기 '서버원들과 친선전' 모드를 플레이합니다."""
        await self.game(ctx, app_commands.Choice(name="서버원들과 친선전", value=2))

    @commands.command(name="끝말잇기3", usage="ㄲ끝말잇기3", aliases=("ㄲ3", "끝3", "ㄲㅁㅇㄱ3"), hidden=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def game3(self, ctx: commands.Context):
        """끝말잇기 '쿵쿵따' 모드를 플레이합니다."""
        await self.game(ctx, app_commands.Choice(name="쿵쿵따", value=3))
