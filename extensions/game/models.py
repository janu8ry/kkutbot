import random
import time
from typing import Literal

import discord
from discord.ext import commands

from config import config
from core import KkutbotContext
from tools.utils import dict_emojis, get_tier, get_winrate

from .utils import choose_first_word, get_transition, get_word

__all__ = ["SoloGame", "MultiGame"]


class GameBase:
    """Base Game Model for many modes."""

    __slots__ = ("ctx", "score", "begin_time", "timeout")

    def __init__(self, ctx: KkutbotContext):
        self.ctx = ctx
        self.score = 0
        self.begin_time = time.time()
        self.timeout = 10

    async def alert_tier_change(self, player: discord.User, tier: str, tier_past: str) -> discord.Message:
        tierlist = list(config.tierlist.keys())
        emojis = [data["emoji"] for data in config.tierlist.values()]
        if tierlist.index(tier) > tierlist.index(tier_past):
            embed = discord.Embed(
                title="{tier} 티어 승급!",
                description=f"{emojis[tierlist.index(tier_past)]} **{tier_past}** -> "
                            f"{emojis[tierlist.index(tier)]} **{tier}** 티어로 승급했습니다!",
                color=config.colors.help
            )
            embed.set_thumbnail(url=self.ctx.bot.get_emoji(config.emojis["levelup"]).url)
        else:
            embed = discord.Embed(
                title="{tier} 티어 강등...",
                description=f"{emojis[tierlist.index(tier_past)]} **{tier_past}** -> "
                            f"{emojis[tierlist.index(tier)]} **{tier}** 티어로 강등되었습니다...",
                color=config.colors.error
            )
            embed.set_thumbnail(url=self.ctx.bot.get_emoji(config.emojis["leveldown"]).url)
        return await self.ctx.send(player.mention, embed=embed, mention_author=True)

    @property
    def time_left(self) -> float:
        return self.timeout - (time.time() - self.begin_time)


class SoloGame(GameBase):
    """Game Model for single play mode"""

    __slots__ = ("player", "kkd", "score", "begin_time", "bot_word", "used_words", "ctx", "timeout")

    def __init__(self, ctx: KkutbotContext, kkd: bool = False):
        super().__init__(ctx)
        self.player = ctx.author
        self.kkd = kkd
        self.bot_word = choose_first_word(kkd)
        self.used_words = [self.bot_word]
        self.timeout = 15 if self.kkd else 10

    async def send_info_embed(self, msg: discord.Message | KkutbotContext, desc: str = "⏰ **10초** 안에 단어를 이어주세요!") -> discord.Message:
        embed = discord.Embed(title=f"📔 끝말잇기 {'쿵쿵따' if self.kkd else '랭킹전 싱글플레이'}", description=f"🔸 현재 점수: `{self.score}` 점", color=config.colors.help)
        embed.add_field(name="🔹 단어", value=f"```yaml\n{self.bot_word} ({' / '.join(get_transition(self.bot_word))})```", inline=False)
        embed.add_field(name="🔹 남은 시간", value=f"<t:{round(self.timeout + self.begin_time)}:R>", inline=False)
        embed.set_footer(text="'/도움'을 사용하여 규칙을 확인할 수 있습니다.")
        if self.kkd:
            desc = desc.replace("10", "15")
        desc = desc.format(**dict_emojis())
        try:
            return await msg.reply(desc, embed=embed, delete_after=self.time_left, mention_author=True)
        except discord.HTTPException as e:
            if e.code == 50035:
                return await self.ctx.send(f"{msg.author.mention}님, {desc}", embed=embed, delete_after=self.time_left)

    async def game_end(self, result: Literal["승리", "패배", "포기"]):
        mode = "kkd" if self.kkd else "rank_solo"
        user = await self.ctx.bot.db.get_user(self.player)
        modes = {"rank_solo": user.game.rank_solo, "kkd": user.game.kkd}

        if result == "승리":
            self.score += 10
            points = self.score * 5 if self.kkd else self.score * 3
            desc = "봇이 대응할 단어를 찾지 못했습니다!"
            color = config.colors.general
            emoji = "win"
            modes[mode].win += 1
        elif result == "패배":
            points = -30
            desc = f"대답시간이 {self.timeout}초를 초과했습니다..."
            color = config.colors.error
            emoji = "gameover"
        elif result == "포기":
            points = -30
            desc = "게임을 포기했습니다."
            color = config.colors.error
            emoji = "surrender"
        else:
            raise commands.BadArgument

        embed = discord.Embed(title="{result} 게임 결과", description=f"**{result}**  |  {desc}", color=color)
        embed.add_field(name="🔸 점수", value=f"`{self.score}` 점")
        embed.add_field(name="🔸 보상", value=f"`{'+' if result == '승리' else ''}{points}` {{points}}")
        embed.set_thumbnail(url=self.ctx.bot.get_emoji(config.emojis[emoji]).url)
        if result in ("패배", "포기"):
            possibles = [i for i in get_word(self.bot_word) if i not in self.used_words and (len(i) == 3 if self.kkd else True)]
            if possibles:
                random.shuffle(possibles)
                embed.add_field(name="🔹 가능했던 단어", value=f"`{'`, `'.join(possibles[:3])}` {'등...' if len(possibles) > 1 else ''}", inline=False)
            else:
                embed.add_field(name="🔹 가능했던 단어", value=f"`{self.bot_word}`은(는) 한방단어였습니다...", inline=False)
        await self.ctx.reply(embed=embed, mention_author=True)
        user.points += points
        modes[mode].times += 1
        if self.score > modes[mode].best:
            modes[mode].best = self.score
        if mode == "rank_solo":
            tier = get_tier(user, "rank_solo", emoji=False)
            if (tier_past := user.game.rank_solo.tier) != tier:
                user.game.rank_solo.tier = tier
                await self.alert_tier_change(self.player, tier, tier_past)
        modes[mode].winrate = get_winrate(modes[mode])
        await self.ctx.bot.db.save(user)


