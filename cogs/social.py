import asyncio
import time

import discord
from discord.ext import commands
from discord.utils import escape_markdown as e_mk
from motor.motor_asyncio import AsyncIOMotorCursor  # noqa

from config import config, get_nested_dict
from core import Kkutbot, KkutbotContext
from tools.db import read, write
from tools.utils import time_convert
from tools.views import BaseView, Paginator


class RankDropdown(discord.ui.Select):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.categories = {
            "general": {"포인트": "points", "메달": "medals", "출석": "attendance.times", "명령어": "command_used"},
            "game": {"솔로": "rank_solo", "쿵쿵따": "kkd"},  # TODO: 게임모드 완성시 교체: , "온라인": 'rank_online', "긴단어": 'long'},
            "main": ["포인트", "메달", "출석", "솔로", "쿵쿵따"]  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체
        }
        self.query = {
            "banned.isbanned": False,
            "_id": {
                "$nin": config("bot_whitelist"),
                "$ne": self.ctx.bot.owner_id
            }
        }
        options = [
            discord.SelectOption(
                label="종합 랭킹",
                value="종합 랭킹",
                description="여러 분야의 랭킹을 한번에 확인합니다.",
                emoji="<:ranking:985439871004995634>"
            )
        ]
        for category in self.categories["general"] | self.categories["game"]:
            option = discord.SelectOption(
                label=category if category in self.categories["general"] else f"끝말잇기 - {category}",
                value=category,
                description=f"{category + ' 분야' if category in self.categories['general'] else '끝말잇기 ' + category + ' 모드' }의 랭킹을 확인합니다.",
                emoji="<:ranking:985439871004995634>"
            )
            options.append(option)
        super().__init__(placeholder="분야를 선택해 주세요.", options=options, row=1)

    async def get_user_name(self, user_id: int) -> str:
        user = self.ctx.bot.get_user(user_id)
        if hasattr(user, "name"):
            username = user.name
        else:
            if await read(user_id, "name"):
                username = await read(user_id, "name")
            else:
                username = (await self.ctx.bot.fetch_user(user_id)).name
        if len(username) >= 15:
            username = username[:12] + "..."
        return username

    async def format_rank(self, rank: AsyncIOMotorCursor, query: str) -> list:
        rank = await rank.to_list(None)
        names = await asyncio.gather(*[self.get_user_name(i["_id"]) for i in rank])
        return [f"**{idx + 1}**. {e_mk(names[idx])} : `{get_nested_dict(i, query.split('.'))}`" for idx, i in enumerate(rank)]

    async def get_overall_rank(self):
        embed = discord.Embed(title="{ranking} 종합 랭킹 top 5", color=config("colors.help"))
        coros = []
        for path in self.categories["main"]:
            if path in self.categories["general"]:
                coros.append(
                    self.format_rank(self.ctx.bot.db.user.find(self.query).sort(self.categories["general"][path], -1).limit(5), self.categories["general"][path]),
                )
            else:
                game_query = self.query.copy()
                game_query[f"game.{self.categories['game'][path]}.times"] = {"$gte": 50}  # type: ignore
                for gpath in ("win", "best", "winrate"):
                    full_path = f"game.{self.categories['game'][path]}.{gpath}"
                    coros.append(
                        self.format_rank(self.ctx.bot.db.user.find(game_query).sort(full_path, -1).limit(5), full_path),
                    )
        overall_rank = await asyncio.gather(*coros)
        gpath = ["승리수", "최고점수", "승률"]
        for i, rank in enumerate(overall_rank):
            if i <= 2:
                embed.add_field(name=f"🔹 {self.categories['main'][i]}", value="\n".join(rank))
            elif 3 <= i <= 5:
                embed.add_field(name=f"🔹 솔로 모드 - {gpath[i % 3]}", value="\n".join(rank))
            else:
                embed.add_field(name=f"🔹 쿵쿵따 모드 - {gpath[i % 3]}", value="\n".join(rank))  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체

        return embed, coros

    async def callback(self, interaction: discord.Interaction):
        for item in self.options:
            item.default = False
            if item.value == self.values[0]:
                item.default = True
        category = self.values[0]
        if category == "종합 랭킹":
            embed, coros = await self.get_overall_rank()
        elif category in self.categories["general"]:
            rank = self.ctx.bot.db.user.find(self.query).sort(self.categories["general"][category], -1).limit(15)
            embed = discord.Embed(
                title=f"{{ranking}} 랭킹 top 15 | {self.values[0]}",
                description="\n".join(await self.format_rank(rank, self.categories["general"][category])),
                color=config("colors.help")
            )
        else:
            self.query[f"game.{self.categories['game'][category]}.times"] = {"$gte": 50}
            embed = discord.Embed(title=f"{{ranking}} 랭킹 top 15 | 끝말잇기 - {category} 모드", color=config("colors.help"))
            coros = []
            for path in ("win", "best", "winrate"):
                full_path = f"game.{self.categories['game'][category]}.{path}"
                coros.append(
                    self.format_rank(self.ctx.bot.db.user.find(self.query).sort(full_path, -1).limit(15), full_path),
                )
            rank = await asyncio.gather(*coros)
            embed.add_field(name="🔹 승리수", value="\n".join(rank[0]))
            embed.add_field(name="🔹 최고점수", value="\n".join(rank[1]))
            embed.add_field(name="🔹 승률", value="\n".join(rank[2]))

        await interaction.response.edit_message(embed=embed, view=self.view)


