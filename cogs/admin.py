import asyncio
import operator
import time
from datetime import datetime

import discord
import psutil
from discord.ext import commands
from discord.utils import escape_markdown as e_mk
from humanize import naturalsize

from ext.converter import SpecialMemberConverter
from ext.core import Kkutbot, KkutbotContext
from ext.db import add, config, delete, read, read_hanmaru, write
from ext.utils import is_admin, split_string


class Admin(commands.Cog, name="관리자"):
    """관리자 전용 명령어들이 있는 카테고리 입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="$현황", usage="ㄲ$현황", aliases=("ㅎ", "$ㅎ"), hidden=True)
    @commands.is_owner()
    async def kkutbot_status(self, ctx: KkutbotContext, count: float = 7):
        """봇의 현황을 확인합니다."""
        embed = discord.Embed(color=config('colors.general'))
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
            f"유저: `{self.bot.db.user.count_documents({})}`명\n"
            f"미사용 유저: `{self.bot.db.unused.count_documents({})}`명\n"
            f"활성화: `{self.bot.db.user.count_documents({'last_command': {'$gt': time.time() - 86400 * count}})}`명\n"
            f"출석 유저 수: `{read(None, 'daily')}`명"
        )
        mem = psutil.virtual_memory()
        embed.add_field(
            name="호스팅",
            value=f"CPU: `{psutil.cpu_percent()}% ({round((psutil.cpu_freq().current / 1000), 2)} GHz)`\n"
                  f"RAM: `{naturalsize(mem.used)} / {naturalsize(mem.total)}`\n"
                  f"온도: `{psutil.sensors_temperatures()['cpu_thermal'][0].current if hasattr(psutil, 'sensors_temperatures') else '측정 불가'}`℃\n"
                  f"상세 정보: [링크1]({config('links.monitoring.pm2')}) [링크2]({config('links.monitoring.mongo')})"
        )
        await ctx.send(embed=embed)

    @commands.command(name="$종료", usage="ㄲ$종료", aliases=("ㅈ", "$ㅈ"), hidden=True)
    @commands.is_owner()
    async def logout(self, ctx: KkutbotContext):
        """봇을 종료합니다."""
        await ctx.send("{done} 완료! 로그아웃 되었습니다.")
        await self.bot.close()

    @commands.command(name="$서버", usage="ㄲ$서버 <키>", hidden=True)
    @commands.is_owner()
    async def servers(self, ctx: KkutbotContext, key: str = "서버"):
        """끝봇이 참가중인 서버의 목록을 키에 따라 정렬 후 확인합니다. (비공개 서버에서 사용시 TOS 위반이 아님)

        <키 목록>
        서버, 유저(멤버), 샤드, 아이디
        """
        if key == "서버":
            callback = lambda guild: read(guild, 'command_used')  # noqa: E731
        elif key in ("유저", "멤버"):
            callback = lambda guild: guild.member_count  # noqa: E731
        elif key == "샤드":
            callback = lambda guild: guild.shard_id  # noqa: E731
        elif key == "아이디":
            callback = lambda guild: guild.id  # noqa: E731
        else:
            return await ctx.send(f"`{key}`는 없는 키 입니다.")

        for content in split_string("\n".join(f"{e_mk(g.name)[:10]} [`{g.id}`]  |  멤버: `{g.member_count}`명 | 샤드: `{g.shard_id}`번 | 명령어: `{read(g, 'command_used') or 0}`회" for g in sorted(self.bot.guilds, key=callback, reverse=True))):
            await ctx.send(content)

    @commands.command(name="$정보", usage="ㄲ$정보 <유저>", rest_is_raw=False)
    @commands.check(is_admin)
    async def user_info(self, ctx: KkutbotContext, *, user: SpecialMemberConverter = None):
        """유저의 (상세)정보를 출력합니다."""
        if user is None:  # check public data
            for content in split_string("\n".join(f"{k.replace('_', '$')}: `{v}`회" for k, v in dict(sorted(read(None, 'commands').items(), key=operator.itemgetter(1), reverse=True)).items())):
                await ctx.send(content)
            public_data = read(user).copy()
            del public_data['commands']
            for content in split_string("\n".join(f"{k}: `{v}`" for k, v in public_data.items())):
                return await ctx.send(content)

        if not read(user, 'register_date'):
            return await ctx.send(f"`{getattr(user, 'name', None)}`님은 끝봇의 유저가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in read(user).items())):
            await ctx.send(content, escape_emoji_formatting=True)

    @commands.command(name="$마루정보", usage="ㄲ$마루정보 <유저>")
    @commands.check(is_admin)
    async def hanmaru_user_info(self, ctx: KkutbotContext, *, user: SpecialMemberConverter()):
        """유저의 한마루 정보를 출력합니다."""
        if not self.bot.db.hanmaru.find_one({'_id': user.id}):
            return await ctx.send(f"`{getattr(user, 'name', None)}`님은 한마루의 유저가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in read_hanmaru(user).items())):
            await ctx.send(content, escape_emoji_formatting=True)

    @commands.command(name="$서버정보", usage="ㄲ$서버정보 <서버>")
    @commands.check(is_admin)
    async def guild_info(self, ctx: KkutbotContext, *, guild: discord.Guild = None):
        """끝봇을 이용하는 서버의 상세 정보를 출력합니다."""
        if guild is None:
            guild = ctx.guild

        if not self.bot.db.guild.find_one({'_id': guild.id}):
            return await ctx.send("해당 서버는 끝봇을 사용중인 서버가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in read(guild).items())):
            await ctx.send(content, escape_emoji_formatting=True)

    @commands.command(name="$포인트", usage="ㄲ$포인트 <포인트> <유저>")
    @commands.check(is_admin)
    async def give_point(self, ctx: KkutbotContext, amount: int = 1000, *, user: SpecialMemberConverter):
        """관리자 권한으로 포인트를 지급합니다."""
        add(user, 'points', amount)
        await ctx.send("{done} 완료!")

    @commands.command(name="$메달", usage="ㄲ$메달 <메달> <유저>")
    @commands.check(is_admin)
    async def give_medal(self, ctx: KkutbotContext, amount: int = 1000, *, user: SpecialMemberConverter):
        """관리자 권한으로 메달을 지급합니다."""
        add(user, 'medal', amount)
        await ctx.send("{done} 완료!")

    @commands.command(name="$통계삭제", usage="ㄲ$통계삭제 <유저>", hidden=True)
    @commands.is_owner()
    async def delete_user(self, ctx: KkutbotContext, *, user: SpecialMemberConverter()):
        """유저의 데이터를 초기화합니다."""
        if self.bot.db.user.find_one({'_id': user.id}):
            delete(user)
            await ctx.send("{done} 완료!")
        else:
            await ctx.send("{denyed} 해당 유저는 끝봇의 유저가 아닙니다.")

    @commands.command(name="$공지", usage="ㄲ$공지 <제목> | <내용>", hidden=True)
    @commands.is_owner()
    async def announce_users(self, ctx: KkutbotContext, *, ann: str):
        """끝봇의 유저들에게 공지를 전송합니다."""
        title, desc = ann.replace("ㄲ$공지 ", "").split(" | ")
        embed = discord.Embed(
            title=f"**{ctx.author.name}** 님의 메일함",
            description="> 1주일간 읽지 않은 메일 `1` 개",
            color=config('colors.help')
        )
        embed.add_field(name=f"{title} - `1초 전`", value=desc)
        await ctx.send(content="> 공지 미리보기 ('ㅇ'로 공지 전송하기, 'ㄴ'로 전송 취소하기)", embed=embed)
        try:
            m = await self.bot.wait_for(
                'message',
                check=lambda _m: _m.content in ("ㅇ", "ㄴ") and _m.author == ctx.author and _m.channel == ctx.channel,
                timeout=30
            )
            if m.content == "ㅇ":
                self.bot.db.user.update_many(
                    {},
                    {
                        '$push': {'mail': {'title': title, 'value': desc, 'time': datetime.now()}},
                        '$set': {'alert.mail': False}
                    }
                )
                await ctx.send("{done} 완료!")
            elif m.content == "ㄴ":
                raise asyncio.TimeoutError
        except asyncio.TimeoutError:
            await ctx.send("공지 전송이 취소되었습니다.")
            return

    @commands.command(name="$알림", usage="ㄲ$알림 <유저> <내용>")
    @commands.check(is_admin)
    async def send_notice(self, ctx: KkutbotContext, user: SpecialMemberConverter(), *, word: str):
        """유저에게 알림을 전송합니다."""
        self.bot.db.user.update_one(
            {'_id': user.id},
            {
                '$push': {'mail': {'title': "관리자로부터의 알림", 'value': word.lstrip(), 'time': datetime.now()}},
                '$set': {'alert.mail': False}
            }
        )
        await ctx.send("{done} 완료!")

    @commands.command(name="$정지", usage="ㄲ$정지 <유저> <사유>", aliases=('차단',))
    @commands.check(is_admin)
    async def block_user(self, ctx: KkutbotContext, user: SpecialMemberConverter(), days: int = 1, *, reason: str = "없음"):
        """유저를 이용 정지 처리합니다."""
        if read(user, 'banned'):
            return await ctx.send("{denyed} 이미 정지 된 유저입니다.")
        write(user, 'banned', True)
        await user.send(
            f"당신은 `끝봇 이용 {days}일 정지` 처리 되었습니다.\n\n"
            f"사유: `{reason.lstrip()}` \n\n차단 일시: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')} \n\n"
            f"끝봇 공식 커뮤니티에서 정지 해제를 요청 할 수 있습니다.\n\n{config('links.invite.server')}")
        await ctx.send("{done} 완료!")

    @commands.command(name="$정지해제", usage="ㄲ$정지해제 <유저>", aliases=('차단해제',))
    @commands.check(is_admin)
    async def unblock_user(self, ctx: KkutbotContext, *, user: SpecialMemberConverter()):
        """유저의 이용 정지 처리를 해제합니다."""
        if read(user, 'banned'):
            write(user, 'banned', False)
            await ctx.send("{done} 완료!")
            await user.send("당신은 `끝봇 이용 정지` 처리가 해제 되었습니다. 다음부터는 조심해 주세요!")
        else:
            await ctx.send("{denyed} 현재 이용 정지 되지 않은 유저입니다.")

    async def update_user_name(self, target: int, counter: int) -> int:  # update cached username
        username = (self.bot.get_user(target) or await self.bot.fetch_user(target)).name
        write(target, '_name', username)
        return counter + 1

    @commands.command(name="$캐시", usage="ㄲ$캐시", hidden=True)
    @commands.is_owner()
    async def add_user_cache(self, ctx: KkutbotContext):
        """유저 캐시를 리프레시합니다."""
        counter = 0
        users = self.bot.db.user.count_documents({"_name": None})
        msg = await ctx.send(f"진행중... (`{counter}`/`{users}`)")
        for t in self.bot.db.user.find({"_name": None}):
            counter = await self.update_user_name(t['_id'], counter)
            await msg.edit(content=f"진행중... (`{counter}`/`{users}`)")
        await ctx.send("{done} 완료!")

    @commands.command(name="$정리", usage="ㄲ$정리")
    async def move_unused_users(self, ctx: KkutbotContext, days: int = 7, command_usage: int = 10, delete_data: str = 'n'):
        """미사용 유저들을 정리합니다."""
        cleaned = 0
        deleted = 0
        if delete_data == 'y':
            deleted = self.bot.db.unused.count_documents()
            self.bot.db.unused.drop()
        for user in self.bot.db.user.find({
            'last_command': {'$lt': time.time() - 86400 * days},
            'command_used': {'$lt': command_usage}
        }):
            self.bot.db.unused.insert_one(user)
            self.bot.db.user.delete_one({"_id": user['_id']})
            cleaned += 1
        await ctx.send(f"{{done}} `{cleaned}` 명 데이터 보존 처리, `{deleted}` 명 데이터 삭제 완료!")


def setup(bot: Kkutbot):
    bot.add_cog(Admin(bot))
