import asyncio
import random
import time
from typing import Literal

import discord
from discord.ext import commands

from config import config
from database.models import GameBase
from tools.utils import fmt

from .ladder import (
    PLACEMENT_GAMES,
    ROMAN_DIVISIONS,
    TIER_EMOJIS,
    choose_bot_word,
    get_bot_surrender_threshold,
    get_rank_progress,
    get_win_lp,
    update_ladder,
)
from .views import MultiGameResult, PlayAgain
from .words import WordCheck, check_word, choose_first_word, get_transition, get_word, is_hanbang, word_error_message

__all__ = ["SoloGame", "MultiGame"]


def get_winrate(data: GameBase) -> float:
    if not data.times or not data.win:
        return 0.0
    return round(data.win / data.times * 100, 2)


async def _try_delete(msg: discord.Message | None) -> None:
    if msg:
        try:
            await msg.delete()
        except discord.HTTPException:
            pass


class GameSession:
    __slots__ = ("ctx", "score", "begin_time", "timeout")

    ENTRY_FEE = 40
    SURRENDER_ROUND = 5

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.score = 0
        self.begin_time = time.time()
        self.timeout = 10

    async def alert_rank_change(
        self, player: discord.User | discord.Member, before: str, after: str, promoted: bool, placement: bool = False
    ) -> discord.Message:
        if placement:
            embed = discord.Embed(
                title=fmt("{tier} 배치 완료!"),
                description=fmt(f"**{after}** 티어에 배치되었습니다."),
                color=config.colors.green,
            )
            embed.set_thumbnail(url=self.ctx.bot.emoji("levelup").url)
        elif promoted:
            embed = discord.Embed(
                title=fmt("{tier} 티어 승급!"),
                description=fmt(f"**{before}** -> **{after}** 티어로 승급했습니다."),
                color=config.colors.green,
            )
            embed.set_thumbnail(url=self.ctx.bot.emoji("levelup").url)
        else:
            embed = discord.Embed(
                title=fmt("{tier} 티어 강등..."),
                description=fmt(f"**{before}** -> **{after}** 티어로 강등되었습니다..."),
                color=config.colors.red,
            )
            embed.set_thumbnail(url=self.ctx.bot.emoji("leveldown").url)
        return await self.ctx.channel.send(player.mention, embed=embed)

    @property
    def time_left(self) -> float:
        return self.timeout - (time.time() - self.begin_time)


