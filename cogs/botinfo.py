import discord
from discord.ext import commands

from core import Kkutbot, KkutbotContext
from tools.config import config
from tools.utils import is_admin
from tools.views import BaseView, BotInvite, ServerInvite


class HelpDropdown(discord.ui.Select):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        cog_list = list(dict(ctx.bot.cogs).keys())
        cog_list.remove("지샤쿠")
        if not is_admin(ctx):
            cog_list.remove("관리자")
        options = []
        for cogname in reversed(cog_list):
            cog = ctx.bot.get_cog(cogname)
            option = discord.SelectOption(
                label=cog.qualified_name,
                value=cog.qualified_name,
                description=cog.description,
                emoji="<:help:715549237022163005>"
            )
            options.append(option)
        super().__init__(placeholder="카테고리를 선택해 주세요.", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        cog_data = self.ctx.bot.get_cog(self.values[0])
        embed = discord.Embed(
            title=f"{{help}} {self.values[0]} 명령어 도움말",
            description=cog_data.description,
            color=config("colors.help")
        )
        for cmd in cog_data.get_commands():
            if not cmd.hidden:
                embed.add_field(
                    name=f"🔹 {cmd.name}",
                    value=f"{cmd.help}\n\n사용 방법: `{cmd.usage}`",
                    inline=False
                )
        embed.set_footer(text="도움이 필요하다면 서포트 서버에 참가해보세요!")
        self.view.children[0].disabled = False  # noqa
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpMenu(BaseView):
    def __init__(self, ctx: commands.Context, home_embed: discord.Embed):
        super().__init__(ctx=ctx, author_only=True)
        self.home_embed = home_embed
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config("links.invite.bot")
            )
        )
        self.add_item(
            discord.ui.Button(
                label="서포트 서버 참가하기", style=discord.ButtonStyle.grey, url=config("links.invite.server")
            )
        )
        self.add_item(
            discord.ui.Button(
                label="하트 누르기", style=discord.ButtonStyle.red, url=f"{config('links.koreanbots')}/vote"
            )
        )
        self.add_item(HelpDropdown(ctx))

    @discord.ui.button(label="홈", style=discord.ButtonStyle.blurple, emoji="🏠", row=2, disabled=True)
    async def go_home(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(embed=self.home_embed, view=self)


class BotInfo(commands.Cog, name="일반"):
    """봇의 기본 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="도움", usage="ㄲ도움", aliases=("도움말", "help", "ㄷㅇ", "ㄷ", "정보", "봇정보", "ㅈㅂ"))
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def help(self, ctx: KkutbotContext):
        """끝봇의 명령어 목록을 확인합니다."""
        embed = discord.Embed(
            title="{help} 끝봇 도움말",
            description="끝봇은 끝말잇기가 주 기능인 디스코드 봇입니다!\n\n"
                        f"**개발자**: `{(await self.bot.application_info()).owner}`\n"
                        f"**서버 /사용자 수**: `{len(self.bot.guilds)}`개/`{await self.bot.db.user.count_documents({})}`명\n"
                        f"**업타임**: ~ <t:{self.bot.started_at}:R>부터\n\n"
                        "개발에 도움을 주신 `서진#5826`님,\n프로필 사진을 만들어 주신 `! Tim23#1475` 님께 감사드립니다!\n"
                        "Icon made from [flaticon](https://www.flaticon.com)",
            color=config('colors.help')
        )
        embed.add_field(
            name="기타 링크",
            value=f"[웹사이트]({config('links.blog')})  [koreanbots]({config('links.koreanbots')})  [github]({config('links.github')})  [개인정보처리방침]({config('links.privacy-policy')})"
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="아래 메뉴를 클릭해서 명령어 도움말을 확인해 보세요!")
        view = HelpMenu(ctx=ctx, home_embed=embed)
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.command(name="초대", usage="ㄲ초대", aliases=("링크", "ㅊㄷ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def kkutbot_invite(self, ctx: KkutbotContext):
        """끝봇을 초대할 때 필요한 링크를 확인합니다."""
        embed = discord.Embed(title="{invitation} 끝봇 초대하기",
                              description="끝봇을 사용하고 싶다면 아래 버튼을 클릭하여\n"
                                          "끝봇을 당신의 서버에 초대하세요!\n\n"
                                          f"끝봇을 서버에 초대할 경우, [약관]({config('links.privacy-policy')})에 동의한 것으로 간주됩니다.",
                              color=config('colors.general')
                              )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed, view=BotInvite())

    @commands.command(name="커뮤니티", usage="ㄲ커뮤니티", aliases=("지원", "서버", "디스코드", "디코", "ㅋㅁㄴㅌ", "ㄷㅋ"))
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def community_invite(self, ctx: KkutbotContext):
        """끝봇 공식 커뮤니티에 참가하기 위한 초대장을 확인합니다."""
        embed = discord.Embed(title="{invitation} 끝봇 커뮤니티 참가하기",
                              description="끝봇 커뮤니티에 참가하여,\n"
                                          "주요 공지사항을 확인하고, 건의사항이나 버그를 제보하고,\n"
                                          "다른 유저들과 교류해 보세요!",
                              color=config('colors.general')
                              )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=embed, view=ServerInvite())

    @commands.command(name="핑", usage="ㄲ핑")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def ping(self, ctx: KkutbotContext):
        """끝봇의 응답 속도를 확인합니다.
        핑이 지속적으로 400ms 이상일 경우, 관리자에게 제보 부탁드립니다.
        """
        message = await ctx.reply("걸린 시간: `---`ms")
        ms = (message.created_at - ctx.message.created_at).total_seconds() * 1000
        await message.edit(content=f'걸린 시간: `{round(ms)}`**ms**')


async def setup(bot: Kkutbot):
    await bot.add_cog(BotInfo(bot))
