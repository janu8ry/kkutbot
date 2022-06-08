from datetime import datetime

import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorCollection  # noqa

from tools.db import db
from tools.utils import disable_buttons

from .config import config  # noqa


class CustomView(discord.ui.View):
    def __init__(self, ctx, author_only=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.author_only = author_only

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_only:
            if interaction.user != self.ctx.author:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="이 명령어를 실행한 사람만 사용할 수 있어요.\n직접 명령어를 입력하여 사용해주세요.",
                        color=config("colors.error")
                    ),
                    ephemeral=True
                )
                return False
        return True


class ConfirmSendAnnouncement(CustomView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label='전송하기', style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = True
        await interaction.channel.send("공지 전송 완료!")
        await disable_buttons(interaction, view=self)
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = False
        await interaction.channel.send("공지 전송이 취소되었습니다.")
        await disable_buttons(interaction, view=self)
        self.stop()


class AnnouncementInput(discord.ui.Modal, title='공지 작성하기'):
    a_title = discord.ui.TextInput(label='공지 제목', required=True)
    description = discord.ui.TextInput(label='공지 본문', style=discord.TextStyle.long, required=True)

    def __init__(self, timeout: float, ctx: commands.Context):
        super().__init__(timeout=timeout)
        self.value = None
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"**{interaction.user.name}** 님의 메일함",
            description="> 1주일간 읽지 않은 메일 `1` 개",
            color=config('colors.help')
        )
        embed.add_field(name=f"{self.a_title.value} - `1초 전`", value=self.description.value)
        view = ConfirmSendAnnouncement(ctx=self.ctx)
        await interaction.response.send_message("**<공지 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await db.user.update_many(
                {},
                {
                    '$push': {'mails': {'title': self.a_title.value, 'value': self.description.value, 'time': datetime.now()}},
                    '$set': {'alerts.mails': False}
                }
            )


class SendAnnouncement(CustomView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.ctx = ctx

    @discord.ui.button(label='내용 작성하기', style=discord.ButtonStyle.blurple)
    async def msg_input(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(AnnouncementInput(ctx=self.ctx, timeout=120))
        self.value = True
        self.stop()


class ConfirmSendNotice(CustomView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label='전송하기', style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = True
        await interaction.channel.send("알림 전송 완료!")
        await disable_buttons(interaction, view=self)
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = False
        await interaction.channel.send("알림 전송이 취소되었습니다.")
        await disable_buttons(interaction, view=self)
        self.stop()


class NoticeInput(discord.ui.Modal, title='알림 보내기'):
    msg = discord.ui.TextInput(label='알림 내용', style=discord.TextStyle.long, required=True)

    def __init__(self, timeout: float, ctx: commands.Context, target: int):
        super().__init__(timeout=timeout)
        self.value = None
        self.target = target
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"**{interaction.user.name}** 님의 메일함",
            description="> 1주일간 읽지 않은 메일 `1` 개",
            color=config('colors.help')
        )
        embed.add_field(name=f"관리자로부터의 알림 - `1초 전`", value=self.msg.value)
        view = ConfirmSendNotice(ctx=self.ctx)
        await interaction.response.send_message("**<알림 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await db.user.update_one(
                {'_id': self.target},
                {
                    '$push': {'mail': {'title': "관리자로부터의 알림", 'value': self.msg.value, 'time': datetime.now()}},
                    '$set': {'alert.mail': False}
                }
            )


class SendNotice(CustomView):
    def __init__(self, ctx: commands.Context, target: int):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.target = target
        self.ctx = ctx

    @discord.ui.button(label='내용 작성하기', style=discord.ButtonStyle.blurple)
    async def msg_input(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(NoticeInput(timeout=120, ctx=self.ctx, target=self.target))
        self.value = True
        self.stop()


class ServerInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="서포트 서버 참가하기", style=discord.ButtonStyle.grey, url=config("links.invite.server")
            )
        )


class BotInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config("links.invite.bot")
            )
        )


class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="서포트 서버 참가하기", style=discord.ButtonStyle.grey, url=config("links.invite.server")
            )
        )
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config("links.invite.bot")
            )
        )
        self.add_item(
            discord.ui.Button(
                label="하트 누르기", style=discord.ButtonStyle.red, url=f"{config('links.koreanbots')}/vote"
            )
        )


class ConfirmModifyData(CustomView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label='수정하기', style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = True
        await interaction.channel.send("데이터 수정 완료!")
        await disable_buttons(interaction, view=self)
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = False
        await interaction.channel.send("데이터 수정이 취소되었습니다.")
        await disable_buttons(interaction, view=self)
        self.stop()


class DataInput(discord.ui.Modal, title="데이터 수정하기"):
    data_target = discord.ui.TextInput(label='타깃 아이디', required=True)
    data_path = discord.ui.TextInput(label='수정할 데이터 경로', required=True)
    data_value = discord.ui.TextInput(label='수정할 값', style=discord.TextStyle.long, required=True)

    def __init__(self, timeout: float, ctx: commands.Context, collection: AsyncIOMotorCollection):
        super().__init__(timeout=timeout)
        self.value = None
        self.colection = collection
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="데이터 수정 확인",
            description=f"수정 대상: {self.colection.name} - {self.data_target.value}",
            color=config('colors.help')
        )
        embed.add_field(name=f"수정할 데이터: {self.data_path.value}", value=self.data_value.value)
        view = ConfirmModifyData(ctx=self.ctx)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        if view.value:
            final_data = self.data_value.value.strip()
            if final_data == "True":
                final_data = True
            elif final_data == "False":
                final_data = False
            elif final_data.isdecimal():
                final_data = int(self.data_value.value)
            await self.colection.update_one(
                {'_id': int(self.data_target.value)},
                {
                    '$set': {self.data_path.value: final_data}
                }
            )


class ModifyData(CustomView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.ctx = ctx

    @discord.ui.button(label='유저', style=discord.ButtonStyle.green)
    async def modify_user(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(DataInput(timeout=120, ctx=self.ctx, collection=db.user))
        self.value = True
        self.stop()

    @discord.ui.button(label='서버', style=discord.ButtonStyle.red)
    async def modify_guild(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(DataInput(timeout=120, ctx=self.ctx, collection=db.guild))
        self.value = True
        self.stop()

    @discord.ui.button(label='일반', style=discord.ButtonStyle.blurple)
    async def modify_general(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(DataInput(timeout=120, ctx=self.ctx, collection=db.general))
        self.value = True
        self.stop()