class SoloGame(GameSession):
    """Game Model for single play mode"""

    __slots__ = ("player", "kkd", "tier", "bot_word", "used_words")

    WIN_BONUS = 10

    def __init__(self, ctx: commands.Context, kkd: bool = False, tier: str = "언랭크"):
        super().__init__(ctx)
        self.player = ctx.author
        self.kkd = kkd
        self.tier = tier
        self.bot_word = choose_first_word(kkd)
        self.used_words = [self.bot_word]
        self.timeout = 15 if self.kkd else 10

    async def run(self) -> None:
        def check(x: discord.Message) -> bool:
            return x.author == self.player and x.channel == self.ctx.channel and bool(x.content.strip())

        info_msg = await self.send_info_embed(self.ctx)
        while True:
            try:
                msg = await self.ctx.bot.wait_for("message", check=check, timeout=self.time_left)
            except asyncio.TimeoutError:
                await self.game_end("패배")
                return

            user_word = msg.content.strip()
            result = check_word(
                user_word,
                self.bot_word,  # type: ignore
                self.used_words,
                first_round=self.score == 0,
                can_surrender=len(self.used_words) >= self.SURRENDER_ROUND * 2,
                kkd=self.kkd,
            )
            if result == WordCheck.SURRENDER:
                await self.game_end("포기")
                return
            if result != WordCheck.OK:
                await _try_delete(info_msg)
                error = word_error_message(result, user_word, self.bot_word, surrender_hint=f"{self.SURRENDER_ROUND}턴")  # type: ignore
                info_msg = await self.send_info_embed(msg, error)
                continue

            await _try_delete(info_msg)
            self.used_words.append(user_word)
            self.score += 1
            final_list = [x for x in get_word(user_word) if x not in self.used_words and (len(x) == 3 if self.kkd else True)]
            if self.kkd:
                if not final_list:
                    await self.game_end("승리")
                    return
                self.bot_word = random.choice(final_list)
            else:
                if len(final_list) <= get_bot_surrender_threshold(self.tier):
                    await self.game_end("승리")
                    return
                bot_word = choose_bot_word(final_list, self.used_words, self.tier)
                if bot_word is None:
                    await self.game_end("승리")
                    return
                self.bot_word = bot_word
            self.used_words.append(self.bot_word)
            self.begin_time = time.time()
            self.score += 1
            if is_hanbang(self.bot_word, self.used_words, kkd=self.kkd):
                await self.game_end("패배", hanbang=True)
                return
            info_msg = await self.send_info_embed(msg)

    async def send_info_embed(self, msg: discord.Message | commands.Context, desc: str | None = None) -> discord.Message | None:
        if desc is None:
            desc = f"⏰ **{self.timeout}초** 안에 단어를 이어주세요!"
        embed = discord.Embed(
            title=f"📔 끝말잇기 {'쿵쿵따 모드' if self.kkd else '솔로 랭크 게임'}",
            description=f"🔸 현재 점수: `{self.score}` 점",
            color=config.colors.green,
        )
        embed.add_field(name="🔹 단어", value=f"```yaml\n{self.bot_word} ({' / '.join(get_transition(self.bot_word))})```", inline=False)
        embed.add_field(name="🔹 남은 시간", value=f"<t:{round(self.timeout + self.begin_time)}:R>", inline=False)
        embed.set_footer(text="'/도움'을 사용하여 규칙을 확인할 수 있습니다.")
        desc = fmt(desc)
        if isinstance(msg, commands.Context) and msg.interaction and msg.interaction.response.is_done():
            return await self.ctx.channel.send(f"{self.player.mention}님, {desc}", embed=embed, delete_after=self.time_left)
        try:
            return await msg.reply(desc, embed=embed, delete_after=self.time_left, mention_author=True)
        except discord.HTTPException as e:
            if e.code == 50035:
                return await self.ctx.channel.send(f"{msg.author.mention}님, {desc}", embed=embed, delete_after=self.time_left)
            return None

    async def game_end(self, result: Literal["승리", "패배", "포기"], hanbang: bool = False):
        user = await self.ctx.bot.db.get_user(self.player)
        stats = user.game.kkd if self.kkd else user.game.rank_solo

        if result == "승리":
            reward = (self.score + self.WIN_BONUS) * (5 if self.kkd else 3)
            desc = "봇이 대응할 단어를 찾지 못했습니다!"
            color = config.colors.blue
            emoji = "win"
            stats.win += 1
            stats.streak += 1
        elif result == "패배":
            reward = 0
            desc = "한방단어에 당했습니다..." if hanbang else f"대답시간이 {self.timeout}초를 초과했습니다..."
            color = config.colors.red
            emoji = "gameover"
            stats.streak = 0
        elif result == "포기":
            reward = 0
            desc = "게임을 포기했습니다."
            color = config.colors.red
            emoji = "surrender"
            stats.streak = 0
        else:
            raise commands.BadArgument

        user.points += reward - self.ENTRY_FEE
        stats.times += 1
        record = self.score > stats.best
        if record:
            stats.best = self.score
        rank_changed = None
        placement_field: str | None = None
        lp_delta: int | None = None
        placement = False
        if not self.kkd:
            solo = user.game.rank_solo
            won = result == "승리"
            placement = solo.tier == "언랭크"
            mask_before = solo.lp
            lp_before, pos_before = solo.lp, (solo.tier, solo.division)
            rank_changed = update_ladder(solo, won, self.score)
            if placement:
                played = min(solo.times, PLACEMENT_GAMES)
                mask = mask_before | (int(won) << (played - 1))
                marks = ["✅" if (mask >> i) & 1 else "❌" for i in range(played)]
                marks += ["🔳"] * (PLACEMENT_GAMES - played)
                placement_field = " ".join(marks)
            elif (solo.tier, solo.division) != pos_before:
                lp_delta = get_win_lp(self.score) if won else None
            elif solo.lp != lp_before:
                lp_delta = solo.lp - lp_before
        stats.winrate = get_winrate(stats)

        head = f"**{stats.streak}연승** 🔥" if result == "승리" and stats.streak >= 2 else f"**{result}**"
        embed = discord.Embed(title=fmt("{result} 게임 결과"), description=f"{head}  |  {desc}", color=color)
        embed.add_field(name="🔸 점수", value=f"`{self.score}` 점{' **(신기록! 🎉)**' if record else ''}")
        embed.add_field(name="🔸 보상", value=fmt(f"`{'+' if reward else ''}{reward}` {{points}}"))
        if placement_field is not None:
            embed.add_field(name="🔸 배치고사", value=placement_field, inline=False)
        if not self.kkd and user.game.rank_solo.tier != "언랭크":
            tier_value = fmt(get_rank_progress(user.game.rank_solo))
            if lp_delta is not None:
                tier_value += f" **({lp_delta:+d})**"
            embed.add_field(name="🔸 티어", value=tier_value, inline=False)
        embed.set_thumbnail(url=self.ctx.bot.emoji(emoji).url)
        if result in ("패배", "포기"):
            possibles = [i for i in get_word(self.bot_word) if i not in self.used_words and (len(i) == 3 if self.kkd else True)]
            if possibles:
                random.shuffle(possibles)
                embed.add_field(
                    name="🔹 가능했던 단어", value=f"`{'`, `'.join(possibles[:3])}` {'등...' if len(possibles) > 1 else ''}", inline=False
                )
            else:
                embed.add_field(name="🔹 가능했던 단어", value=f"`{self.bot_word}`은(는) 한방단어였습니다...", inline=False)
        await self.ctx.bot.db.save(user)
        if rank_changed:
            await self.alert_rank_change(self.player, *rank_changed, placement=placement)
        view = PlayAgain(ctx=self.ctx)
        view.message = await self.send_result(embed, view)

    async def send_result(self, embed: discord.Embed, view: discord.ui.View) -> discord.Message:
        if not self.ctx.interaction:
            try:
                return await self.ctx.reply(embed=embed, view=view, mention_author=True)
            except discord.HTTPException as e:
                if e.code != 50035:
                    raise
        return await self.ctx.channel.send(self.player.mention, embed=embed, view=view)