class RankMenu(BaseView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.dropdown = RankDropdown(ctx)
        self.add_item(self.dropdown)

    async def get_home_embed(self):
        embed, _ = await self.dropdown.get_overall_rank()
        return embed


class Social(commands.Cog, name="소셜"):
    """끝봇의 소셜 기능에 관련된 명령어들입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="랭킹", usage="ㄲ랭킹", aliases=("ㄹ", "리더보드", "순위", "ㄹㅋ"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def ranking(self, ctx: KkutbotContext):
        """여러 분야의 랭킹을 확인합니다.
        끝말잇기 랭킹의 경우, 랭킹에 등재되려면 해당 모드를 50번 이상 플레이 해야 합니다.
        """
        view = RankMenu(ctx)
        view.message = await ctx.reply(embed=await view.get_home_embed(), view=view)

    @commands.command(name="메일", usage="ㄲ메일", aliases=("ㅁ", "ㅁㅇ", "메일함", "알림", "공지"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def mail(self, ctx: KkutbotContext):
        """끝봇의 공지와 업데이트 소식, 개인 알림 등을 확인합니다."""
        mails = sorted(await read(ctx.author, "mails") + await read(None, "announcements"), key=lambda item: item["time"], reverse=True)
        pages = []
        if mails:
            for mail in mails:
                embed = discord.Embed(title=f"{{email}} {ctx.author.name} 님의 메일함", color=config("colors.help"))
                embed.add_field(
                    name=f"🔹 {mail['title']} - `{time_convert(time.time() - mail['time'])} 전`",
                    value=mail["value"],
                    inline=False
                )
                pages.append(embed)
        else:
            embed = discord.Embed(
                    title=f"{{email}} {ctx.author.name} 님의 메일함",
                    description="{denyed} 메일함이 비어있습니다!",
                    color=config("colors.help")
                )
            pages.append(embed)
        await write(ctx.author, "alerts.mails", True)
        await write(ctx.author, "alerts.announcements", True)
        paginator = Paginator(ctx, pages=pages)
        await paginator.run()

    @commands.command(name="뱝", usage="ㄲ뱝", aliases=("고래뱝", "뱝뱝", "ㄸ뜌"), hidden=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def byab(self, ctx: KkutbotContext):
        """🐳 안녕하세요!"""
        await ctx.reply("""
코로나19로 힘든 시기!
딩가딩가 놀 수만은 없죠.
도움이 필요하실 때에는 어떻게 한다?
우리 고래뱝을 쓴다!
미친듯이 안켜지지만 어쩔 수 없어요...

개발중이라 조금 불안정할 수 있어요!
씹덕봇은 아니니까 걱정하지 않으셔도 돼요.
망한 것 같지만, 좋은 봇입니다! 초대해봐요

**봇 초대 링크**

https://discord.com/oauth2/authorize?client_id=732773322286432416&permissions=336066630&scope=bot
""")


async def setup(bot: Kkutbot):
    await bot.add_cog(Social(bot))
