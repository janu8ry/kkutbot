import asyncio
from typing import Coroutine

import discord
from discord.utils import escape_markdown as e_mk
from motor.motor_asyncio import AsyncIOMotorCursor

from config import config, get_nested_dict
from core import KkutbotContext
from views import BaseView

__all__ = ["RankMenu"]


class RankDropdown(discord.ui.Select):
    def __init__(self, ctx: KkutbotContext):
        self.ctx = ctx
        self.guild = False
        self.guild_ids = [m.id for m in self.ctx.guild.members]
        self.now = "종합 랭킹"
        self.categories = {
            "general": {"포인트": "points", "메달": "medals", "출석": "attendance.times", "명령어": "command_used"},
            "game": {"솔로": "rank_solo", "쿵쿵따": "kkd"},  # TODO: 게임모드 완성시 교체: , "온라인": 'rank_online', "긴단어": 'long'},
            "main": ["포인트", "메달", "출석", "솔로", "쿵쿵따"]  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체
        }
        options = [
            discord.SelectOption(
                label="종합 랭킹",
                value="종합 랭킹",
                description="여러 분야의 랭킹을 한번에 확인합니다.",
                emoji="{ranking}"
            )
        ]
        for category in (self.categories["general"] | self.categories["game"]):
            option = discord.SelectOption(
                label=category if category in self.categories["general"] else f"끝말잇기 - {category}",
                value=category,
                description=f"{category + ' 분야' if category in self.categories['general'] else '끝말잇기 ' + category + ' 모드'}의 랭킹을 확인합니다.",
                emoji="{ranking}"
            )
            options.append(option)
        super().__init__(placeholder="분야를 선택해 주세요.", options=options, row=1)

    @property
    def query(self) -> dict:
        if self.guild:
            return {
                "_id": {
                    "$ne": self.ctx.bot.owner_id,
                    "$in": self.guild_ids
                }
            }
        return {
            "_id": {
                "$ne": self.ctx.bot.owner_id
            }
        }

    def game_query(self, path: str) -> dict:
        query = self.query.copy()
        query[f"game.{self.categories['game'][path]}.times"] = {"$gte": 30}
        return query

    async def get_user_name(self, user_id: int) -> str:
        user = self.ctx.bot.get_user(user_id)
        if hasattr(user, "name"):
            username: str = user.name
        else:
            if await self.ctx.bot.db.read_user(user_id, "name"):
                username = await self.ctx.bot.db.read_user(user_id, "name")
            else:
                username = (await self.ctx.bot.fetch_user(user_id)).name
        if len(username) >= 15:
            username = username[:12] + "..."
        return username

    async def format_rank(self, rank: AsyncIOMotorCursor, query: str) -> list:
        rank = await rank.to_list(None)
        names = await asyncio.gather(*[self.get_user_name(i["_id"]) for i in rank])
        return [f"**{idx + 1}**. {e_mk(names[idx])} : `{get_nested_dict(i, query.split('.'))}`" for idx, i in enumerate(rank)]

    async def get_overall_rank(self) -> tuple[discord.Embed, list[Coroutine]]:
        embed = discord.Embed(title=f"{{ranking}} {'서버' if self.guild else ''} 종합 랭킹 Top 5", color=config.colors.help)
        coros = []
        for path in self.categories["main"]:
            if path in self.categories["general"]:
                coros.append(
                    self.format_rank(self.ctx.bot.db.client.user.find(self.query).sort(self.categories["general"][path], -1).limit(5), self.categories["general"][path]),
                )
            else:
                for gpath in ("win", "best", "winrate"):
                    full_path = f"game.{self.categories['game'][path]}.{gpath}"
                    coros.append(
                        self.format_rank(self.ctx.bot.db.client.user.find(self.game_query(path)).sort(full_path, -1).limit(5), full_path),
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

    async def rank_embed(self, category: str = "종합 랭킹") -> discord.Embed:
        if category == "종합 랭킹":
            embed, coros = await self.get_overall_rank()
        elif category in self.categories["general"]:
            rank = self.ctx.bot.db.client.user.find(self.query).sort(self.categories["general"][category], -1).limit(15)
            embed = discord.Embed(
                title=f"{{ranking}} {'서버' if self.guild else ''} 랭킹 top 15 | {self.values[0]}",
                description="\n".join(await self.format_rank(rank, self.categories["general"][category])),
                color=config.colors.help
            )
        else:
            embed = discord.Embed(title=f"{{ranking}} 랭킹 Top 15 | 끝말잇기 - {category} 모드", color=config.colors.help)
            coros = []
            for path in ("win", "best", "winrate"):
                full_path = f"game.{self.categories['game'][category]}.{path}"
                coros.append(
                    self.format_rank(self.ctx.bot.db.client.user.find(self.game_query(category)).sort(full_path, -1).limit(15), full_path),
                )
            rank = await asyncio.gather(*coros)
            embed.add_field(name="🔹 승리수", value="\n".join(rank[0]))
            embed.add_field(name="🔹 최고점수", value="\n".join(rank[1]))
            embed.add_field(name="🔹 승률", value="\n".join(rank[2]))

        return embed

    async def callback(self, interaction: discord.Interaction):
        for item in self.options:
            item.default = False
            if item.value == self.values[0]:
                item.default = True
        self.now = self.values[0]
        embed = await self.rank_embed(category=self.now)
        await interaction.response.edit_message(embed=embed, view=self.view)


class RankMenu(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.dropdown = RankDropdown(ctx)
        self.add_item(self.dropdown)

    async def get_home_embed(self):
        embed, _ = await self.dropdown.get_overall_rank()
        return embed

    @discord.ui.button(label="전체 랭킹", style=discord.ButtonStyle.blurple, emoji="{global}", row=2, disabled=True)
    async def global_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        self.children[1].disabled = False
        self.dropdown.guild = False
        await interaction.response.edit_message(embed=await self.dropdown.rank_embed(self.dropdown.now), view=self)

    @discord.ui.button(label="서버 랭킹", style=discord.ButtonStyle.green, emoji="{server}", row=2, disabled=False)
    async def guild_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        self.children[0].disabled = False
        self.dropdown.guild = True
        await interaction.response.edit_message(embed=await self.dropdown.rank_embed(self.dropdown.now), view=self)
