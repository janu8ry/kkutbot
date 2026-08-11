from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from tools import fmt
from views import BaseView

if TYPE_CHECKING:
    from .models import MultiGame


__all__ = ["HostGuildGame", "PlayAgain", "MultiGameResult"]


class MultiGameResult(BaseView):
    def __init__(self, ctx: commands.Context, game: MultiGame):
        super().__init__(ctx=ctx)
        self.game = game
        self.timeout = 15

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.game.host:
            await interaction.response.send_message(fmt("{denied} 호스트만 사용할 수 있습니다."), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="한 판 더", style=discord.ButtonStyle.green, emoji="▶️")
    async def play_again(self: MultiGameResult, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        self.game.next_action = "again"
        await self.disable_buttons(interaction)
        self.stop()

    @discord.ui.button(label="로비로 돌아가기", style=discord.ButtonStyle.blurple, emoji="🔙")
    async def back_to_lobby(self: MultiGameResult, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        self.game.next_action = "lobby"
        await self.disable_buttons(interaction)
        self.stop()


class PlayAgain(BaseView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.timeout = 10

    @discord.ui.button(label="한 판 더", style=discord.ButtonStyle.green, emoji="▶️")
    async def play_again(self: PlayAgain, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        await self.disable_buttons(interaction)
        self.stop()
        await self.ctx.bot.invoke(self.ctx)


class HostGuildGame(BaseView):
    def __init__(self, ctx: commands.Context, game: MultiGame):
        super().__init__(ctx=ctx, author_only=False)
        self.ctx = ctx
        self.game = game
        self.timeout = game.hosting_timeout
        self.value: str | None = None
        self.refresh_join_button()

    def refresh_join_button(self) -> None:
        self.join_game.disabled = len(self.game.players) >= self.game.max_players

    @discord.ui.button(label="참가하기", style=discord.ButtonStyle.blurple, emoji=fmt("{join}"))
    async def join_game(self: HostGuildGame, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        if interaction.user in self.game.players:
            await interaction.response.send_message(fmt("{denied} 이미 게임에 참가했습니다."), ephemeral=True)
            return
        if interaction.user.id in self.ctx.bot.playing_games:
            await interaction.response.send_message(fmt("{denied} 이미 진행 중인 끝말잇기 게임이 있습니다."), ephemeral=True)
            return
        if (await self.ctx.bot.db.get_user(interaction.user)).points < self.game.ENTRY_FEE:
            await interaction.response.send_message(
                fmt(f"{{denied}} 참가비 `{self.game.ENTRY_FEE}`{{points}}가 부족하여 참가할 수 없습니다."), ephemeral=True
            )
            return
        self.game.players.append(interaction.user)
        self.ctx.bot.playing_games.add(interaction.user.id)
        await self.ctx.channel.send(fmt(f"{{plus}} **{interaction.user.display_name}** 님이 참가했습니다."))
        if len(self.game.players) >= self.game.max_players:
            await self.ctx.channel.send(f"✅ 최대 인원에 도달하여 **{self.game.host.display_name}** 님의 게임을 시작합니다.")
            self.value = "start"
            await self.disable_buttons(interaction)
            self.stop()
            return
        await interaction.response.defer()
        self.message = await self.game.update_embed(await self.game.hosting_embed(), view=self)

    @discord.ui.button(label="나가기", style=discord.ButtonStyle.red, emoji=fmt("{leave}"))
    async def leave_game(self: HostGuildGame, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.is_finished():
            return
        if interaction.user not in self.game.players:
            await interaction.response.send_message(fmt("{denied} 게임에 참가하지 않았습니다."), ephemeral=True)
            return
        self.game.players.remove(interaction.user)
        self.ctx.bot.playing_games.discard(interaction.user.id)
        self.game.last_host = self.game.host
        self.refresh_join_button()
        await self.ctx.channel.send(fmt(f"{{minus}} **{interaction.user.display_name}**님이 나갔습니다."))
        if len(self.game.players) == 0:
            await self.ctx.channel.send(f"❌ 플레이어 수가 부족하여 **{self.game.host.display_name}** 님의 게임을 종료합니다.")
            self.value = "stop"
            await self.disable_buttons(interaction)
            self.stop()
            return
        await interaction.response.defer()
        self.message = await self.game.update_embed(await self.game.hosting_embed(), view=self)

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
        await self.ctx.channel.send(f"✅ **{self.game.host.display_name}**님의 게임을 시작합니다.")
        self.value = "start"
        await self.disable_buttons(interaction)
        self.stop()
        return
