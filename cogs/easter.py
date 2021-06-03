import asyncio
import random

import discord
from discord.ext import commands

from ext.core import Kkutbot, KkutbotContext
from ext.db import config


class EasterEgg(commands.Cog, name="이스터에그"):
    """그런 게 없을까?"""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="슬롯", usage="ㄲ슬롯 <값>")
    @commands.bot_has_permissions(add_reactions=True)
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    async def hanmaru_slot(self, ctx: KkutbotContext, amount: str = None):
        """올인하세요"""
        em = ['🍎', '🍇', '🍌', '🍊', '🥝', '🍑', '⭐']
        if not amount == "올인":
            await ctx.reply("올인하세요")
            return
        msg = await ctx.reply(
            f":slot_machine: **{ctx.author.name}**님의 슬롯 | <:hanmaru_token:796185418616930314> `9999` 베팅 | <:hanmaru_token:796185418616930314> `0` 누적\n"
            "[❔] [❔] [❔]")
        slot_em = []
        for _ in range(3):
            n_em = random.choice(em)
            slot_em.append(n_em)
            em.remove(n_em)
        await asyncio.sleep(1)
        await msg.edit(content=f":slot_machine: **{str(ctx.author).split('#')[0]}**님의 슬롯 | <:hanmaru_token:796185418616930314> `9999` 베팅 | <:hanmaru_token:796185418616930314> `0` 누적\n"
                               f"[{slot_em[0]}] [❔] [❔]")
        await asyncio.sleep(1)
        await msg.edit(content=f":slot_machine: **{str(ctx.author).split('#')[0]}**님의 슬롯 | <:hanmaru_token:796185418616930314> `9999` 베팅 | <:hanmaru_token:796185418616930314> `0` 누적\n"
                               f"[{slot_em[0]}] [{slot_em[1]}] [❔]")
        await asyncio.sleep(1)
        await msg.edit(content=f":slot_machine: **{str(ctx.author).split('#')[0]}**님의 슬롯 | <:hanmaru_token:796185418616930314> `9999` 베팅 | <:hanmaru_token:796185418616930314> `0` 누적\n"
                               f"[{slot_em[0]}] [{slot_em[1]}] [{slot_em[2]}]")
        embed = discord.Embed(description=f"{ctx.author.mention} 아쉽게도 만들어진 조합이 없어요..", color=0xA04F4F)
        await msg.edit(content=f":slot_machine: **{str(ctx.author).split('#')[0]}**님의 슬롯 | <:hanmaru_token:796185418616930314> `9999` 베팅 | <:hanmaru_token:796185418616930314> `0` 누적\n"
                               f"[{slot_em[0]}] [{slot_em[1]}] [{slot_em[2]}]", embed=embed)

    @commands.command(name="재생", usage="ㄲ재생 <노래명>")
    @commands.cooldown(rate=1, per=4, type=commands.BucketType.user)
    async def green_play(self, ctx: KkutbotContext, song: str = None):
        """노래나 들으실래요?"""
        if song is None:
            raise commands.BadArgument
        embed = discord.Embed(
            title="에러 발생",
            description="""
File "/usr/local/lib/python3.8/site-packages/discord/ext/commands/core.py", line 85, in wrapped
ret = await coro(*args, **kwargs)
File "/kkutbot-easter/Cogs/music.py", line 96, in _play
await self_check.connect_voice(ctx)
File "/kkutbot-easter/self_check.py", line 20, in connect_voice
await ctx.bot.audio.connect(ctx.author.voice.channel)
File "/usr/local/lib/python3.8/site-packages/discodo/client/DPYClient.py", line 200, in connect
raise NodeNotConnected
NodeNotConnected:
""",
            color=config('colors.error'))
        await ctx.send(embed=embed)

    @commands.command(name="$디스코드", usage="ㄲ$디스코드", aliases=("$디코",))
    @commands.max_concurrency(1)
    async def my_discord(self, ctx: KkutbotContext):
        """?"""
        return await ctx.send("**그런 거 없다**")


def setup(bot: Kkutbot):
    bot.add_cog(EasterEgg(bot))
