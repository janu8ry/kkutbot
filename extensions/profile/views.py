import discord
from discord.ext import commands
from discord.utils import escape_markdown as e_mk
from discord.utils import escape_mentions as e_mt

from tools import fmt
from views import BaseModal, BaseView

__all__ = ["ProfileMenu", "SelfProfileMenu"]


class InfoInput(BaseModal, title="소개말 수정하기"):
    bio_text = discord.ui.TextInput(
        label="소개말 내용 (최대 50자)", min_length=1, max_length=50, placeholder="소개말을 입력해 주세요.", required=True
    )

    def __init__(self, ctx: commands.Context, view: BaseView):
        super().__init__()
        self.ctx = ctx
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        bio = self.bio_text.value.replace("`", "")
        user = await self.ctx.bot.db.get_user(interaction.user)
        user.bio = bio
        await self.ctx.bot.db.save(user)
        for btn in self.view.children:
            btn.disabled = True  # type: ignore
        if self.view.message:
            await self.view.message.edit(view=self.view)
        await interaction.response.send_message(fmt(f"{{done}} 소개말을 '{e_mk(e_mt(bio))}'(으)로 변경했습니다!"), ephemeral=True)
        self.view.stop()


class ProfileMenu(BaseView):
    def __init__(self, ctx: commands.Context, profile_embed: discord.Embed, stats_embed: discord.Embed):
        super().__init__(ctx=ctx, author_only=True)
        self.profile_embed = profile_embed
        self.stats_embed = stats_embed
        self.ctx = ctx

    @discord.ui.button(label="홈", style=discord.ButtonStyle.blurple, emoji="🏠", row=1, disabled=True)
    async def go_home(self: ProfileMenu, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        self.children[1].disabled = False
        await interaction.response.edit_message(embed=self.profile_embed, view=self)

    @discord.ui.button(label="통계 확인하기", style=discord.ButtonStyle.red, emoji=fmt("{stats}"), row=1, disabled=False)
    async def stats(self: ProfileMenu, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        self.children[0].disabled = False
        await interaction.response.edit_message(embed=self.stats_embed, view=self)


class SelfProfileMenu(ProfileMenu):
    @discord.ui.button(label="소개말 수정하기", style=discord.ButtonStyle.blurple, row=1, emoji=fmt("{edit}"))
    async def edit_info(self: SelfProfileMenu, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(InfoInput(ctx=self.ctx, view=self))
