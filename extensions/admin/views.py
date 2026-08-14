import ast
import time
from typing import Literal

import discord
from beanie.operators import Set
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorCollection

from config import config
from database.models import Announcement, User
from tools import fmt
from views import BaseModal, BaseView

__all__ = ["ModifyData", "SendAnnouncement"]


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
    a_title = discord.ui.TextInput(label="공지 제목", required=True, max_length=256)
    description = discord.ui.TextInput(label="공지 본문", style=discord.TextStyle.long, required=True, max_length=1024)

    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx

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
        self.ctx = ctx

    @discord.ui.button(label="내용 작성하기", style=discord.ButtonStyle.blurple)
    async def msg_input(self: SendAnnouncement, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnnouncementInput(ctx=self.ctx))
        button.disabled = True
        await self.message.edit(view=self)  # type: ignore
        self.value = True
        self.stop()


class DataInput(BaseModal, title="데이터 수정하기"):
    data_path = discord.ui.TextInput(label="수정할 데이터 경로", required=True)
    data_value = discord.ui.TextInput(label="수정할 값", style=discord.TextStyle.long, required=True)

    def __init__(self, ctx: commands.Context, target: discord.User | discord.Guild | Literal["public"], collection: AsyncIOMotorCollection):
        super().__init__()
        self.ctx = ctx
        self.target = target
        self.collection = collection

    async def on_submit(self, interaction: discord.Interaction):
        try:
            data = self.data_value.value.strip()
            final_data = ast.literal_eval(data)
        except SyntaxError, ValueError:
            try:
                data = '"' + self.data_value.value.strip() + '"'
                final_data = ast.literal_eval(data)
            except SyntaxError, ValueError:
                await interaction.response.send_message("올바른 값이 아닙니다.")
                self.stop()
                return
        embed = discord.Embed(
            title="데이터 수정 확인",
            description=f"수정 대상: {getattr(self.target, 'name', '공용 데이터')} - {getattr(self.target, 'id', 'public')}",
            color=config.colors.green,
        )
        embed.add_field(name=f"수정할 데이터: {self.data_path.value}", value=self.data_value.value)
        view = Confirm(ctx=self.ctx, action="데이터 수정", confirm_label="수정하기")
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        if view.value:
            await self.collection.update_one({"_id": getattr(self.target, "id", "public")}, {"$set": {self.data_path.value: final_data}})
        self.stop()
        return


class ModifyData(BaseView):
    def __init__(self, ctx: commands.Context, target: discord.User | discord.Guild | Literal["public"]):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.target = target
        self.ctx = ctx

    @discord.ui.button(label="수정하기", style=discord.ButtonStyle.blurple)
    async def modify_user(self: ModifyData, interaction: discord.Interaction, _button: discord.ui.Button):
        if isinstance(self.target, discord.User) and (await self.ctx.bot.db.get_user(self.target)).registered:
            collection = self.ctx.bot.db.client.user
        elif isinstance(self.target, discord.Guild) and (await self.ctx.bot.db.get_guild(self.target)).invited:
            collection = self.ctx.bot.db.client.guild
        elif self.target == "public":
            collection = self.ctx.bot.db.client.public
        else:
            await interaction.response.send_message("올바른 타깃이 아닙니다.")
            self.stop()
            return
        await interaction.response.send_modal(DataInput(ctx=self.ctx, target=self.target, collection=collection))
        self.value = True
        self.stop()
        return
