import discord
from discord.ext import commands
from discord.utils import escape_markdown as e_mk
from discord.utils import escape_mentions as e_mt

from config import config
from core import KkutbotContext
from tools.db import write
from views.general import BaseModal, BaseView

__all__ = ["InfoEdit"]


class InfoInput(BaseModal, title="소개말 수정하기"):
    info_word = discord.ui.TextInput(
        label="소개말 내용 (최대 50자)", min_length=1, max_length=50, placeholder="소개말을 입력해 주세요.", required=True
    )

    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        self.info_word.value.replace("`", "")
        await write(self.ctx.author, "info", self.info_word.value)
        await interaction.response.send_message(
            f"<:done:{config.emojis['done']}> 소개말을 '{e_mk(e_mt(self.info_word.value))}'(으)로 변경했습니다!", ephemeral=True
        )


class InfoEdit(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.ctx = ctx

    @discord.ui.button(label="소개말 수정하기", style=discord.ButtonStyle.blurple, emoji="<:edit:984405210870988870>")
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoInput(ctx=self.ctx))
        button.disabled = True
        await self.message.edit(view=self)
        self.stop()
