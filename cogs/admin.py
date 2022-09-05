import time
from copy import deepcopy
from typing import Union

import discord
from discord.ext import commands
from humanize import naturalsize
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa

from config import config
from core import Kkutbot, KkutbotContext
from tools.converter import KkutbotUserConverter
from tools.db import add, delete, read, write
from tools.utils import is_admin, split_string
from views.admin import ModifyData, SendAnnouncement, SendNotice
from views.general import ServerInvite


class Admin(commands.Cog, name="관리자"):
    """관리자 전용 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    def cog_check(self, ctx: KkutbotContext):
        return is_admin(ctx)

    @commands.command(name="$현황", usage="ㄲ$현황", aliases=("ㅎ", "$ㅎ"))
    async def kkutbot_status(self, ctx: KkutbotContext, count: int = 7):
        """끝봇의 현황을 확인합니다."""
        embed = discord.Embed(color=config("colors.general"))

        t1 = time.time()
        await self.bot.db.general.find_one({"_id": "test"})
        t1 = time.time() - t1

        t2 = time.time()
        await self.bot.db.general.update_one({"_id": "test"}, {"$set": {"lastest": time.time()}}, upsert=True)
        t2 = time.time() - t2

        embed.add_field(
            name="성능",
            value=f"평균 연결 속도: `{round(self.bot.latency * 1000)}`ms\n"
                  f"메시지 캐시: `{len(self.bot.cached_messages)}`개\n"
                  f"명령어: `{len(self.bot.commands)}`개\n"
                  f"확장: `{len(self.bot.cogs)}`개\n"
                  f"샤드: `{self.bot.shard_count}`개"
        )
        embed.add_field(
            name="현황",
            value=f"서버: `{len(self.bot.guilds)}`개\n"
                  f"유저: `{await self.bot.db.user.count_documents({})}`명\n"
                  f"미사용 유저: `{await self.bot.db.unused.count_documents({})}`명\n"
                  f"활성화 유저: `{await self.bot.db.user.count_documents({'latest_usage': {'$gte': round(time.time() - 86400 * count)}})}`명\n"
                  f"활성화 서버: `{await self.bot.db.guild.count_documents({'latest_usage': {'$gte': round(time.time() - 86400 * count)}})}`서버\n"
                  f"출석 유저 수: `{await read(None, 'attendance')}`명"
        )
        embed.add_field(
            name="DB",
            value=f"용량: `{naturalsize((await self.bot.db.command('collstats', 'user'))['size'])}`\n"
                  f"조회 지연 시간: `{round(t1 * 1000)}`ms\n"
                  f"업뎃 지연 시간: `{round(t2 * 1000)}`ms"
        )
        await ctx.reply(embed=embed)

    @commands.command(name="$로그", usage="ㄲ$로그 <날짜>")
    async def get_log(self, ctx: KkutbotContext, date: str = None):
        """해당 날짜의 로그 파일을 확인합니다."""
        if date is None:
            path = "logs/latest.log"
        else:
            path = f"logs/{date}.log.gz"
        await ctx.reply(file=discord.File(path))

    @commands.command(name="$정보", usage="ㄲ$정보 <유저>", rest_is_raw=False)
    async def user_info(self, ctx: KkutbotContext, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """유저의 (상세)정보를 출력합니다."""
        if user is None:
            cmd_data = await read(None, "commands")
            if "jisahku" not in cmd_data:
                cmd_data["jishaku"] = 0
            for k, v in cmd_data.copy().items():
                if k.startswith("jishaku "):
                    cmd_data["jishaku"] += v
                    del cmd_data[k]
            sorted_data = sorted(cmd_data.items(), key=lambda item: item[1], reverse=True)
            for content in split_string("\n".join(f"{k.replace('_', '$')}: `{v}`회" for k, v in dict(sorted_data).items())):
                await ctx.reply(content, escape_emoji_formatting=True, mention_author=True)
            public_data = deepcopy(await read(user))
            del public_data["commands"]
            del public_data["announcements"]
            for content in split_string("\n".join(f"{k}: `{v}`" for k, v in public_data.items())):
                await ctx.reply(content, escape_emoji_formatting=True, mention_author=True)
            return

        if not (await read(user, "registered")):
            return await ctx.reply(f"`{getattr(user, 'name', None)}`님은 끝봇의 유저가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in (await read(user)).items())):
            await ctx.reply(content, escape_emoji_formatting=True, mention_author=True)

    @commands.command(name="$서버정보", usage="ㄲ$서버정보 <서버>")
    async def guild_info(self, ctx: KkutbotContext, *, guild: discord.Guild = commands.CurrentGuild):
        """끝봇을 이용하는 서버의 상세 정보를 출력합니다."""
        if not (await self.bot.db.guild.find_one({"_id": guild.id})):
            return await ctx.reply("{denyed} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다.")
        guild_data = await read(guild)
        guild_data["name"] = guild.name
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in guild_data.items())):
            await ctx.reply(content, escape_emoji_formatting=True)

    @commands.command(name="$포인트", usage="ㄲ$포인트 <포인트> <유저>")
    async def give_point(self, ctx: KkutbotContext, amount: int = 1000, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """관리자 권한으로 포인트를 지급합니다."""
        await add(user, "points", amount)
        await ctx.reply("{done} 완료!")

    @commands.command(name="$메달", usage="ㄲ$메달 <메달> <유저>")
    async def give_medal(self, ctx: KkutbotContext, amount: int = 1000, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """관리자 권한으로 메달을 지급합니다."""
        await add(user, "medals", amount)
        await ctx.reply("{done} 완료!")

    @commands.command(name="$정보수정", usage="ㄲ$정보수정 <id>")
    async def modify_data(self, ctx: KkutbotContext, *, target: Union[int, str]):
        """
        대상의 정보를 수정합니다.
        id가 general이면 공용 데이터를 수정합니다.
        """
        embed = discord.Embed(
            title="데이터 수정하기",
            description=f"대상: {target}",
            color=config("colors.help")
        )
        view = ModifyData(ctx=ctx, target=target)
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.command(name="$통계삭제", usage="ㄲ$통계삭제 <유저>")
    async def delete_userdata(self, ctx: KkutbotContext, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """유저의 데이터를 초기화합니다."""
        if await self.bot.db.user.find_one({'_id': user.id}):
            await delete(user)
            await ctx.reply("{done} 완료!")
        else:
            await ctx.reply("{denyed} 해당 유저는 끝봇의 유저가 아닙니다.")

    @commands.command(name="$서버통계삭제", usage="ㄲ$서버통계삭제 <서버>")
    async def delete_guilddata(self, ctx: KkutbotContext, *, guild: discord.Guild = commands.CurrentGuild):
        """서버의 데이터를 초기화합니다."""
        if await self.bot.db.guild.find_one({"_id": guild.id}):
            await delete(guild)
            await ctx.reply("{done} 완료!")
        else:
            await ctx.reply("{denyed} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다.")

    @commands.command(name="$서버탈퇴", usage="ㄲ$서버탈퇴 <서버>", aliases=("$탈퇴", "$나가기"))
    async def leave_guild(self, ctx: KkutbotContext, *, guild: discord.Guild = commands.CurrentGuild):
        """서버를 나갑니다."""
        if await self.bot.db.guild.find_one({"_id": guild.id}):
            await guild.leave()
            await delete(guild)
            await ctx.reply("{done} 완료!")
        else:
            await ctx.reply("{denyed} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다.")

    @commands.command(name="$공지", usage="ㄲ$공지")
    async def announce_users(self, ctx: KkutbotContext):
        """끝봇의 유저들에게 공지를 전송합니다."""
        view = SendAnnouncement(ctx=ctx)
        view.message = await ctx.reply("버튼 눌러 공지 작성하기", view=view)

    @commands.command(name="$알림", usage="ㄲ$알림 <유저>")
    async def send_notice(self, ctx: KkutbotContext, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """유저에게 알림을 전송합니다."""
        view = SendNotice(ctx=ctx, target=user.id)
        view.message = await ctx.reply("버튼 눌러 알림 보내기", view=view)

    @commands.command(name="$차단", usage="ㄲ$차단 <유저> <기간(일)> <사유>", aliases=("$정지",))
    async def ban_user(self, ctx: KkutbotContext, user: discord.Member = commands.parameter(converter=KkutbotUserConverter), days: float = 1.0, *, reason: str = "없음"):
        """유저를 이용 정지 처리합니다."""
        if await read(user, "banned.isbanned"):
            return await ctx.reply("{denyed} 이미 차단된 유저입니다.")
        banned_since = time.time()
        await write(user, "banned", {"isbanned": True, "since": banned_since, "period": days, "reason": reason.lstrip()})
        await user.send(
            f"당신은 `끝봇 이용 {days}일 정지` 처리되었습니다.\n\n"
            f"사유: `{reason.lstrip()}` \n\n차단 시작: <t:{round(banned_since)}> \n\n"
            f"차단 해제: <t:{round(banned_since + 86400 * days)}> (<t:{round(banned_since + 86400 * days)}:R>)\n\n"
            f"끝봇 공식 커뮤니티에서 차단 해제를 요청할 수 있습니다.",
            view=ServerInvite("차단 해제 요청하기")
        )
        await ctx.reply("{done} 완료!")

    @commands.command(name="$차단해제", usage="ㄲ$차단해제 <유저>", aliases=("$정지해제",))
    async def unban_user(self, ctx: KkutbotContext, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """유저의 이용 정지 처리를 해제합니다."""
        if await read(user, "banned.isbanned"):
            await write(user, "banned", {"isbanned": False, "since": 0, "period": 0, "reason": None})
            await ctx.reply("{done} 완료!")
            await user.send("당신은 관리자에 의해 `끝봇 이용 정지` 처리가 해제되었습니다. 다음부터는 조심해주세요!")
        else:
            await ctx.reply("{denyed} 현재 차단되지 않은 유저입니다.")

    @commands.command(name="$차단목록", usage="ㄲ$정지목록", aliases=("$정지목록", "$정지리스트", "$차단리스트"))
    async def blocked_list(self, ctx: KkutbotContext):
        """정지된 유저의 목록을 확인합니다."""
        banned_users = await (self.bot.db.user.find({"banned.isbanned": True})).to_list(None)
        if not banned_users:
            return await ctx.reply("{help} 현재 차단된 유저가 없습니다.")
        else:
            embed = discord.Embed(
                title="차단 유저 목록",
                color=config("colors.help")
            )
            for user in banned_users:
                embed.add_field(
                    name=f"**{user['name']}** - `{user['_id']}`\n",
                    value=f"차단 기간: `{user['banned']['period']}`일, 차단 사유: {user['banned']['reason']}"
                )
            await ctx.reply(embed=embed)

    @commands.command(name="$정리", usage="ㄲ$정리")
    async def move_unused_users(self, ctx: KkutbotContext, days: int = 7, command_usage: int = 10, delete_data: str = 'n'):
        """미사용 유저들을 정리합니다."""
        cleaned = 0
        deleted = 0
        if delete_data == "y":
            deleted = await self.bot.db.unused.count_documents()
            await self.bot.db.unused.drop()
        async for user in self.bot.db.user.find({
            "latest_usage": {"$lt": time.time() - 86400 * days},
            "command_used": {"$lt": command_usage}
        }):
            await self.bot.db.unused.insert_one(user)
            await self.bot.db.user.delete_one({"_id": user["_id"]})
            cleaned += 1
        await ctx.reply(f"{{done}} `{cleaned}`명 데이터 보존 처리, `{deleted}`명 데이터 삭제 완료!")


async def setup(bot: Kkutbot):
    await bot.add_cog(Admin(bot))
