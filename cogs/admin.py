import operator
import time
from copy import deepcopy

import discord
from discord.ext import commands
from humanize import naturalsize

from core import Kkutbot, KkutbotContext
from tools.converter import KkutbotUserConverter
from tools.db import add, config, delete, read, write
from tools.utils import get_tier, get_winrate, is_admin, split_string
from tools.views import SendAnnouncement, SendNotice, ServerInvite


class Admin(commands.Cog, name="관리자"):
    """관리자 전용 명령어들이 있는 카테고리입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    def cog_check(self, ctx):
        return is_admin(ctx)

    @commands.command(name="$현황", usage="ㄲ$현황", aliases=("ㅎ", "$ㅎ"))
    async def kkutbot_status(self, ctx: KkutbotContext, count: int = 7):
        """봇의 현황을 확인합니다."""
        embed = discord.Embed(color=config('colors.general'))

        t1 = time.time()
        await self.bot.db.general.find_one()
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
                  f"활성화: `{await self.bot.db.user.count_documents({'latest_command': {'$gte': round(time.time() - 86400 * count)}})}`명\n"
                  f"출석 유저 수: `{await read(None, 'attendance')}`명"
        )
        embed.add_field(
            name="DB",
            value=f"용량: `{naturalsize((await self.bot.db.command('collstats', 'user'))['size'])}`\n"
                  f"조회 지연시간: `{round(t1 * 1000)}`ms\n"
                  f"업뎃 지연시간: `{round(t2 * 1000)}`ms"
        )
        await ctx.send(embed=embed)

    # @commands.command(name="$서버", usage="ㄲ$서버 <키>", hidden=True)
    # @commands.is_owner()
    # async def servers(self, ctx: KkutbotContext, key: str = "서버"):
    #     """끝봇이 참가중인 서버의 목록을 키에 따라 정렬 후 확인합니다. (비공개 서버에서 사용시 TOS 위반이 아님)
    #
    #     **<키 목록>**
    #     서버, 유저(멤버), 샤드, 아이디
    #     """
    #     async def callback(guild):
    #         if key == "서버":
    #             return await read(guild, 'command_used')
    #         elif key in ("유저", "멤버"):
    #             return guild.member_count
    #         elif key == "샤드":
    #             return guild.shard_id
    #         elif key == "아이디":
    #             return guild.id
    #         else:
    #             raise KeyError(f"`{key}`(은)는 없는 키 입니다.")
    #
    #     for content in split_string("\n".join(f"{e_mk(g.name)[:10]} [`{g.id}`]  |  멤버: `{g.member_count}`명 | 샤드: `{g.shard_id}`번 | 명령어: `{await read(g, 'command_used') or 0}`회" for g in sorted(self.bot.guilds, key=callback, reverse=True))):
    #         await ctx.send(content, escape_emoji_formatting=True)

    @commands.command(name="$정보", usage="ㄲ$정보 <유저>", rest_is_raw=False)
    async def user_info(self, ctx: KkutbotContext, *, user: KkutbotUserConverter() = None):  # noqa
        """유저의 (상세)정보를 출력합니다."""
        if user is None:  # check public data
            for content in split_string("\n".join(f"{k.replace('_', '$')}: `{v}`회" for k, v in dict(sorted((await read(None, 'commands')).items(), key=operator.itemgetter(1), reverse=True)).items())):
                await ctx.send(content, escape_emoji_formatting=True)
            public_data = deepcopy(await read(user))
            del public_data['commands']
            for content in split_string("\n".join(f"{k}: `{v}`" for k, v in public_data.items())):
                await ctx.send(content, escape_emoji_formatting=True)
            return

        if not (await read(user, 'registered')):
            return await ctx.send(f"`{getattr(user, 'name', None)}`님은 끝봇의 유저가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in (await read(user)).items())):
            await ctx.send(content, escape_emoji_formatting=True)

    @commands.command(name="$서버정보", usage="ㄲ$서버정보 <서버>")
    async def guild_info(self, ctx: KkutbotContext, *, guild: discord.Guild = None):
        """끝봇을 이용하는 서버의 상세 정보를 출력합니다."""
        if guild is None:
            guild = ctx.guild

        if not (await self.bot.db.guild.find_one({'_id': guild.id})):
            return await ctx.send("{denyed} 해당 서버는 끝봇을 사용중인 서버가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in (await read(guild)).items())):
            await ctx.send(content, escape_emoji_formatting=True)

    @commands.command(name="$포인트", usage="ㄲ$포인트 <포인트> <유저>")
    async def give_point(self, ctx: KkutbotContext, amount: int = 1000, *, user: KkutbotUserConverter()):  # noqa
        """관리자 권한으로 포인트를 지급합니다."""
        await add(user, 'points', amount)
        await ctx.send("{done} 완료!")

    @commands.command(name="$메달", usage="ㄲ$메달 <메달> <유저>")
    async def give_medal(self, ctx: KkutbotContext, amount: int = 1000, *, user: KkutbotUserConverter()):  # noqa
        """관리자 권한으로 메달을 지급합니다."""
        await add(user, 'medals', amount)
        await ctx.send("{done} 완료!")

    @commands.command(name="$통계삭제", usage="ㄲ$통계삭제 <유저>")
    async def delete_userdata(self, ctx: KkutbotContext, *, user: KkutbotUserConverter()):  # noqa
        """유저의 데이터를 초기화합니다."""
        if await self.bot.db.user.find_one({'_id': user.id}):
            await delete(user)
            await ctx.send("{done} 완료!")
        else:
            await ctx.send("{denyed} 해당 유저는 끝봇의 유저가 아닙니다.")

    @commands.command(name="$서버통계삭제", usage="ㄲ$서버통계삭제 <서버>")
    async def delete_guilddata(self, ctx: KkutbotContext, *, guild: discord.Guild):  # noqa
        """유저의 데이터를 초기화합니다."""
        if await self.bot.db.guild.find_one({'_id': guild.id}):
            await delete(guild)
            await ctx.send("{done} 완료!")
        else:
            await ctx.send("{denyed} 해당 서버는 끝봇을 사용중인 서버가 아닙니다.")

    @commands.command(name="$공지", usage="ㄲ$공지")
    async def announce_users(self, ctx: KkutbotContext):
        """끝봇의 유저들에게 공지를 전송합니다."""
        view = SendAnnouncement(ctx=ctx)
        await ctx.send("버튼 눌러 공지 작성하기", view=view)

    @commands.command(name="$알림", usage="ㄲ$알림 <유저>")
    async def send_notice(self, ctx: KkutbotContext, user: KkutbotUserConverter()):  # noqa
        """유저에게 알림을 전송합니다."""
        view = SendNotice(ctx=ctx, target=user.id)
        await ctx.send("버튼 눌러 알림 보내기", view=view)

    @commands.command(name="$차단", usage="ㄲ$차단 <유저> <기간(일)> <사유>", aliases=("$정지",))
    async def ban_user(self, ctx: KkutbotContext, user: KkutbotUserConverter(), days: float = 1.0, *, reason: str = "없음"):  # noqa
        """유저를 이용 정지 처리합니다."""
        if await read(user, 'banned.isbanned'):
            return await ctx.send("{denyed} 이미 차단된 유저입니다.")
        banned_since = time.time()
        await write(user, "banned", {"isbanned": True, "since": banned_since, "period": days, "reason": reason.lstrip()})
        await user.send(
            f"당신은 `끝봇 이용 {days}일 정지` 처리 되었습니다.\n\n"
            f"사유: `{reason.lstrip()}` \n\n차단 시작: <t:{round(banned_since)}> \n\n"
            f"차단 해제: <t:{round(banned_since + 86400 * days)}> (<t:{round(banned_since + 86400 * days)}:R>)\n\n"
            f"끝봇 공식 커뮤니티에서 차단 해제를 요청할 수 있습니다.",
            view=ServerInvite()
        )
        await ctx.send("{done} 완료!")

    @commands.command(name="$차단해제", usage="ㄲ$차단해제 <유저>", aliases=("$정지해제",))
    async def unban_user(self, ctx: KkutbotContext, *, user: KkutbotUserConverter()):  # noqa
        """유저의 이용 정지 처리를 해제합니다."""
        if await read(user, 'banned.isbanned'):
            await write(user, "banned", {"isbanned": False, "since": 0, "period": 0, "reason": None})
            await ctx.send("{done} 완료!")
            await user.send("당신은 관리자에 의해 `끝봇 이용 정지` 처리가 해제되었습니다. 다음부터는 조심해주세요!")
        else:
            await ctx.send("{denyed} 현재 차단되지 않은 유저입니다.")

    @commands.command(name="$차단목록", usage="ㄲ$정지목록", aliases=("$정지목록", "$정지리스트", "$차단리스트"))
    async def blocked_list(self, ctx: KkutbotContext):
        """정지된 유저의 목록을 확인합니다."""
        banned_users = await (self.bot.db.user.find({"banned.isbanned": True})).to_list(None)
        if not banned_users:
            return await ctx.send("{help} 현재 차단된 유저가 없습니다.")
        else:
            embed = discord.Embed(
                title="차단 유저 목록",
                color=config("colors.help")
            )
            for user in banned_users:
                print(banned_users)
                embed.add_field(
                    name=f"**{user['name']}** - `{user['_id']}`\n",
                    value=f"차단기간: `{user['banned']['period']}`일, 차단사유: {user['banned']['reason']}"
                )
            await ctx.send(embed=embed)

    async def update_user_name(self, target: int):
        username = (self.bot.get_user(target) or await self.bot.fetch_user(target)).name
        await write(target, 'name', username)

    @staticmethod
    async def update_game_winrate(target: int):
        for gamemode in config('modelist').values():
            if (await read(target, f'game.{gamemode}.winrate')) != (winrate := await get_winrate(target, gamemode)):
                await write(target, f'game.{gamemode}.winrate', winrate)

    @staticmethod
    async def update_game_tier(target: int):
        for gamemode in ("rank_solo", "rank_online"):
            if (await read(target, f'game.{gamemode}.tier')) != (tier := await get_tier(target, gamemode, emoji=False)):
                await write(target, f'game.{gamemode}.tier', tier)

    @commands.command(name="$캐시", usage="ㄲ$캐시")
    async def add_user_cache(self, ctx: KkutbotContext):
        """유저 캐시를 새로고침합니다."""
        users = await self.bot.db.user.count_documents({"name": None})
        msg = await ctx.send(f"이름 캐싱 진행중... (`0`/`{users}`)")
        for n, target in enumerate(await self.bot.db.user.find({"name": None})):
            await self.update_user_name(target['_id'])
            await msg.edit(content=f"이름 캐싱 진행중... (`{n + 1}`/`{users}`)")
        await ctx.send("{done} 이름 캐싱 완료!")

        users = await self.bot.db.user.count_documents({})
        msg = await ctx.send(f"게임 데이터 캐싱 진행중... (`0`/`{users}`)")
        for n, target in enumerate(await self.bot.db.user.find()):
            await self.update_game_winrate(target['_id'])
            await self.update_game_tier(target['_id'])
            await msg.edit(content=f"진행중... (`{n + 1}`/`{users}`)")
        await ctx.send("{done} 게임 데이터 캐싱 완료!")

    @commands.command(name="$정리", usage="ㄲ$정리")
    async def move_unused_users(self, ctx: KkutbotContext, days: int = 7, command_usage: int = 10, delete_data: str = 'n'):
        """미사용 유저들을 정리합니다."""
        cleaned = 0
        deleted = 0
        if delete_data == 'y':
            deleted = await self.bot.db.unused.count_documents()
            await self.bot.db.unused.drop()
        async for user in self.bot.db.user.find({
            'latest_usage': {'$lt': time.time() - 86400 * days},
            'command_used': {'$lt': command_usage}
        }):
            await self.bot.db.unused.insert_one(user)
            await self.bot.db.user.delete_one({"_id": user['_id']})
            cleaned += 1
        await ctx.send(f"{{done}} `{cleaned}` 명 데이터 보존 처리, `{deleted}` 명 데이터 삭제 완료!")


async def setup(bot: Kkutbot):
    await bot.add_cog(Admin(bot))
