import asyncio
import operator
import random
import time
from typing import Literal, Union

import discord
from discord.ext import commands

from core import Kkutbot, KkutbotContext
from tools.db import add, config, read, write
from tools.utils import choose_first_word, get_tier, get_transition, get_winrate, get_word, is_hanbang
from tools.views import BaseView


class GameBase:
    """Base Game Model for many modes."""

    __slots__ = ("ctx", "score", "begin_time")

    def __init__(self, ctx: KkutbotContext):
        self.ctx = ctx
        self.score = 0
        self.begin_time = time.time()

    async def alert_tier_change(self, player: discord.User, tier: str, tier_past: str) -> discord.Message:
        tierlist = list(config("tierlist").keys())
        emojis = [data["emoji"] for data in config("tierlist").values()]
        if tierlist.index(tier) > tierlist.index(tier_past):
            embed = discord.Embed(
                title="{tier} 티어 승급!",
                description=f"{emojis[tierlist.index(tier_past)]} **{tier_past}** -> "
                            f"{emojis[tierlist.index(tier)]} **{tier}** 티어로 승급했습니다!",
                color=config("colors.help")
            )
            embed.set_thumbnail(url=self.ctx.bot.get_emoji(config('emojis.levelup')).url)
        else:
            embed = discord.Embed(
                title="{tier} 티어 강등...",
                description=f"{emojis[tierlist.index(tier_past)]} **{tier_past}** -> "
                            f"{emojis[tierlist.index(tier)]} **{tier}** 티어로 강등되었습니다...",
                color=config("colors.error")
            )
            embed.set_thumbnail(url=self.ctx.bot.get_emoji(config("emojis.leveldown")).url)
        return await self.ctx.send(player.mention, embed=embed, mention_author=True)


class SoloGame(GameBase):
    """Game Model for single play mode"""

    __slots__ = ("player", "kkd", "score", "begin_time", "bot_word", "used_words", "ctx")

    def __init__(self, ctx: KkutbotContext, kkd: bool = False):
        super().__init__(ctx)
        self.player = ctx.author
        self.kkd = kkd
        self.bot_word = choose_first_word(kkd)
        self.used_words = [self.bot_word]

    async def send_info_embed(self, _msg: Union[discord.Message, KkutbotContext], desc: str = "10초 안에 단어를 이어주세요!") -> discord.Message:
        embed = discord.Embed(title=f"📔 끝말잇기 {'쿵쿵따' if self.kkd else '랭킹전 싱글플레이'}", description=f"🔸 현재 점수: `{self.score}` 점", color=config('colors.help'))
        embed.add_field(name="🔹 단어", value=f"```yaml\n{self.bot_word} ({' / '.join(get_transition(self.bot_word))})```", inline=False)
        embed.add_field(name="🔹 남은 시간", value=f"<t:{round((15 if self.kkd else 10) + self.begin_time)}:R>", inline=False)
        embed.set_footer(text="'ㄲ도움'을 입력하여 규칙을 확인할 수 있습니다.")
        if self.kkd:
            desc = desc.replace("10", "15")
        desc = desc.format(**self.ctx.bot.dict_emojis())
        try:
            return await _msg.reply(desc, embed=embed, delete_after=(15 if self.kkd else 10) - (time.time() - self.begin_time), mention_author=True)
        except discord.HTTPException as e:
            if e.code == 50035:
                return await self.ctx.send(f"{_msg.author.mention}님, {desc}", embed=embed, delete_after=(15 if self.kkd else 10) - (time.time() - self.begin_time))

    async def game_end(self, result: Literal["승리", "패배", "포기"]):
        mode = "kkd" if self.kkd else "rank_solo"

        if result == "승리":
            self.score += 10
            points = self.score * 5 if self.kkd else self.score * 3
            desc = "봇이 대응할 단어를 찾지 못했습니다!"
            color = config("colors.general")
            emoji = "win"
            await add(self.player, f"game.{mode}.win", 1)
        elif result == "패배":
            points = -30
            desc = f"대답시간이 {15 if self.kkd else 10}초를 초과했습니다..."
            color = config("colors.error")
            emoji = "gameover"
        elif result == "포기":
            points = -30
            desc = "게임을 포기했습니다."
            color = config("colors.error")
            emoji = "surrender"
        else:
            raise commands.BadArgument

        embed = discord.Embed(title="{result} 게임 결과", description=f"**{result}**  |  {desc}", color=color)
        embed.add_field(name="🔸 점수", value=f"`{self.score}` 점")
        embed.add_field(name="🔸 보상", value=f"`{'+' if result == '승리' else ''}{points}` {{points}}")
        embed.set_thumbnail(url=self.ctx.bot.get_emoji(config(f"emojis.{emoji}")).url)
        if result in ("패배", "포기"):
            possibles = [i for i in get_word(self.bot_word) if i not in self.used_words and (len(i) == 3 if self.kkd else True)]
            if possibles:
                random.shuffle(possibles)
                embed.add_field(name="🔹 가능했던 단어", value=f"`{'`, `'.join(possibles[:3])}` {'등...' if len(possibles) > 1 else ''}", inline=False)
            else:
                embed.add_field(name="🔹 가능했던 단어", value=f"`{self.bot_word}`은(는) 한방단어였습니다...", inline=False)
        await self.ctx.reply(embed=embed, mention_author=True)
        await add(self.player, "points", points)
        await add(self.player, f"game.{mode}.times", 1)
        if self.score > await read(self.player, f"game.{mode}.best"):
            await write(self.player, f"game.{mode}.best", self.score)
        if mode == "rank_solo":
            tier = await get_tier(self.player, "rank_solo", emoji=False)
            if (tier_past := await read(self.player, "game.rank_solo.tier")) != tier:
                await write(self.player, "game.rank_solo.tier", tier)
                await self.alert_tier_change(self.player, tier, tier_past)
        await write(self.player, f"game.{mode}.winrate", await get_winrate(self.player, mode))


