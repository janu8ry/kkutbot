import discord

from core import KkutbotContext
from views import BaseView


__all__ = ["SelectMode"]


class SelectMode(BaseView):
    def __init__(self, ctx: KkutbotContext):
        super().__init__(ctx=ctx, author_only=True)
        self.ctx = ctx
        self.timeout = 15
        self.value = None

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="1️⃣")
    async def rank_solo(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 1
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="2️⃣")
    async def guild_multi(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 2
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="3️⃣")
    async def kkd(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 3
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="❌")
    async def quit(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = 0
        await self.disable_buttons(interaction)
        self.stop()

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
        await self.ctx.reply("취소되었습니다.")
