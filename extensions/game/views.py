from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from tools import fmt
from views import BaseView

from .utils import GameMode

if TYPE_CHECKING:
    from .models import MultiGame


__all__ = ["SelectMode", "HostGuildGame"]


class SelectMode(BaseView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.ctx = ctx
        self.timeout = 15
        self.value: GameMode | None = None

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="1️⃣")
    async def rank_solo(self: SelectMode, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = GameMode.RANK_SOLO
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="2️⃣")
    async def guild_multi(self: SelectMode, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = GameMode.GUILD_MULTI
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="3️⃣")
    async def kkd(self: SelectMode, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = GameMode.KKD
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(style=discord.ButtonStyle.gray, emoji="❌")
    async def quit(self: SelectMode, interaction: discord.Interaction, _button: discord.ui.Button):
        self.value = GameMode.CANCELLED
        await self.disable_buttons(interaction)
        self.stop()

    async def on_timeout(self) -> None:
        await super().on_timeout()
        await self.ctx.reply("취소되었습니다.")


class HostGuildGame(BaseView):
    def __init__(self, ctx: commands.Context, game: "MultiGame"):
        super().__init__(ctx=ctx, author_only=False)
        self.ctx = ctx
        self.game = game
        self.timeout = game.hosting_timeout
        self.value: str | None = None

    @discord.ui.button(label="참가하기", style=discord.ButtonStyle.blurple, emoji=fmt("{join}"))
    async def join_game(self: HostGuildGame, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        if interaction.user in self.game.players:
            await interaction.response.send_message(fmt("{denied} 이미 게임에 참가했습니다."), ephemeral=True)
            return
        self.game.players.append(interaction.user)
        await self.ctx.send(fmt(f"{{plus}} **{interaction.user}** 님이 참가했습니다."))
        if len(self.game.players) >= self.game.max_players:
            await self.ctx.send(f"✅ 최대 인원에 도달하여 **{self.game.host}** 님의 게임을 시작합니다.")
            self.value = "start"
            await self.disable_buttons(interaction)
            self.stop()
            return
        await interaction.response.defer()
        self.message = await self.game.update_embed(self.game.hosting_embed(), view=self)

    @discord.ui.button(label="나가기", style=discord.ButtonStyle.red, emoji=fmt("{leave}"))
    async def leave_game(self: HostGuildGame, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        if interaction.user not in self.game.players:
            await interaction.response.send_message(fmt("{denied} 게임에 참가하지 않았습니다."), ephemeral=True)
            return
        self.game.players.remove(interaction.user)
        self.game.last_host = self.game.host
        await self.ctx.send(fmt(f"{{minus}} **{interaction.user}**님이 나갔습니다."))
        if len(self.game.players) == 0:
            await self.ctx.send(f"❌ 플레이어 수가 부족하여 **{self.game.host}** 님의 게임을 종료합니다.")
            self.value = "stop"
            await self.disable_buttons(interaction)
            self.stop()
            return
        await interaction.response.defer()
        self.message = await self.game.update_embed(self.game.hosting_embed(), view=self)

    @discord.ui.button(label="게임 시작", style=discord.ButtonStyle.green, emoji=fmt("{start}"))
    async def start_game(self: HostGuildGame, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        if interaction.user != self.game.host:
            await interaction.response.send_message(fmt("{denied} 호스트만 게임을 시작할 수 있습니다."), ephemeral=True)
            return
        if len(self.game.players) < 2:
            await interaction.response.send_message(fmt("{denied} 플레이어 수가 부족하여 게임을 시작할 수 없습니다."), ephemeral=True)
            return
        await self.ctx.send(f"✅ **{self.game.host}**님의 게임을 시작합니다.")
        self.value = "start"
        await self.disable_buttons(interaction)
        self.stop()
        return

    async def on_timeout(self) -> None:
        await super().on_timeout()
        if len(self.game.players) < 2:
            await self.ctx.send(f"❌ 플레이어 수가 부족하여 **{self.game.host}**님의 게임을 종료합니다.")
            self.value = "stop"
        else:
            await self.ctx.send(f"✅ 대기 시간이 초과되어 **{self.game.host}**님의 게임을 시작합니다.")
            self.value = "start"
        self.stop()