class MultiGame(GameBase):
    """Game Model for multiple play mode"""

    __slots__ = ("players", "ctx", "msg", "turn", "word", "used_words", "begin_time", "final_score", "score", "hosting_time", "last_host")

    def __init__(self, ctx: KkutbotContext, hosting_time: int):
        super().__init__(ctx)
        self.players = [ctx.author]
        self.msg = ctx.message
        self.turn = 0
        self.word = choose_first_word()
        self.used_words = [self.word]
        self.final_score = {}
        self.hosting_time = hosting_time
        self.last_host = ctx.author

    @property
    def host(self) -> discord.User:
        return self.players[0] if self.players else self.last_host

    @property
    def now_player(self) -> discord.User:
        return self.alive[self.turn % len(self.alive)]

    @property
    def alive(self) -> list:
        return [p for p in self.players if p not in self.final_score]

    def hosting_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f"📔 **{self.host}**님의 끝말잇기",
                              description=f"🔸 채널: {self.ctx.channel.mention}\n"
                                          f"🔸 플레이어 모집 종료: <t:{self.hosting_time + 120}:R>\n\n"
                                          "`참가하기` 버튼을 클릭하여 게임에 참가하기\n"
                                          "`나가기` 버튼을 클릭하여 게임에서 나가기\n"
                                          f"호스트 {self.host.mention} 님은 `게임 시작` 버튼을 클릭하여 게임을 시작할 수 있습니다.",
                              color=config('colors.general'))
        embed.add_field(name=f"🔸 플레이어 ({len(self.players)}/5)",
                        value="`" + "`\n`".join([str(_x) for _x in self.players]) + "`")
        return embed

    async def update_embed(self, embed: discord.Embed, view: discord.ui.View = None):
        try:
            if self.msg.author.id == self.ctx.bot.user.id:
                await self.msg.delete()
        except discord.NotFound:
            pass
        self.msg = await self.msg.channel.send(embed=embed, view=view)
        return self.msg

    def game_embed(self) -> discord.Embed:
        embed = discord.Embed(title="📔 끝말잇기 멀티플레이", description=f"🔸 라운드 **{(self.turn // len(self.alive)) + 1}**  |  차례: {self.now_player.mention}", color=config('colors.help'))
        embed.add_field(name="🔹 단어", value=f"```yaml\n{self.word} ({' / '.join(get_transition(self.word))})```")
        embed.add_field(name="🔹 누적 점수", value=f"`{self.score}` 점", inline=False)
        embed.add_field(name="🔹 플레이어", value=f"`{'`, `'.join([_x.name for _x in self.players if _x not in self.final_score])}`", inline=False)
        embed.set_footer(text="'ㄲ도움'을 입력하여 규칙을 확인할 수 있습니다.")
        if self.final_score:
            embed.add_field(name="🔻 탈락자", value=f"`{'`, `'.join([_x.name for _x in self.final_score])}`", inline=False)
        return embed

    async def player_out(self, gg=False):
        embed = discord.Embed(title=f"🔻 {self.now_player}님 {'포기' if gg else '탈락'}!", color=config("colors.error"))
        embed.set_thumbnail(url=self.ctx.bot.get_emoji(config(f"emojis.{'surrender' if gg else 'dead'}")).url)
        possibles = [i for i in get_word(self.word) if i not in self.used_words]
        if possibles:
            random.shuffle(possibles)
            embed.add_field(name="🔹 가능했던 단어", value=f"`{'`, `'.join(possibles[:3])}` {'등...' if len(possibles) > 1 else ''}", inline=False)
        else:
            embed.add_field(name="🔹 가능했던 단어", value=f"`{self.word}`은(는) 한방단어였습니다...", inline=False)
        await self.ctx.send(embed=embed)
        self.final_score[self.now_player] = self.score
        self.score += 2
        self.begin_time = time.time()
        self.word = choose_first_word()
        self.used_words.append(self.word)

    async def game_end(self):
        await self.msg.delete()
        desc = []
        self.final_score[self.now_player] = self.score
        self.final_score["zero"] = 0
        rank = sorted(self.final_score.items(), key=operator.itemgetter(1), reverse=True)
        emojis = ["{gold}", "{silver}", "{bronze}"]
        for n, kv in enumerate(rank):
            if n < len(rank) - 1:
                desc.append(f"**{n + 1 if n >= 3 else emojis[n]}** - {kv[0].mention} : +`{int(rank[n + 1][1]) * 2}` {{points}}")
                await add(kv[0], "points", int(rank[n + 1][1]) * 2)
                await add(kv[0], "game.guild_multi.times", 1)
                await write(kv[0], "last_command", time.time())
                if int(rank[n + 1][1]) > await read(kv[0], "game.guild_multi.best"):
                    await write(kv[0], "game.guild_multi.best", self.score)
                if (n + 1) <= round((len(rank) - 1) / 2):
                    await add(kv[0], "game.guild_multi.win", 1)
                await write(kv[0], "game.guild_multi.winrate", await get_winrate(kv[0], "guild_multi"))
        embed = discord.Embed(title="📔 게임 종료!", description="\n".join(desc), color=config("colors.general"))
        embed.set_thumbnail(url=self.ctx.bot.get_emoji(config("emojis.gameover")).url)
        await self.ctx.send(embed=embed)
        Game.guild_multi_games.remove(self.ctx.channel.id)
        del self

    async def send_info_embed(self, desc: str = "10초 안에 단어를 이어주세요!") -> discord.Message:
        du_word = get_transition(self.word)
        desc = desc.format(**self.ctx.bot.dict_emojis())
        embed = discord.Embed(
            title=self.word,
            description=f"<t:{round(10 + self.begin_time)}:R>까지 `{'` 또는 `'.join(du_word)}` (으)로 시작하는 단어를 이어주세요.",
            color=config("colors.general")
        )
        return await self.msg.channel.send(f"{self.now_player.mention}님, {desc}", embed=embed, delete_after=10 - (time.time() - self.begin_time))


