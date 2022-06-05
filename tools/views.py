from datetime import datetime

import discord

from tools.db import db

from .config import config  # noqa


class ConfirmSend(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='전송하기', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.send_message("공지 전송 완료!")
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.send_message("공지 전송이 취소되었습니다.")
        self.stop()


class AnnouncementInput(discord.ui.Modal, title='공지 작성하기'):
    a_title = discord.ui.TextInput(label='공지 제목', required=True)
    description = discord.ui.TextInput(label='공지 본문', style=discord.TextStyle.long, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"**{interaction.user.name}** 님의 메일함",
            description="> 1주일간 읽지 않은 메일 `1` 개",
            color=config('colors.help')
        )
        embed.add_field(name=f"{self.a_title.value} - `1초 전`", value=self.description.value)
        view = ConfirmSend()
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


class SendAnnouncement(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label='내용 작성하기', style=discord.ButtonStyle.blurple)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnnouncementInput(timeout=120))
        self.value = True
        self.stop()
