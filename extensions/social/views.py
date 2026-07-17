import asyncio
from typing import Coroutine, TypedDict

import discord
from discord.ext import commands
from discord.utils import escape_markdown as e_mk
from motor.motor_asyncio import AsyncIOMotorCursor

from config import config, get_nested_dict
from tools import fmt
from tools.utils import ROMAN_DIVISIONS, TIER_EMOJIS, format_number  # noqa
from views import BaseView

__all__ = ["RankMenu"]


class _Categories(TypedDict):
    general: dict[str, str]
    game: dict[str, str]
    main: list[str]


class RankDropdown(discord.ui.Select):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.guild = False
        self.guild_ids = [m.id for m in self.ctx.guild.members]  # type: ignore
        self.now = "종합 랭킹"
        self.categories: _Categories = {
            "general": {"포인트": "points", "메달": "medals", "출석": "attendance.times", "명령어": "command_used"},
            "game": {"솔로": "rank_solo", "쿵쿵따": "kkd"},  # TODO: 게임모드 완성시 교체: , "온라인": 'rank_online', "긴단어": 'long'},
            "main": ["포인트", "메달", "출석", "솔로", "쿵쿵따"],  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체
        }
        category_emojis: dict[str, str] = {
            "포인트": fmt("{points}"),
            "메달": fmt("{medals}"),
            "출석": fmt("{attendance}"),
            "명령어": "⌨️",
            "솔로": "📔",
            "쿵쿵따": "3️⃣",
        }
        options = [
            discord.SelectOption(label="종합 랭킹", value="종합 랭킹", description="여러 분야의 랭킹을 한번에 확인합니다.", emoji=fmt("{ranking}"))
        ]
        for category in self.categories["general"] | self.categories["game"]:
            option = discord.SelectOption(
                label=category if category in self.categories["general"] else f"끝말잇기 - {category}",
                value=category,
                description=f"{category + ' 분야' if category in self.categories['general'] else '끝말잇기 ' + category + ' 모드'}의 랭킹을 확인합니다.",
                emoji=category_emojis.get(category, fmt("{ranking}")),
            )
            options.append(option)
        super().__init__(placeholder="분야를 선택해 주세요.", options=options, row=1)

    @property
    def query(self) -> dict:
        if self.guild:
            return {"_id": {"$in": self.guild_ids}}
        return {"_id": {"$ne": self.ctx.bot.owner_id}}

    def game_query(self, path: str) -> dict:
        query = self.query.copy()
        query[f"game.{self.categories['game'][path]}.times"] = {"$gte": 30}
        return query

    async def get_user_name(self, doc: dict) -> str:
        stored: str | None = doc.get("name")
        cached = self.ctx.bot.get_user(doc["_id"])
        if cached is not None:
            username = cached.name
        elif stored:
            username = stored
        else:
            username = (await self.ctx.bot.fetch_user(doc["_id"])).name
        if username != stored:
            await self.ctx.bot.db.client.user.update_one({"_id": doc["_id"]}, {"$set": {"name": username}})
        if len(username) >= 15:
            username = username[:12] + "..."
        return username

    async def format_rank(self, cursor: AsyncIOMotorCursor, query: str) -> list[str]:
        docs = await cursor.to_list(None)
        names = list(await asyncio.gather(*[self.get_user_name(doc) for doc in docs]))  # type: ignore
        return [f"**{idx + 1}**. {e_mk(names[idx])} : `{format_number(get_nested_dict(doc, query.split('.')))}`" for idx, doc in enumerate(docs)]

    async def format_ladder_rank(self, limit: int) -> list[str]:
        tiers = list(TIER_EMOJIS)
        match = self.query.copy()
        match["game.rank_solo.tier"] = {"$in": tiers[1:]}
        pipeline = [
            {"$match": match},
            {
                "$addFields": {
                    "_ladder": {
                        "$add": [
                            {"$multiply": [{"$indexOfArray": [tiers, "$game.rank_solo.tier"]}, 10000]},
                            {"$multiply": [{"$subtract": [3, "$game.rank_solo.division"]}, 1000]},
                            "$game.rank_solo.lp",
                        ]
                    }
                }
            },
            {"$sort": {"_ladder": -1}},
            {"$limit": limit},
        ]
        docs = await self.ctx.bot.db.client.user.aggregate(pipeline).to_list(None)
        names = list(await asyncio.gather(*[self.get_user_name(doc) for doc in docs]))
        lines = []
        for idx, doc in enumerate(docs):
            rs = doc["game"]["rank_solo"]
            division = f" {ROMAN_DIVISIONS[rs['division']]}" if rs["division"] else ""
            lines.append(f"**{idx + 1}**. {e_mk(names[idx])} : {fmt(TIER_EMOJIS.get(rs['tier'], ''))}{division} `{format_number(rs['lp'])}`LP")
        return lines

    async def get_overall_rank(self) -> tuple[discord.Embed, list[Coroutine]]:
        embed = discord.Embed(title=fmt(f"{{ranking}} {'서버' if self.guild else ''} 종합 랭킹 Top 5"), color=config.colors.green)
        coros = []
        for path in self.categories["main"]:
            if path in self.categories["general"]:
                coros.append(
                    self.format_rank(
                        self.ctx.bot.db.client.user.find(self.query).sort(self.categories["general"][path], -1).limit(5),
                        self.categories["general"][path],
                    ),
                )
            else:
                mode = self.categories["game"][path]
                coros.append(
                    self.format_rank(
                        self.ctx.bot.db.client.user.find(self.game_query(path)).sort(f"game.{mode}.win", -1).limit(5), f"game.{mode}.win"
                    )
                )
                coros.append(
                    self.format_rank(
                        self.ctx.bot.db.client.user.find(self.game_query(path)).sort(f"game.{mode}.best", -1).limit(5), f"game.{mode}.best"
                    )
                )
                if mode == "rank_solo":
                    coros.append(self.format_ladder_rank(5))
                else:
                    coros.append(
                        self.format_rank(
                            self.ctx.bot.db.client.user.find(self.game_query(path)).sort(f"game.{mode}.winrate", -1).limit(5), f"game.{mode}.winrate"
                        )
                    )
        overall_rank = await asyncio.gather(*coros)
        labels_solo = ["승리수", "최고점수", "래더"]
        labels_kkd = ["승리수", "최고점수", "승률"]
        for i, rank in enumerate(overall_rank):
            if i <= 2:
                embed.add_field(name=f"🔹 {self.categories['main'][i]}", value="\n".join(rank) or "정보 없음")
            elif 3 <= i <= 5:
                embed.add_field(name=f"🔹 솔로 모드 - {labels_solo[i - 3]}", value="\n".join(rank) or "정보 없음")
            else:
                embed.add_field(
                    name=f"🔹 쿵쿵따 모드 - {labels_kkd[i - 6]}", value="\n".join(rank) or "정보 없음"
                )  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체

        return embed, coros

    async def rank_embed(self, category: str = "종합 랭킹") -> discord.Embed:
        if category == "종합 랭킹":
            embed, coros = await self.get_overall_rank()
        elif category in self.categories["general"]:
            rank = self.ctx.bot.db.client.user.find(self.query).sort(self.categories["general"][category], -1).limit(15)
            embed = discord.Embed(
                title=fmt(f"{{ranking}} {'서버' if self.guild else ''} 랭킹 top 15 | {category}"),
                description="\n".join(await self.format_rank(rank, self.categories["general"][category])),
                color=config.colors.green,
            )
        else:
            embed = discord.Embed(title=fmt(f"{{ranking}} 랭킹 Top 15 | 끝말잇기 - {category} 모드"), color=config.colors.green)
            mode = self.categories["game"][category]
            is_solo = mode == "rank_solo"
            coros = [
                self.format_rank(
                    self.ctx.bot.db.client.user.find(self.game_query(category)).sort(f"game.{mode}.win", -1).limit(15), f"game.{mode}.win"
                ),
                self.format_rank(
                    self.ctx.bot.db.client.user.find(self.game_query(category)).sort(f"game.{mode}.best", -1).limit(15), f"game.{mode}.best"
                ),
                self.format_ladder_rank(15)
                if is_solo
                else self.format_rank(
                    self.ctx.bot.db.client.user.find(self.game_query(category)).sort(f"game.{mode}.winrate", -1).limit(15), f"game.{mode}.winrate"
                ),
            ]
            rank = await asyncio.gather(*coros)
            embed.add_field(name="🔹 승리수", value="\n".join(rank[0]) or "정보 없음")
            embed.add_field(name="🔹 최고점수", value="\n".join(rank[1]) or "정보 없음")
            embed.add_field(name="🔹 래더" if is_solo else "🔹 승률", value="\n".join(rank[2]) or "정보 없음")

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
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.dropdown = RankDropdown(ctx)
        self.add_item(self.dropdown)

    async def get_home_embed(self):
        embed, _ = await self.dropdown.get_overall_rank()
        return embed

    @discord.ui.button(label="전체 랭킹", style=discord.ButtonStyle.blurple, emoji=fmt("{global}"), row=2, disabled=True)
    async def global_rank(self: RankMenu, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        self.children[1].disabled = False
        self.dropdown.guild = False
        await interaction.response.edit_message(embed=await self.dropdown.rank_embed(self.dropdown.now), view=self)

    @discord.ui.button(label="서버 랭킹", style=discord.ButtonStyle.green, emoji=fmt("{server}"), row=2, disabled=False)
    async def guild_rank(self: RankMenu, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        self.children[0].disabled = False
        self.dropdown.guild = True
        await interaction.response.edit_message(embed=await self.dropdown.rank_embed(self.dropdown.now), view=self)