class MultiGame(GameSession):
    """Game Model for multiple play mode"""

    __slots__ = (
        "players",
        "msg",
        "turn",
        "round",
        "word",
        "used_words",
        "final_score",
        "hosting_time",
        "last_host",
        "started_at",
        "next_action",
        "board_lock",
    )

    ENTRY_FEE = 20
    REWARD_RATE = 8
    MAX_RETURN = 1.5
    SURRENDER_ROUND = 3
    max_players = 7
    hosting_timeout = 120

    def __init__(self, ctx: commands.Context, hosting_time: int):
        super().__init__(ctx)
        self.players: list[discord.User | discord.Member] = [ctx.author]
        self.msg = ctx.message
        self.turn = 0
        self.round = 1
        self.word = choose_first_word()
        self.used_words = [self.word]
        self.final_score: dict[discord.User | discord.Member, int] = {}
        self.hosting_time = hosting_time
        self.last_host = ctx.author
        self.started_at = time.time()
        self.next_action: str | None = None
        self.board_lock = asyncio.Lock()

    @property
    def host(self) -> discord.User | discord.Member:
        return self.players[0] if self.players else self.last_host

    @property
    def now_player(self) -> discord.User | discord.Member:
        return self.alive[self.turn % len(self.alive)]

    @property
    def alive(self) -> list[discord.User | discord.Member]:
        return [p for p in self.players if p not in self.final_score]

    def wrap_turn(self) -> None:
        if self.turn >= len(self.alive):
            self.turn = 0
            self.round += 1

    async def run(self) -> None:
        def check(x: discord.Message) -> bool:
            return x.author in self.players and x.channel == self.ctx.channel and x.author == self.now_player and bool(x.content.strip())

        self.started_at = self.begin_time = time.time()
        await self.update_board()
        while True:
            try:
                m = await self.ctx.bot.wait_for("message", check=check, timeout=self.time_left)
            except asyncio.TimeoutError:
                if await self.handle_elimination():
                    return
                continue

            user_word = m.content.strip()
            result = check_word(
                user_word,
                self.word,
                self.used_words,
                first_round=self.round == 1,
                can_surrender=self.round > self.SURRENDER_ROUND,
            )
            if result == WordCheck.SURRENDER:
                if await self.handle_elimination(gg=True):
                    return
                continue
            if result != WordCheck.OK:
                await self.update_board(word_error_message(result, user_word, self.word, surrender_hint=f"{self.SURRENDER_ROUND}라운드"))
                continue

            self.used_words.append(user_word)
            self.word = user_word
            self.turn += 1
            self.wrap_turn()
            self.score += 1
            self.begin_time = time.time()
            if is_hanbang(self.word, self.used_words):
                if await self.handle_elimination():
                    return
            else:
                await self.update_board()

    async def handle_elimination(self, gg: bool = False) -> bool:
        await self.player_out(gg=gg)
        if len(self.players) - len(self.final_score) == 1:
            await self.game_end()
            return True
        await self.update_board()
        return False

    async def hosting_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"📔 **{self.host.display_name}**님의 끝말잇기 다인전",
            description=fmt(
                f"🔸 채널: {self.ctx.channel.mention}\n"  # type: ignore
                f"🔸 참가비: `{self.ENTRY_FEE}`{{points}}\n"
                f"🔸 플레이어 모집 종료: <t:{self.hosting_time + self.hosting_timeout}:R>\n\n"
                "서버 멤버들과 플레이하는 친선전입니다.\n"
                "티어와 LP는 변하지 않으며, 오래 살아남을수록 더 많은 포인트를 획득할 수 있습니다."
            ),
            color=config.colors.blue,
        )
        users = await asyncio.gather(*[self.ctx.bot.db.get_user(player) for player in self.players])
        lines = []
        for player, user in zip(self.players, users):
            rank = user.game.rank_solo
            if rank.tier == "언랭크":
                lines.append(player.mention)
            else:
                division = f"`{ROMAN_DIVISIONS[rank.division]}`" if rank.division else ""
                lines.append(f"{player.mention} ({fmt(TIER_EMOJIS[rank.tier])}{division})")
        embed.add_field(name=f"🔸 플레이어 ({len(self.players)}/{self.max_players})", value="\n".join(lines))
        embed.set_footer(text="최소 2인부터 시작할 수 있으며, 게임 시작은 호스트만 가능합니다.")
        return embed

    async def update_embed(self, embed: discord.Embed, view: discord.ui.View | None = None, content: str | None = None):
        async with self.board_lock:
            if self.msg.author.id == self.ctx.bot.user.id:
                await _try_delete(self.msg)
            self.msg = await self.ctx.channel.send(content, embed=embed, view=view)  # type: ignore
            return self.msg

    async def update_board(self, desc: str | None = None) -> None:
        if desc is None:
            desc = f"⏰ {self.timeout}초 안에 단어를 이어주세요!"
        head, _, tail = fmt(desc).partition(" ")
        await self.update_embed(self.game_embed(), content=f"{head} {self.now_player.mention}님, {tail}")

    def game_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📔 끝말잇기 다인전",
            description=f"🔸 라운드 **{self.round}**  |  차례: {self.now_player.mention}\n🔸 <t:{round(self.timeout + self.begin_time)}:R> 마감",
            color=config.colors.green,
        )
        embed.add_field(name="🔹 단어", value=f"```yaml\n{self.word} ({' / '.join(get_transition(self.word))})```")
        embed.add_field(name="🔹 누적 점수", value=f"`{self.score}` 점", inline=False)
        embed.add_field(name="🔹 플레이어", value=f"{', '.join([_x.mention for _x in self.players if _x not in self.final_score])}", inline=False)
        embed.set_footer(text="'/도움'을 사용하여 규칙을 확인할 수 있습니다.")
        if self.final_score:
            embed.add_field(name="🔻 탈락자", value=f"{', '.join([_x.mention for _x in self.final_score])}", inline=False)
        return embed

    async def player_out(self, gg=False):
        player = self.now_player
        embed = discord.Embed(title=f"🔻 {player.display_name}님 {'포기' if gg else '탈락'}!", color=config.colors.red)
        embed.set_thumbnail(url=self.ctx.bot.emoji("surrender" if gg else "dead").url)
        possibles = [i for i in get_word(self.word) if i not in self.used_words]
        if possibles:
            random.shuffle(possibles)
            embed.add_field(name="🔹 가능했던 단어", value=f"`{'`, `'.join(possibles[:3])}` {'등...' if len(possibles) > 1 else ''}", inline=False)
        else:
            embed.add_field(name="🔹 가능했던 단어", value=f"`{self.word}`은(는) 한방단어였습니다...", inline=False)
        await self.ctx.channel.send(embed=embed)
        self.final_score[player] = self.score
        self.wrap_turn()
        self.score += 2
        self.begin_time = time.time()
        self.word = choose_first_word()
        self.used_words.append(self.word)

    async def game_end(self):
        await _try_delete(self.msg)
        desc = []
        self.final_score[self.now_player] = self.score
        rank = sorted(self.final_score.items(), key=lambda item: item[1], reverse=True)
        pool = min(round(self.score * self.REWARD_RATE), round(self.ENTRY_FEE * len(rank) * self.MAX_RETURN))
        weight_sum = len(rank) * (len(rank) + 1) // 2
        emojis = ["{gold}", "{silver}", "{bronze}"]
        users = await asyncio.gather(*[self.ctx.bot.db.get_user(player) for player, _ in rank])
        for n, ((player, score), user) in enumerate(zip(rank, users)):
            reward = round(pool * (len(rank) - n) / weight_sum)
            user.points += reward - self.ENTRY_FEE
            user.game.guild_multi.times += 1
            user.latest_usage = round(time.time())
            record = score > user.game.guild_multi.best
            if record:
                user.game.guild_multi.best = score
            if (n + 1) <= len(rank) // 2:
                user.game.guild_multi.win += 1
                user.game.guild_multi.streak += 1
            else:
                user.game.guild_multi.streak = 0
            user.game.guild_multi.winrate = get_winrate(user.game.guild_multi)
            streak = user.game.guild_multi.streak
            tail = f" **({streak}연승 🔥)**" if streak >= 2 else (" **(신기록! 🎉)**" if record else "")
            desc.append(
                f"**{n + 1 if n >= 3 else emojis[n]}** - {player.mention} : `{score}`점  |  `{'+' if reward else ''}{reward}` {{points}}{tail}"
            )
        await asyncio.gather(*[self.ctx.bot.db.save(user) for user in users])
        elapsed = round(time.time() - self.started_at)
        duration = f"{elapsed // 60}분 {elapsed % 60}초" if elapsed >= 60 else f"{elapsed}초"
        embed = discord.Embed(
            title=fmt("{result} 게임 결과"),
            description=f"`{self.round}`라운드  |  소요 시간 `{duration}`",
            color=config.colors.blue,
        )
        embed.add_field(name="🔸 순위", value=fmt("\n".join(desc)), inline=False)
        embed.set_thumbnail(url=self.ctx.bot.emoji("gameover").url)
        view = MultiGameResult(ctx=self.ctx, game=self)
        embed.set_footer(text=f"{round(view.timeout or 0)}초 안에 선택하지 않으면 로비가 종료됩니다.")
        view.message = await self.ctx.channel.send(embed=embed, view=view)
        await view.wait()