class MultiGame(GameBase):
    """Game Model for multiple play mode"""

    __slots__ = ("players", "ctx", "msg", "turn", "word", "used_words", "begin_time",
                 "final_score", "score", "hosting_time", "last_host")

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
        embed = discord.Embed(
            title=f"📔 **{self.host}**님의 끝말잇기",
            description=f"🔸 채널: {self.ctx.channel.mention}\n"
                        f"🔸 플레이어 모집 종료: <t:{self.hosting_time + 120}:R>\n\n"
                        "**참가하기** 버튼을 클릭하여 게임에 참가하기\n"
                        "**나가기** 버튼을 클릭하여 게임에서 나가기\n"
                        f"호스트 {self.host.mention} 님은 **게임 시작** 버튼을 클릭하여 게임을 시작할 수 있습니다.",
            color=config.colors.general)
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
        embed = discord.Embed(title="📔 끝말잇기 멀티플레이", description=f"🔸 라운드 **{(self.turn // len(self.alive)) + 1}**  |  차례: {self.now_player.mention}", color=config.colors.help)
        embed.add_field(name="🔹 단어", value=f"```yaml\n{self.word} ({' / '.join(get_transition(self.word))})```")
        embed.add_field(name="🔹 누적 점수", value=f"`{self.score}` 점", inline=False)
        embed.add_field(name="🔹 플레이어", value=f"`{'`, `'.join([_x.display_name for _x in self.players if _x not in self.final_score])}`", inline=False)
        embed.set_footer(text="'/도움'을 사용하여 규칙을 확인할 수 있습니다.")
        if self.final_score:
            embed.add_field(name="🔻 탈락자", value=f"`{'`, `'.join([_x.display_name for _x in self.final_score])}`", inline=False)
        return embed

    async def player_out(self, gg=False):
        embed = discord.Embed(title=f"🔻 {self.now_player}님 {'포기' if gg else '탈락'}!", color=config.colors.error)
        embed.set_thumbnail(url=self.ctx.bot.get_emoji(config.emojis["surrender" if gg else "dead"]).url)
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
        rank = sorted(self.final_score.items(), key=lambda item: item[1], reverse=True)
        emojis = ["{gold}", "{silver}", "{bronze}"]
        for n, kv in enumerate(rank):
            if n < len(rank) - 1:
                user = await self.ctx.bot.db.get_user(kv[0])
                desc.append(f"**{n + 1 if n >= 3 else emojis[n]}** - {kv[0].mention} : +`{int(rank[n + 1][1]) * 2}` {{points}}")
                user.points += int(rank[n + 1][1]) * 2
                user.game.guild_multi.times += 1
                user.latest_usage = time.time()
                if int(rank[n + 1][1]) > user.game.guild_multi.best:
                    user.game.guild_multi.best = self.score
                if (n + 1) <= round((len(rank) - 1) / 2):
                    user.game.guild_multi.win += 1
                user.game.guild_multi.winrate = get_winrate(user.game.guild_multi)  # type: ignore
                await self.ctx.bot.db.save(user)
        embed = discord.Embed(title="📔 게임 종료!", description="\n".join(desc), color=config.colors.general)
        embed.set_thumbnail(url=self.ctx.bot.get_emoji(config.emojis["gameover"]).url)
        await self.ctx.send(embed=embed)
        self.ctx.bot.guild_multi_games.remove(self.ctx.channel.id)

    async def send_info_embed(self, desc: str = "⏰ 10초 안에 단어를 이어주세요!") -> discord.Message:
        du_word = get_transition(self.word)
        desc = desc.format(**dict_emojis())
        embed = discord.Embed(
            title=self.word,
            description=f"<t:{round(10 + self.begin_time)}:R>까지 **{'** 또는 **'.join(du_word)}** (으)로 시작하는 단어를 이어주세요.",
            color=config.colors.general
        )
        return await self.msg.channel.send(f"{desc[0]} {self.now_player.mention}님, {desc[2:]}", embed=embed, delete_after=self.time_left)
