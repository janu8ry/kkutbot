import discord
from discord.ext import commands

from config import config
from core import KkutbotContext
from tools.utils import is_admin
from views.general import BaseView

__all__ = ["HelpMenu"]


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
                emoji="<:help:715549237022163005>",
            )
            options.append(option)
        super().__init__(placeholder="카테고리를 선택해 주세요.", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        cog_data = self.ctx.bot.get_cog(self.values[0])
        embed = discord.Embed(
            title=f"{{help}} {self.values[0]} 명령어 도움말",
            description=cog_data.description,
            color=config("colors.help"),
        )
        for cmd in cog_data.get_commands():
            if not cmd.hidden:
                embed.add_field(
                    name=f"🔹 {cmd.name}",
                    value=f"{cmd.help}\n\n사용 방법: `{cmd.usage}`",
                    inline=False,
                )
        embed.set_footer(text="도움이 필요하다면 서포트 서버에 참가해보세요!")
        self.view.children[0].disabled = False
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpMenu(BaseView):
    def __init__(self, ctx: KkutbotContext, home_embed: discord.Embed):
        super().__init__(ctx=ctx, author_only=True)
        self.home_embed = home_embed
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기",
                style=discord.ButtonStyle.grey,
                url=config("links.invite.bot"),
            )
        )
        self.add_item(
            discord.ui.Button(
                label="서포트 서버 참가하기",
                style=discord.ButtonStyle.grey,
                url=config("links.invite.server"),
            )
        )
        self.add_item(
            discord.ui.Button(
                label="하트 누르기",
                style=discord.ButtonStyle.red,
                url=f"{config('links.koreanbots')}/vote",
            )
        )
        self.add_item(HelpDropdown(ctx))

    @discord.ui.button(label="홈", style=discord.ButtonStyle.blurple, emoji="🏠", row=2, disabled=True)
    async def go_home(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(embed=self.home_embed, view=self)
