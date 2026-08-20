import time

import discord
from beanie.operators import Set
from discord.ext import commands

from config import config
from database.models import Announcement, User
from tools import fmt
from views import BaseModal, BaseView

__all__ = ["SendAnnouncement"]


class Confirm(BaseView):
    def __init__(self, ctx: commands.Context, action: str, confirm_label: str):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.action = action
        self.confirm.label = confirm_label

    @discord.ui.button(style=discord.ButtonStyle.green)
    async def confirm(self: Confirm, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = True
        await interaction.channel.send(f"{self.action} 완료!")  # type: ignore
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(label="취소하기", style=discord.ButtonStyle.red)
    async def cancel(self: Confirm, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = False
        await interaction.channel.send(f"{self.action}이 취소되었습니다.")  # type: ignore
        await self.disable_buttons(interaction)
        self.stop()


class AnnouncementInput(BaseModal, title="공지 작성하기"):
    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx
        self.a_title = discord.ui.TextInput(required=True, max_length=256)
        self.description = discord.ui.TextInput(style=discord.TextStyle.long, required=True, max_length=1024)
        self.add_item(discord.ui.Label(text="공지 제목", component=self.a_title))
        self.add_item(discord.ui.Label(text="공지 본문", component=self.description))

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=fmt("{email} 끝봇 공지사항"), color=config.colors.green)
        embed.add_field(name=f"🔹 {self.a_title.value} - <t:{int(time.time()) - 1}:R>", value=self.description.value)
        view = Confirm(ctx=self.ctx, action="공지 전송", confirm_label="전송하기")
        await interaction.response.send_message("**<공지 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await Announcement(id=round(time.time()), title=self.a_title.value, value=self.description.value).insert()
            await User.find().update(Set({User.alerts.announcements: False}))  # noqa


class SendAnnouncement(BaseView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label="내용 작성하기", style=discord.ButtonStyle.blurple)
    async def msg_input(self: SendAnnouncement, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnnouncementInput(ctx=self.ctx))
        button.disabled = True
        await self.message.edit(view=self)  # type: ignore
        self.value = True
        self.stop()
