import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

import discord
from discord.ext import commands

from config import config
from core import Kkutbot
from database.models import RankGameBase
from extensions.game.ladder import DIVISIONS, LP_PER_DIVISION, TIER_EMOJIS, get_rank_display, get_rank_progress  # noqa
from tools.utils import fmt, is_admin, split_string

from .views import SendAnnouncement

TIER_CODES: dict[str, str] = dict(zip("ubsgpdm", TIER_EMOJIS))
NO_DIVISION = ("언랭크", "마스터")


def format_field(key: str, value: Any) -> str:
    if isinstance(value, dict) and any(isinstance(v, dict) for v in value.values()):
        return "\n".join([f"{key}:", *(f"- {k}: `{v}`" for k, v in value.items())])
    return f"{key}: `{value}`"


def parse_tier(text: str) -> tuple[str, int] | None:
    name = TIER_CODES.get(text[:1].lower())
    if name is None:
        return None
    division = text[1:]
    if name in NO_DIVISION:
        return (name, 0) if not division else None
    return (name, int(division)) if division.isdecimal() and 0 < int(division) <= DIVISIONS else None


class Admin(commands.Cog, name="관리자"):
    """관리자 전용 명령어들입니다."""

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        return is_admin(ctx)

    @commands.command(name="$로그", aliases=("$ㄹㄱ", "$ㄹ"))
    async def get_log(self, ctx: commands.Context, date: str = commands.parameter(default=None)):
        """
        봇 로그 파일을 확인합니다.

        --사용법
        `ㄲ$로그`로 오늘자 로그 파일을 확인합니다.
        `ㄲ$로그 yy/mm/dd`로 특정 날짜의 로그 파일을 확인합니다.
        """
        if date is None:
            path = "logs/latest.log"  # noqa
        else:
            now = datetime.now()
            try:
                parts = [int(p) for p in re.split(r"[-/]", date)]
                if not 1 <= len(parts) <= 3:
                    raise ValueError
                if len(parts) == 1:
                    parts = [now.year, now.month, *parts]
                elif len(parts) == 2:
                    parts = [now.year, *parts]
                normalized = datetime(*parts).strftime("%Y-%m-%d")
            except TypeError, ValueError:
                await ctx.reply("날짜 형식이 올바르지 않습니다. (예: `2026-07-05`, `07/05`, `5`)")
                return
            path = f"logs/{normalized}.log.gz"
        if not os.path.isfile(path):
            await ctx.reply(fmt("{denied} 해당 날짜의 로그 파일이 존재하지 않습니다."))
            return
        await ctx.reply(file=discord.File(path))

    @commands.command(name="$백업", aliases=("$ㅂㅇ", "$ㅂ"))
    async def backup_now(self, ctx: commands.Context):
        """
        현재 데이터베이스를 백업하여 파일로 전송합니다.

        --사용법
        `ㄲ$백업`을 사용하여 실시간 백업을 진행합니다.
        """
        fp = f"backup/{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.gz"
        async with ctx.typing():
            if error := await self.bot.dump_data(fp):
                await ctx.reply(fmt(f"{{denied}} 데이터베이스 백업에 실패했습니다.\n```\n{error}```"))
                return
            try:
                await ctx.reply(file=discord.File(fp))
            finally:
                os.remove(fp)

    @commands.command(name="$정보", aliases=("$ㅈㅂ", "$ㅈ"))
    async def user_info(self, ctx: commands.Context, *, user: discord.User = commands.parameter(default=None)):
        """
        유저의 상세 정보를 출력합니다.

        --사용법
        `ㄲ$정보`를 사용하여 공용 데이터를 확인합니다.
        `ㄲ$정보 <유저>`를 사용하여 특정 유저의 데이터를 확인합니다.
        """
        if user is None:
            public_data = await self.bot.db.get_public()  # noqa
            sorted_data = sorted(public_data.commands.items(), key=lambda item: item[1], reverse=True)
            for content in split_string("\n".join(f"{k}: `{v}`회" for k, v in sorted_data)):
                await ctx.reply(content)
            public_data = public_data.model_dump()
            del public_data["commands"]
            for content in split_string("\n".join(format_field(k, v) for k, v in public_data.items())):
                await ctx.reply(content)
        else:
            user_data = await self.bot.db.get_user(user)
            if not user_data.registered:
                await ctx.reply(f"`{user.name}`님은 끝봇의 유저가 아닙니다.")
                return
            for content in split_string("\n".join(format_field(k, v) for k, v in user_data.model_dump().items())):
                await ctx.reply(content)

    @commands.command(name="$서버정보", aliases=("$ㅅㅂㅈㅂ", "$ㅅㅈ"))
    async def guild_info(self, ctx: commands.Context, *, guild: discord.Guild = commands.CurrentGuild):
        """
        끝봇을 사용중인 서버의 상세 정보를 출력합니다.

        --사용법
        `ㄲ$서버정보`를 사용하여 현재 서버의 데이터를 확인합니다.
        `ㄲ$서버정보 <서버>`를 사용하여 특정 서버의 데이터를 확인합니다.
        """
        guild_data = await self.bot.db.get_guild(guild)
        if not guild_data.invited:
            await ctx.reply(fmt("{denied} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다."))
            return
        guild_data = guild_data.model_dump()
        guild_data["name"] = guild.name
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in guild_data.items())):
            await ctx.reply(content)

    @commands.command(name="$포인트", aliases=("$ㅍㅇㅌ", "$ㅍ"))
    async def give_point(self, ctx: commands.Context, amount: int = 1000, *, user: discord.User = commands.Author):
        """
        관리자 권한으로 유저에게 포인트를 지급합니다.

        --사용법
        `ㄲ$포인트 <포인트>`로 자신에게 포인트를 지급합니다.
        `ㄲ$포인트 <포인트> <유저>`를 사용하여 특정 유저에게 포인트를 지급합니다.
        """
        if user.bot:
            await ctx.reply(fmt("{denied} 봇에게는 지급할 수 없습니다."))
            return
        user_data = await self.bot.db.get_user(user)
        user_data.points += amount
        await self.bot.db.save(user_data)
        await ctx.reply(fmt("{done} 완료!"))

    @commands.command(name="$메달", aliases=("$ㅁㄷ", "$ㅁ"))
    async def give_medal(self, ctx: commands.Context, amount: int = 10, *, user: discord.User = commands.Author):
        """
        관리자 권한으로 유저에게 메달을 지급합니다.

        --사용법
        `ㄲ$메달 <메달>`로 자신에게 메달을 지급합니다.
        `ㄲ$메달 <메달> <유저>`를 사용하여 특정 유저에게 메달을 지급합니다.
        """
        if user.bot:
            await ctx.reply(fmt("{denied} 봇에게는 지급할 수 없습니다."))
            return
        user_data = await self.bot.db.get_user(user)
        user_data.medals += amount
        await self.bot.db.save(user_data)
        await ctx.reply(fmt("{done} 완료!"))

    async def send_tier_distribution(self, ctx: commands.Context) -> None:
        pipeline = [{"$group": {"_id": {"tier": "$game.rank_solo.tier", "division": "$game.rank_solo.division"}, "count": {"$sum": 1}}}]
        docs = await self.bot.db.client.user.aggregate(pipeline).to_list(None)
        order = list(TIER_EMOJIS)

        counts: defaultdict[str, defaultdict[int, int]] = defaultdict(lambda: defaultdict(int))
        for doc in docs:
            name = doc["_id"].get("tier")
            counts[name if name in order else order[0]][doc["_id"].get("division") or 0] += doc["count"]

        total = sum(sum(divisions.values()) for divisions in counts.values())
        if not total:
            await ctx.reply(fmt("{denied} 집계할 유저가 없습니다."))
            return

        def stat(tier: str, division: int, count: int) -> str:
            label = get_rank_display(RankGameBase(tier=tier, division=division), emoji=False)
            return f"- {label} `{count:,}`명 (`{count / total * 100:.2f}`%)"

        sections = []
        for name in reversed(order):
            if not (divisions := counts.get(name)):
                continue
            subtotal = sum(divisions.values())
            rows = [f"🔸 **{name}** {fmt(TIER_EMOJIS[name])} - `{subtotal:,}`명 (`{subtotal / total * 100:.2f}`%)"]
            rows.extend(stat(name, division, divisions[division]) for division in sorted(divisions) if division)
            sections.append("\n".join(rows))

        ranked = total - sum(counts[order[0]].values())
        embed = discord.Embed(title="솔로 랭크 티어 분포", description="\n\n".join(sections), color=config.colors.blue)
        embed.set_footer(text=f"전체 {total:,}명 · 배치 완료 {ranked:,}명 ({ranked / total * 100:.2f}%)")
        await ctx.reply(embed=embed)

    @commands.command(name="$티어", aliases=("$ㅌㅇ", "$ㅌ"))
    async def set_tier(
        self, ctx: commands.Context, tier: str | None = commands.parameter(default=None), lp: int = 0, *, user: discord.User = commands.Author
    ):
        """
        유저의 솔로 랭크 티어를 변경합니다.

        티어는 앞글자(ubsgpdm)에 디비전을 붙여 사용하고, (예: `b3`, `s1`, `d2`)
        언랭크와 마스터는 디비전을 추가하지 않습니다. (예: `u`, `m`)
        언랭크로 변경하면 배치고사 기록이 함께 초기화됩니다.

        --사용법
        `ㄲ$티어`를 사용하여 전체 유저의 티어 분포를 확인합니다.
        `ㄲ$티어 <티어> <lp> <유저>`를 사용하여 특정 유저의 티어를 변경합니다.
        """
        if tier is None:
            await self.send_tier_distribution(ctx)
            return
        if user.bot:
            await ctx.reply(fmt("{denied} 봇의 티어는 변경할 수 없습니다."))
            return
        if (parsed := parse_tier(tier)) is None:
            await ctx.reply(fmt("{denied} 티어 형식이 올바르지 않습니다. (예: `b3`, `s1`, `d2`, `m`, `u`)"))
            return
        name, division = parsed
        if lp < 0:
            await ctx.reply(fmt("{denied} LP는 0 이상이어야 합니다."))
            return
        if name == "언랭크":
            lp = 0
        elif name != "마스터" and lp >= LP_PER_DIVISION:
            await ctx.reply(fmt(f"{{denied}} 마스터가 아닌 티어의 LP는 최대 `{LP_PER_DIVISION - 1}`입니다."))
            return

        user_data = await self.bot.db.get_user(user)
        rank = user_data.game.rank_solo
        rank.tier, rank.division, rank.lp = name, division, lp
        if name == "언랭크":
            rank.times = rank.win = rank.streak = 0
        await self.bot.db.save(user_data)
        await ctx.reply(fmt(f"{{done}} `{user.name}`님의 티어를 {get_rank_progress(rank)} (으)로 변경했습니다."))

    @commands.command(name="$삭제", aliases=("$ㅅ", "$통계삭제", "$ㅌㅅ"))
    async def delete_user_data(self, ctx: commands.Context, *, user: discord.User = commands.Author):
        """
        유저의 데이터를 초기화합니다.

        --사용법
        `ㄲ$통계삭제`를 사용하여 자신의 데이터를 삭제합니다.
        `ㄲ$통계삭제 <유저>`를 사용하여 특정 유저의 데이터를 삭제합니다.
        """
        data = await self.bot.db.get_user(user)
        if data.registered:
            await data.delete()
            await ctx.reply(fmt("{done} 완료!"))
        else:
            await ctx.reply(fmt("{denied} 해당 유저는 끝봇의 유저가 아닙니다."))

    @commands.command(name="$서버삭제", aliases=("$ㅅㅅ", "$서버통계삭제", "$ㅅㅌㅅ"))
    async def delete_guild_data(self, ctx: commands.Context, *, guild: discord.Guild = commands.CurrentGuild):
        """
        서버의 데이터를 초기화합니다.

        --사용법
        `ㄲ$서버통계삭제`를 사용하여 현재 서버의 데이터를 삭제합니다.
        `ㄲ$서버통계삭제 <서버>`를 사용하여 특정 서버의 데이터를 삭제합니다.
        """
        data = await self.bot.db.get_guild(guild)
        if data.invited:
            await data.delete()
            await ctx.reply(fmt("{done} 완료!"))
        else:
            await ctx.reply(fmt("{denied} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다."))

    @commands.command(name="$탈퇴", aliases=("$서버탈퇴", "$나가기", "$ㅌㅌ"))
    async def leave_guild(self, ctx: commands.Context, *, guild: discord.Guild = commands.CurrentGuild):
        """
        봇이 참가한 서버를 나갑니다.

        --사용법
        `ㄲ$서버탈퇴`를 사용하여 현재 서버를 탈퇴합니다.
        `ㄲ$서버탈퇴 <서버>`를 사용하여 특정 서버를 탈퇴합니다.
        """
        data = await self.bot.db.get_guild(guild)
        if data.invited:
            await guild.leave()
            await data.delete()
            await ctx.reply(fmt("{done} 완료!"))
        else:
            await ctx.reply(fmt("{denied} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다."))

    @commands.command(name="$공지", aliases=("$ㄱㅈ", "$ㄱ"))
    async def announce_users(self, ctx: commands.Context):
        """
        끝봇의 유저들에게 공지를 전송합니다.

        --사용법
        `ㄲ$공지`로 공지를 작성하고 전송합니다.
        """
        view = SendAnnouncement(ctx=ctx)
        view.message = await ctx.reply("버튼 눌러 공지 작성하기", view=view)
