import logging
from collections.abc import Callable

import discord
from discord.ext import commands
from sentry_sdk import capture_exception

from config import config

__all__ = ["BaseView", "BaseModal", "ServerInvite", "Paginator"]

logger = logging.getLogger("kkutbot")


class BaseView(discord.ui.View):
    def __init__(self, ctx: commands.Context, *, author_only: bool = False) -> None:
        super().__init__()
        self.ctx = ctx
        self.author_only = author_only
        self.timeout = 120
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_only and (interaction.user != self.ctx.author):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="이 명령어를 실행한 사람만 사용할 수 있어요.\n직접 명령어를 입력하여 사용해주세요.", color=config.colors.red
                ),
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True  # type: ignore
        try:
            if self.message:
                await self.message.edit(view=self)
        except discord.HTTPException:
            pass

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item, /) -> None:
        logger.error(f"'{type(self).__name__}'의 '{type(item).__name__}' 처리에 실패했습니다.", exc_info=error)
        capture_exception(error)

    async def disable_buttons(self, interaction: discord.Interaction, use_msg: bool = False) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if use_msg and self.message:
            await self.message.edit(view=self)
        else:
            await interaction.response.edit_message(view=self)


class BaseModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__()
        self.timeout = 120

    async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None:
        logger.error(f"'{type(self).__name__}' 모달 처리에 실패했습니다.", exc_info=error)
        capture_exception(error)


class ServerInvite(discord.ui.View):
    def __init__(self, text: str = "커뮤니티 서버 참가하기") -> None:
        super().__init__()
        self.add_item(discord.ui.Button(label=text, style=discord.ButtonStyle.grey, url=config.links.invite.server))


class PageInput(BaseModal, title="페이지 이동하기"):
    def __init__(self, ctx: commands.Context, view: Paginator) -> None:
        super().__init__()
        self.ctx = ctx
        self.view = view
        self.target_page = discord.ui.TextInput(placeholder="이동할 페이지의 번호를 입력해 주세요.", required=True)
        self.add_item(discord.ui.Label(text=f"페이지 번호 (1~{view.page_count})", component=self.target_page))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.target_page.value.isdecimal() and (1 <= int(self.target_page.value) <= self.view.page_count):
            self.view.index = int(self.target_page.value) - 1
            await self.view.update_buttons(interaction)
        else:
            await interaction.response.send_message(f"올바른 값이 아닙니다.\n가능한 값: (1~{self.view.page_count})", ephemeral=True)
            self.stop()
            return


class NavButton(discord.ui.Button["Paginator"]):
    def __init__(self, label: str, style: discord.ButtonStyle, target: Callable[[Paginator], int], disabled: bool = False) -> None:
        super().__init__(label=label, style=style, disabled=disabled)
        self.target = target

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.index = self.target(self.view)  # type: ignore
        await self.view.update_buttons(interaction)  # type: ignore


class PageInfo(discord.ui.Button["Paginator"]):
    def __init__(self, pagecount: int) -> None:
        super().__init__(label=f"1/{pagecount}", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PageInput(self.view.ctx, self.view))  # type: ignore


class Paginator(BaseView):
    def __init__(self, ctx: commands.Context, pages: list[discord.Embed]):
        super().__init__(ctx=ctx, author_only=True)
        self.pages = pages
        self.index = 0
        self.page_count = len(self.pages)
        self.add_item(NavButton("<<", discord.ButtonStyle.red, lambda v: 0, disabled=True))
        self.add_item(NavButton("<", discord.ButtonStyle.red, lambda v: v.index - 1, disabled=True))
        self.add_item(PageInfo(pagecount=self.page_count))
        self.add_item(NavButton(">", discord.ButtonStyle.blurple, lambda v: v.index + 1, disabled=self.page_count == 1))
        self.add_item(NavButton(">>", discord.ButtonStyle.blurple, lambda v: v.page_count - 1, disabled=self.page_count == 1))

    async def update_buttons(self, interaction: discord.Interaction) -> None:
        self.children[0].disabled = self.children[1].disabled = self.index == 0  # type: ignore
        self.children[2].label = f"{self.index + 1}/{self.page_count}"  # type: ignore
        self.children[3].disabled = self.children[4].disabled = self.index == self.page_count - 1  # type: ignore
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    async def run(self) -> None:
        self.message = await self.ctx.reply(embed=self.pages[0], view=self)
