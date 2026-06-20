import discord

from config import config
from core import KkutbotContext
from views import BaseView

__all__ = ["HelpMenu", "InviteMenu"]


class HelpDropdown(discord.ui.Select):
    def __init__(self, ctx: KkutbotContext):
        self.ctx = ctx
        options = []
        for cmd in ctx.bot.commands:
            if cmd.cog.qualified_name not in ["지샤쿠", "관리자"] and not cmd.hidden:  # noqa
                option = discord.SelectOption(label=cmd.name, value=cmd.name, description=cmd.short_doc, emoji=cmd.usage)
                options.append(option)
        super().__init__(placeholder="도움말을 확인할 명령어를 선택해 주세요.", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        cmd = self.ctx.bot.get_command(self.values[0])
        embed = discord.Embed(
            title=f"{{help}} {self.values[0]} 명령어 도움말",
            description=f"🔸 {cmd.help.split('--')[0] or '도움말이 없습니다.'}",
            color=config.colors.help,
        )
        if len(body := cmd.help.split("--")) > 1:
            embed.add_field(name="", value="", inline=False)
            for section in body[1:]:
                embed.add_field(name="🔹 " + section.split("\n")[0], value="\n".join(section.split("\n")[1:]), inline=False)
        embed.set_thumbnail(url=self.ctx.bot.user.display_avatar.url)
        embed.set_footer(text="도움이 필요하다면 서포트 서버에 참가해보세요!")
        self.view.children[0].disabled = False
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpMenu(BaseView):
    def __init__(self, ctx: KkutbotContext, home_embed: discord.Embed):
        super().__init__(ctx=ctx, author_only=True)
        self.home_embed = home_embed
        self.add_item(discord.ui.Button(label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config.links.invite.bot))
        self.add_item(discord.ui.Button(label="커뮤니티 서버 참가하기", style=discord.ButtonStyle.grey, url=config.links.invite.server))
        self.add_item(discord.ui.Button(label="하트 누르기", style=discord.ButtonStyle.red, url=f"{config.links.koreanbots}/vote"))
        self.add_item(HelpDropdown(ctx))

    @discord.ui.button(label="홈", style=discord.ButtonStyle.blurple, emoji="🏠", row=2, disabled=True)
    async def go_home(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(embed=self.home_embed, view=self)


class InviteMenu(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(discord.ui.Button(label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config.links.invite.bot))
        self.add_item(discord.ui.Button(label="커뮤니티 서버 참가하기", style=discord.ButtonStyle.grey, url=config.links.invite.server))
