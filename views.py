from typing import Any, Optional

import discord

from config import config
from core import KkutbotContext

__all__ = ["BaseView", "BaseModal", "ServerInvite", "BotInvite", "KoreanBotsVote"]


class BaseView(discord.ui.View):
    def __init__(self, ctx: KkutbotContext, *args: Any, author_only: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.author_only = author_only
        self.timeout = 120
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_only and (interaction.user != self.ctx.author):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="이 명령어를 실행한 사람만 사용할 수 있어요.\n직접 명령어를 입력하여 사용해주세요.",
                    color=config.colors.error
                ),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def disable_buttons(self, interaction: discord.Interaction, use_msg: bool = False) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if use_msg:
            await self.message.edit(view=self)
        else:
            await interaction.response.edit_message(view=self)


class BaseModal(discord.ui.Modal):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.timeout = 120


class ServerInvite(discord.ui.View):
    def __init__(self, text: str = "커뮤니티 서버 참가하기") -> None:
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label=text, style=discord.ButtonStyle.grey, url=config.links.invite.server
            )
        )


class BotInvite(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config.links.invite.bot
            )
        )


class KoreanBotsVote(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="끝봇에게 하트추가", style=discord.ButtonStyle.grey, url=config.links.koreanbots
            )
        )
