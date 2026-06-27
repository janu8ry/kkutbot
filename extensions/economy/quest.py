import discord
from discord.ext import commands

from config import config
from core import Kkutbot
from tools.utils import fmt, get_nested_dict


class Quest(commands.Cog, name="퀘스트"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="퀘스트", usage="{quest}", aliases=("ㅋㅅㅌ", "ㅋ", "과제", "데일리", "미션"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def quest(self, ctx: commands.Context):
        """
        매일 퀘스트를 클리어하고 보상을 획득합니다.

        퀘스트를 클리어하면 자동으로 보상을 획득할 수 있습니다.
        오늘의 모든 퀘스트를 완료하면 추가 보상을 받을 수 있습니다!
        퀘스트 항목은 0시에 초기화됩니다.

        --사용법
        `/퀘스트`를 사용하여 오늘의 퀘스트 목록을 확인합니다.
        """
        embed = discord.Embed(title="데일리 퀘스트", description="끝봇을 사용하며 퀘스트를 클리어하고, 보상을 획득하세요!", color=config.colors.green)
        user = await self.bot.db.get_user(ctx.author)
        public = await self.bot.db.get_public()
        for data, info in public.quests.items():
            current = get_nested_dict(user.model_dump(), data.split("/")) - user.quest.cache[data]
            if data in user.quest.status.completed:
                desc = "이 퀘스트를 완료했습니다!"
                title = f"🔸 ~~{info['name']}~~"
            else:
                desc = f"진행 상황: {round(current, 3)} / {info['target']} (`{round(current / info['target'] * 100, 1)}`%)"
                title = f"🔹 {info['name']}"
            embed.add_field(name=fmt(f"{title} `{info['reward'][0]}`{{{info['reward'][1]}}}"), value=desc, inline=False)
        embed.set_thumbnail(url=self.bot.emoji("quest").url)
        embed.set_footer(text="모든 퀘스트를 완료하고 추가 보상을 받아가세요!")
        await ctx.reply(embed=embed)
