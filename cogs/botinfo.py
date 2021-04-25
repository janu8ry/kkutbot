import discord
from discord.ext import commands

from ext.db import config
from ext.core import Kkutbot, KkutbotContext


class BotInfo(commands.Cog, name="일반"):
    """봇의 기본 정보에 대한 카테고리입니다!"""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="도움", usage="ㄲ도움 <명령어/카테고리>", aliases=("도움말", "help", "ㄷㅇ"))
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def help(self, ctx: KkutbotContext, *, command_name=None):
        """끝봇의 커맨드 목록을 확인합니다."""
        cog_list = ("일반", "게임", "사용자", "경제", "기타")
        if not command_name:
            embed = discord.Embed(
                title="끝봇 도움말",
                description=self.bot.description,
                color=config('colors.help')
            )
            for x in cog_list:
                embed.add_field(
                    name=x,
                    value=f"`{'`, `'.join([c.name for c in self.bot.cogs[x].get_commands() if not c.hidden])}`",
                    inline=False
                )
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.set_footer(text="ㄲ도움 (명령어/카테고리 이름)을 입력해서 더 자세한 정보를 알아보세요!")
            return await ctx.send(embed=embed)
        elif command_name == "관리자":
            cog_data = self.bot.get_cog("관리자")
            if ctx.author.id == self.bot.owner_id:
                admin_command_list = [c.name for c in cog_data.get_commands()]
            elif ctx.author.id in config('admin'):
                admin_command_list = [c.name for c in cog_data.get_commands() if not c.hidden]
            else:
                return await ctx.send("{denyed} 존재하지 않는 명령어 또는 카테고리입니다.")
            embed = discord.Embed(
                title=f"카테고리 정보 | {cog_data.qualified_name}",
                description=cog_data.description,
                color=config('colors.help')
            )
            embed.add_field(name="명령어 목록", value=f"`{'`, `'.join(admin_command_list)}`")
            return await ctx.send(embed=embed)
        elif command_name in self.bot.cogs:
            cog_data = self.bot.get_cog(command_name)
            embed = discord.Embed(
                title=f"카테고리 정보 | {cog_data.qualified_name}",
                description=cog_data.description,
                color=config('colors.help')
            )
            embed.add_field(
                name="명령어 목록",
                value=f"`{'`, `'.join([c.name for c in cog_data.get_commands()])}`"
            )
            return await ctx.send(embed=embed)
        cmd = self.bot.get_command(command_name)
        if not cmd or (command_name.startswith("$") and (ctx.author.id not in config('admin'))) or self.bot.get_command(command_name).hidden:
            return await ctx.send("{denyed} 존재하지 않는 명령어 또는 카테고리입니다.")
        embed = discord.Embed(
            title=f"명령어 정보 | {cmd}",
            description=f"{cmd.help}\n> [상세 도움말]({config('links.blog')}/blog/명령어-{cmd.name})",
            color=config('colors.help')
        )
        embed.add_field(name="사용법", value=f"`{cmd.usage}`", inline=False)
        embed.add_field(name="다른 이름", value=f"`{'`, `'.join(cmd.aliases) if cmd.aliases else '없음'}`", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="정보", usage="ㄲ정보", aliases=("봇정보", "봇", "저작권", "ㅈㅂ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def kkutbot_info(self, ctx: KkutbotContext):
        """끝봇의 정보를 확인합니다."""
        embed = discord.Embed(
            title="끝봇 정보",
            description=f"버전 {self.bot.__version__} | {self.bot.version_info}",
            color=config('colors.general')
        )
        desc = {"개발자": f'{(await self.bot.application_info()).owner}', "개발 언어": f'python 3.8.6\n(discord.py {discord.__version__})',
                "서버 /사용자 수, 샤드": f'`{len(self.bot.guilds)}`개/`{self.bot.db.user.count_documents({})}`명, `{ctx.guild.shard_id + 1}/{self.bot.shard_count}`',
                "크레딧": '끝봇 개발에 도움을 주신\n`서진`님, 프로필 사진을\n만들어 주신`! Tim23`\n님께 감사드립니다.',
                "저작권": 'Icon made by `Pixel\nperfect`, `Freepik`,\n`Good Ware`\nfrom [flaticon](https://www.flaticon.com)',
                "링크": f"[봇 초대하기]({config('links.invite.bot')})\n[웹사이트]({config('links.blog')})\n[koreanbots]({config('links.koreanbots')})\n[github]({config('links.github')})"}
        for k, v in desc.items():
            embed.add_field(name=k, value=v)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="초대", usage="ㄲ초대", aliases=("링크", "ㅊㄷ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def kkutbot_invite(self, ctx: KkutbotContext):
        """끝봇을 초대할 때 필요한 링크를 확인합니다."""
        embed = discord.Embed(title="끝봇 초대하기",
                              description="끝봇을 사용하고 싶다면 아래 링크를 통해\n"
                                          "끝봇을 당신의 서버에 초대하세요!\n\n"
                                          "끝봇을 초대하려면 해당 서버에서\n"
                                          "**서버 관리하기** (필수), **메시지 관리하기** (선택)\n"
                                          "권한을 가지고 있어야 합니다.",
                              color=config('colors.general')
                              )
        embed.add_field(name="초대 링크", value=f"[끝봇 초대링크 바로가기]({config('links.invite.bot')})")
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="커뮤니티", usage="ㄲ커뮤니티", aliases=("지원", "서버", "디스코드", "디코"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def community_invite(self, ctx: KkutbotContext):
        """끝봇 공식 커뮤니티에 참가하기 위한 초대장 확인합니다."""
        embed = discord.Embed(title="끝봇 커뮤니티 참가하기",
                              description=f"[끝봇 커뮤니티]({config('links.invite.server')})에 참가하여, \n"
                                          "주요 공지사항을 확인하고, 건의사항이나 버그를 제보하고,\n"
                                          "다른 유저들과 교류해 보세요!",
                              color=config('colors.general')
                              )
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)


def setup(bot: Kkutbot):
    bot.add_cog(BotInfo(bot))
