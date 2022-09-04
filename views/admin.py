import time
import ast
import re
from typing import Optional, Union

import discord
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa

from config import config
from core import KkutbotContext
from tools.db import db
from .general import BaseModal, BaseView

__all__ = ["ModifyData", "SendNotice", "SendAnnouncement"]


class ConfirmSendAnnouncement(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label="전송하기", style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = True
        await interaction.channel.send("공지 전송 완료!")
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(label="취소하기", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = False
        await interaction.channel.send("공지 전송이 취소되었습니다.")
        await self.disable_buttons(interaction)
        self.stop()


class AnnouncementInput(BaseModal, title="공지 작성하기"):
    a_title = discord.ui.TextInput(label="공지 제목", required=True, max_length=256)
    description = discord.ui.TextInput(label="공지 본문", style=discord.TextStyle.long, required=True, max_length=1024)

    def __init__(self, ctx: KkutbotContext):
        super().__init__()
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{{email}} **{interaction.user.name}** 님의 메일함",
            color=config("colors.help")
        )
        embed.add_field(name=f"🔹 {self.a_title.value} - `1초 전`", value=self.description.value)
        view = ConfirmSendAnnouncement(ctx=self.ctx)
        await interaction.response.send_message("**<공지 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await db.general.update_one(
                {"_id": "general"},
                {
                    "$push": {"announcements": {"title": self.a_title.value, "value": self.description.value, "time": round(time.time())}}
                }
            )
            await db.user.update_many(
                {},
                {
                    "$set": {"alerts.announcements": False}
                }
            )


class SendAnnouncement(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.ctx = ctx

    @discord.ui.button(label="내용 작성하기", style=discord.ButtonStyle.blurple)
    async def msg_input(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnnouncementInput(ctx=self.ctx))
        button.disabled = True
        await self.message.edit(view=self)
        self.value = True
        self.stop()


class ConfirmSendNotice(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label="전송하기", style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = True
        await interaction.channel.send("알림 전송 완료!")
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(label="취소하기", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = False
        await interaction.channel.send("알림 전송이 취소되었습니다.")
        await self.disable_buttons(interaction)
        self.stop()


class NoticeInput(BaseModal, title="알림 보내기"):
    msg = discord.ui.TextInput(label="알림 내용", style=discord.TextStyle.long, required=True, max_length=1024)

    def __init__(self, ctx: KkutbotContext, target: int):
        super().__init__()
        self.target = target
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{{email}} **{interaction.user.name}** 님의 메일함",
            color=config("colors.help")
        )
        embed.add_field(name="🔹 관리자로부터의 알림 - `1초 전`", value=self.msg.value)
        view = ConfirmSendNotice(ctx=self.ctx)
        await interaction.response.send_message("**<알림 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await db.user.update_one(
                {"_id": self.target},
                {
                    "$push": {"mails": {"title": "관리자로부터의 알림", "value": self.msg.value, "time": round(time.time())}},
                    "$set": {"alerts.mails": False}
                }
            )


class SendNotice(BaseView):
    def __init__(self, ctx: KkutbotContext, target: int):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.target = target
        self.ctx = ctx
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="내용 작성하기", style=discord.ButtonStyle.blurple)
    async def msg_input(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NoticeInput(ctx=self.ctx, target=self.target))
        button.disabled = True
        await self.message.edit(view=self)
        self.value = True
        self.stop()


class ConfirmModifyData(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label="수정하기", style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = True
        await interaction.channel.send("데이터 수정 완료!")
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(label="취소하기", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = False
        await interaction.channel.send("데이터 수정이 취소되었습니다.")
        await self.disable_buttons(interaction)
        self.stop()


class DataInput(BaseModal, title="데이터 수정하기"):
    data_path = discord.ui.TextInput(label="수정할 데이터 경로", required=True)
    data_value = discord.ui.TextInput(label="수정할 값", style=discord.TextStyle.long, required=True)

    def __init__(self, ctx: KkutbotContext, target: Union[int, str], collection: AsyncIOMotorCollection):
        super().__init__()
        self.colection = collection
        self.ctx = ctx
        self.target = target

    async def on_submit(self, interaction: discord.Interaction):
        final_data = self.data_value.value.strip()
        if final_data == "True":
            final_data = True
        elif final_data == "False":
            final_data = False
        elif final_data.isdecimal():
            final_data = int(self.data_value.value)
        else:
            try:
                final_data = ast.literal_eval(self.data_value.value)
            except SyntaxError:
                await interaction.response.send_message("올바른 값이 아닙니다.")
                return self.stop()
        embed = discord.Embed(
            title="데이터 수정 확인",
            description=f"수정 대상: {self.colection.name} - {self.target}",
            color=config("colors.help")
        )
        embed.add_field(name=f"수정할 데이터: {self.data_path.value}", value=self.data_value.value, escape_emoji_formatting=True)  # noqa
        view = ConfirmModifyData(ctx=self.ctx)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        if view.value:
            await self.colection.update_one(
                {"_id": self.target},
                {
                    "$set": {self.data_path.value: final_data}
                }
            )
        self.stop()


class ModifyData(BaseView):
    def __init__(self, ctx: KkutbotContext, target: Union[int, str]):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.target = target
        self.ctx = ctx

    @discord.ui.button(label="수정하기", style=discord.ButtonStyle.blurple)
    async def modify_user(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if isinstance(self.target, str) and re.match(r"<@!?(\d+)>$", self.target):  # if argument is mention
            self.target = re.findall(r'\d+', self.target)[0]
        if isinstance(self.target, str) and self.target.isdecimal():
            self.target = int(self.target)
        if self.target in [g.id for g in self.ctx.bot.guilds]:
            collection = db.guild
        elif await db.user.find_one({"_id": self.target}):
            collection = db.user
        elif self.target == "general":
            collection = db.general
        else:
            await interaction.response.send_message("올바른 타깃이 아닙니다.")
            return self.stop()
        await interaction.response.send_modal(DataInput(ctx=self.ctx, target=self.target, collection=collection))
        self.value = True
        self.stop()
