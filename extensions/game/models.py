import random
import time
from typing import Literal

import discord
from discord.ext import commands

from config import config
from core import KkutbotContext
from tools.utils import get_tier, get_winrate
from .utils import choose_first_word, get_transition, get_word

__all__ = ["SoloGame"]


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
        desc = desc.format(**self.ctx.bot.dict_emojis())
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
            desc = f"대답시간이 {15 if self.kkd else 10}초를 초과했습니다..."
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
