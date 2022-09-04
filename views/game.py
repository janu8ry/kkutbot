from typing import TYPE_CHECKING

import discord

from core import KkutbotContext
from tools.db import read
from views.general import BaseView

if TYPE_CHECKING:
    from cogs.game import MultiGame

__all__ = ["SelectMode", "HostGuildGame"]


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


class HostGuildGame(BaseView):
    def __init__(self, ctx: KkutbotContext, game: "MultiGame"):
        super().__init__(ctx=ctx, author_only=False)
        self.ctx = ctx
        self.timeout = 120
        self.game = game
        self.value = None

    @discord.ui.button(label="참가하기", style=discord.ButtonStyle.blurple, emoji="<:join:988350647093063681>")
    async def join_game(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if interaction.user in self.game.players:
            return await interaction.response.send_message("<:denyed:730319627623596032> 이미 게임에 참가했습니다.", ephemeral=True)
        if await read(interaction.user, "banned.isbanned"):
            return await interaction.response.send_message("<:denyed:730319627623596032> 차단된 유저는 게임에 참가할 수 없습니다.", ephemeral=True)
        self.game.players.append(interaction.user)
        await self.ctx.send(f"<:plus:988352187522506782> **{interaction.user}** 님이 참가했습니다.")
        if len(self.game.players) == 5:
            await self.ctx.send(f"✅ 최대 인원에 도달하여 **{self.game.host}** 님의 게임을 시작합니다.")
            self.value = "start"
            await self.disable_buttons(interaction)
            return self.stop()
        await interaction.response.defer()
        self.message = await self.game.update_embed(self.game.hosting_embed(), view=self)

    @discord.ui.button(label="나가기", style=discord.ButtonStyle.red, emoji="<:leave:988350673223548949>")
    async def leave_game(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if interaction.user not in self.game.players:
            return await interaction.response.send_message("<:denyed:730319627623596032> 게임에 참가하지 않았습니다.", ephemeral=True)
        self.game.players.remove(interaction.user)
        self.game.last_host = self.game.host
        await self.ctx.send(f"<:minus:988352203200794634> **{interaction.user}**님이 나갔습니다.")
        if len(self.game.players) == 0:
            await self.ctx.send(f"❌ 플레이어 수가 부족하여 **{self.game.host}** 님의 게임을 종료합니다.")
            self.ctx.bot.guild_multi_games.remove(self.ctx.channel.id)
            self.value = "stop"
            await self.disable_buttons(interaction)
            return self.stop()
        await interaction.response.defer()
        self.message = await self.game.update_embed(self.game.hosting_embed(), view=self)

    @discord.ui.button(label="게임 시작", style=discord.ButtonStyle.green, emoji="<:start:988350697873477683>")
    async def start_game(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if interaction.user != self.game.host:
            return await interaction.response.send_message("<:denyed:730319627623596032> 호스트만 게임을 시작할 수 있습니다.", ephemeral=True)
        if len(self.game.players) < 2:
            return await interaction.response.send_message("<:denyed:730319627623596032> 플레이어 수가 부족하여 게임을 시작할 수 없습니다.", ephemeral=True)
        await self.ctx.send(f"✅ **{self.game.host}**님의 게임을 시작합니다.")
        self.value = "start"
        await self.disable_buttons(interaction)
        return self.stop()

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
        if len(self.game.players) < 2:
            await self.ctx.send(f"❌ 플레이어 수가 부족하여 **{self.game.host}**님의 게임을 종료합니다.")
            self.ctx.bot.guild_multi_games.remove(self.ctx.channel.id)
            self.value = "stop"
            return self.stop()
        else:
            await self.ctx.send(f"✅ 대기 시간이 초과되어 **{self.game.host}**님의 게임을 시작합니다.")
            self.value = "start"
            return self.stop()