class SelectMode(BaseView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.ctx = ctx
        self.timeout = 15
        self.value = None

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="1️⃣")
    async def rank_solo(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 1
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="2️⃣")
    async def guild_multi(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 2
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="3️⃣")
    async def kkd(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 3
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="❌")
    async def quit(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 0
        await self.disable_buttons(interaction)
        self.stop()

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
        await self.ctx.reply("취소되었습니다.")


class HostGuildGame(BaseView):
    def __init__(self, ctx: commands.Context, game: MultiGame):
        super().__init__(ctx=ctx, author_only=False)
        self.ctx = ctx
        self.timeout = 120
        self.game = game
        self.value = None

    @discord.ui.button(label="참가하기", style=discord.ButtonStyle.blurple, emoji="<:join:988350647093063681>")
    async def join_game(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if interaction.user in self.game.players:
            return await interaction.response.send_message("<:denyed:730319627623596032> 이미 게임에 참가했습니다.", ephemeral=True)
        if await read(interaction.user, "banned.isbanned"):
            return await interaction.response.send_message("<:denyed:730319627623596032> 차단된 유저는 게임에 참가할 수 없습니다.", ephemeral=True)
        self.game.players.append(interaction.user)
        await self.ctx.send(f"<:plus:988352187522506782> **{interaction.user}** 님이 참가했습니다.")
        if len(self.game.players) == 5:
            await self.ctx.send(f"✅ 최대 인원에 도달하여 **{self.game.host}** 님의 게임을 시작합니다.")
            self.value = "start"
            await self.disable_buttons(interaction)
            return self.stop()
        await interaction.response.defer()
        self.message = await self.game.update_embed(self.game.hosting_embed(), view=self)

    @discord.ui.button(label="나가기", style=discord.ButtonStyle.red, emoji="<:leave:988350673223548949>")
    async def leave_game(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if interaction.user not in self.game.players:
            return await interaction.response.send_message("<:denyed:730319627623596032> 게임에 참가하지 않았습니다.", ephemeral=True)
        self.game.players.remove(interaction.user)
        self.game.last_host = self.game.host
        await self.ctx.send(f"<:minus:988352203200794634> **{interaction.user}**님이 나갔습니다.")
        if len(self.game.players) == 0:
            await self.ctx.send(f"❌ 플레이어 수가 부족하여 **{self.game.host}** 님의 게임을 종료합니다.")
            Game.guild_multi_games.remove(self.ctx.channel.id)
            self.value = "stop"
            await self.disable_buttons(interaction)
            return self.stop()
        await interaction.response.defer()
        self.message = await self.game.update_embed(self.game.hosting_embed(), view=self)

    @discord.ui.button(label="게임 시작", style=discord.ButtonStyle.green, emoji="<:start:988350697873477683>")
    async def start_game(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if interaction.user != self.game.host:
            return await interaction.response.send_message("<:denyed:730319627623596032> 호스트만 게임을 시작할 수 있습니다.", ephemeral=True)
        if len(self.game.players) < 2:
            return await interaction.response.send_message("<:denyed:730319627623596032> 플레이어 수가 부족하여 게임을 시작할 수 없습니다.", ephemeral=True)
        await self.ctx.send(f"✅ **{self.game.host}**님의 게임을 시작합니다.")
        self.value = "start"
        await self.disable_buttons(interaction)
        return self.stop()

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
        if len(self.game.players) < 2:
            await self.ctx.send(f"❌ 플레이어 수가 부족하여 **{self.game.host}**님의 게임을 종료합니다.")
            Game.guild_multi_games.remove(self.ctx.channel.id)
            self.value = "stop"
            return self.stop()
        else:
            await self.ctx.send(f"✅ 대기 시간이 초과되어 **{self.game.host}**님의 게임을 시작합니다.")
            self.value = "start"
            return self.stop()


class Game(commands.Cog, name="게임"):
    """끝봇의 메인 기능인 끝말잇기 게임에 대한 명령어입니다."""

    __slots__ = ("bot",)
    guild_multi_games = []

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="끝말잇기", usage="ㄲ끝말잇기 <모드>", aliases=("ㄲ", "끝", "ㄲㅁㅇㄱ"))
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def game(self, ctx: KkutbotContext, mode: int = None):
        """
        **1. 게임 방법**
        서로 번갈아가며 상대방이 마지막에 제시한 단어의 마지막 글자로 시작하는 단어를 제시합니다.
        이를 계속 반복하다가 어느 한쪽이 단어를 잇지 못하게 되면 상대방의 승리!
        첫 차례에 한방단어는 사용 불가합니다.
        이미 사용한 단어, 한글자 단어, 사전에 없는 단어는 사용 불가능합니다.

        게임 도중에 "ㅈㅈ" 또는 "gg"를 입력하면 게임을 포기할 수 있습니다. (*주의: 포기시 해당 게임은 패배로 처리됩니다.*)

        **2. 점수 계산 방식**
        승리시에는 상대방과 플레이어가 주고받은 단어의 개수에 비례해 포인트를 획득하고,
        패배 또는 포기시에는 30포인트가 차감됩니다.

        **3. 기타**
        단어DB 출처 : 표준국어대사전, 단어수 약 31만개

        **4. 게임모드**
        :one: 솔로 랭킹전
        -끝봇과 끝말잇기 대결을 합니다.

        :two: 서버원들과 친선전
        -같은 서버에 있는 유저들 여러 명과 끝말잇기 대결을 합니다.

        :three: 쿵쿵따
        -끝봇과 끝말잇기 대결을 합니다. 하지만 세글자 단어만 사용 가능합니다.

        `ㄲ끝말잇기 <모드>` 명령어로 해당 게임 모드를 빠르게 플레이 할 수도 있습니다!
        예시) `ㄲ끝말잇기 1` -> 1번 모드(솔로 랭킹전) 플레이

        3종류의 모드 추가 개발중...
        """

        def check(x: Union[discord.Message, KkutbotContext]) -> bool:
            return x.author == ctx.author and x.channel == ctx.channel

        if (await read(ctx.author, "points")) <= 30:
            return await ctx.reply("{denyed} 포인트가 30점 미만이라 플레이할 수 없습니다.\n"
                                   "`ㄲ출석`, `ㄲ포인트`, `ㄲ퀘스트` 명령어를 사용해서 포인트를 획득해 보세요!")

        if mode is None:
            embed = discord.Embed(title="📔 끝말잇기", description="🔸 끝말잇기 게임의 모드를 선택해 주세요.", color=config("colors.general"))
            embed.add_field(name=":one:", value="- 솔로 랭킹전", inline=False)
            embed.add_field(name=":two:", value="- 서버원들과 친선전", inline=False)
            embed.add_field(name=":three:", value="- 쿵쿵따", inline=False)
            embed.set_footer(text="'ㄲ도움' 으로 더 자세한 도움말을 확인해 보세요!")
            view = SelectMode(ctx)
            view.message = await ctx.reply(embed=embed, view=view)
            await view.wait()
            mode = view.value
        elif not (1 <= mode <= 3):
            return await ctx.reply("{denyed} 존재하지 않는 모드입니다.")

        if mode == 1:
            game = SoloGame(ctx)
            await game.send_info_embed(ctx)
            while True:
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=10.0 - (time.time() - game.begin_time))
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
                        await game.send_info_embed(msg, f"**{user_word}** (은)는 이미 사용한 단어입니다.")
                        continue
                    elif user_word[0] not in du:
                        await game.send_info_embed(msg, f"`{'` 또는 `'.join(du)}` (으)로 시작하는 단어를 입력해 주세요.")
                        continue
                    elif user_word in get_word(game.bot_word):
                        if (game.score == 0) and is_hanbang(user_word, game.used_words):
                            await game.send_info_embed(msg, "첫번째 회차에서는 한방단어를 사용할 수 없습니다.")
                            continue
                        elif user_word[0] in du:
                            game.used_words.append(user_word)
                            game.score += 1
                    else:
                        await game.send_info_embed(msg, f"**{user_word}** (은)는 없는 단어입니다.")
                        continue
                final_list = [x for x in get_word(user_word) if x not in game.used_words]
                if not final_list:  # noqa
                    await game.game_end("승리")
                    return
                else:
                    game.bot_word = random.choice(final_list)
                    game.used_words.append(game.bot_word)
                    game.begin_time = time.time()
                    game.score += 1
                    if is_hanbang(game.bot_word, game.used_words):
                        await game.game_end("패배")
                        return
                    else:
                        await game.send_info_embed(msg)

        elif mode == 2:
            if isinstance(ctx.channel, discord.DMChannel):
                raise commands.errors.NoPrivateMessage
            if ctx.channel.id in Game.guild_multi_games:
                return await ctx.reply("{denyed} 이 끝말잇기 모드는 하나의 채널에서 한개의 게임만 플레이 가능합니다.")

            Game.guild_multi_games.append(ctx.channel.id)
            game = MultiGame(ctx, hosting_time=round(time.time()))
            view = HostGuildGame(ctx, game=game)
            view.message = await ctx.reply(embed=game.hosting_embed(), view=view)
            game.msg = view.message
            is_timeout = await view.wait()

            if view.value == "start":
                pass
            elif view.value == "stop" or is_timeout:
                return

            await game.update_embed(game.game_embed())
            game.begin_time = time.time()
            await game.send_info_embed()
            while True:
                try:
                    m = await self.bot.wait_for(
                        "message",
                        check=lambda _x: _x.author in game.players and _x.channel == ctx.channel and game.alive[game.turn % len(game.alive)] == _x.author,
                        timeout=10.0 - (time.time() - game.begin_time)
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
                        await game.send_info_embed(f"***{user_word}*** (은)는 이미 사용한 단어입니다.")
                        continue
                    elif user_word[0] not in du:
                        await game.send_info_embed(f"`{'` 또는 `'.join(du)}` (으)로 시작하는 단어를 입력 해 주세요.")
                        continue
                    elif user_word in get_word(game.word):
                        if ((game.turn // len(game.alive)) == 0) and is_hanbang(user_word, game.used_words):
                            await game.send_info_embed("첫번째 회차에서는 한방단어를 사용할 수 없습니다.")
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
                        await game.send_info_embed(f"**{user_word}** (은)는 없는 단어입니다.")
                        continue

        elif mode == 3:
            game = SoloGame(ctx, True)
            await game.send_info_embed(ctx)
            while True:
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=15.0 - (time.time() - game.begin_time))
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
                        await game.send_info_embed(msg, f"**{user_word}** (은)는 이미 사용한 단어입니다.")
                        continue
                    elif user_word[0] not in du:
                        await game.send_info_embed(msg, f"`{'` 또는 `'.join(du)}` (으)로 시작하는 단어를 입력 해 주세요.")
                        continue
                    elif len(user_word) != 3:
                        await game.send_info_embed(msg, "세글자 단어만 사용 가능합니다.")
                        continue
                    elif user_word in get_word(game.bot_word):
                        if (game.score == 0) and (len(get_word(user_word)) == 0):
                            await game.send_info_embed(msg, "첫번째 회차에서는 한방단어를 사용할 수 없습니다.")
                            continue
                        elif user_word[0] in du:
                            game.used_words.append(user_word)
                            game.score += 1
                    else:
                        await game.send_info_embed(msg, f"**{user_word}** (은)는 없는 단어입니다.")
                        continue
                final_list = [x for x in get_word(user_word) if x not in game.used_words and len(x) == 3]
                if not final_list:
                    await game.game_end("승리")
                    return
                else:
                    game.bot_word = random.choice(final_list)
                    game.used_words.append(game.bot_word)
                    game.begin_time = time.time()
                    game.score += 1
                    if is_hanbang(game.bot_word, game.used_words, kkd=True):
                        await game.game_end("패배")
                        return
                    else:
                        await game.send_info_embed(msg)

        elif mode == 0:
            return await ctx.send("취소되었습니다.")


async def setup(bot: Kkutbot):
    await bot.add_cog(Game(bot))
