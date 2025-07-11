from typing import Any

import discord

from config import config
from core import KkutbotContext

__all__ = ["BaseView", "BaseModal", "ServerInvite", "Paginator"]


class BaseView(discord.ui.View):
    def __init__(self, ctx: KkutbotContext, *args: Any, author_only: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.author_only = author_only
        self.timeout = 120
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_only and (interaction.user != self.ctx.author):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="이 명령어를 실행한 사람만 사용할 수 있어요.\n직접 명령어를 입력하여 사용해주세요.", color=config.colors.error
                ),
                ephemeral=True,
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
        self.add_item(discord.ui.Button(label=text, style=discord.ButtonStyle.grey, url=config.links.invite.server))


class PageInput(BaseModal, title="페이지 이동하기"):
    target_page = discord.ui.TextInput(label="페이지 번호", placeholder="이동할 페이지의 번호를 입력해 주세요.", required=True)

    def __init__(self, ctx: KkutbotContext, view: "Paginator") -> None:
        super().__init__()
        self.ctx = ctx
        self.target = None
        self.view = view
        self.target_page.label = f"페이지 번호 (1~{view.page_count})"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.target_page.value.isdecimal() and (1 <= int(self.target_page.value) <= self.view.page_count):
            self.view.index = int(self.target_page.value) - 1
            await self.view.children[2].update_buttons(interaction)
        else:
            await interaction.response.send_message(f"올바른 값이 아닙니다.\n가능한 값: (1~{self.view.page_count})", ephemeral=True)
            self.stop()
            return


class PaginatorButton(discord.ui.Button):
    async def update_buttons(self, interaction: discord.Interaction) -> None:
        self.view.children[0].disabled = bool(self.view.index == 0)
        self.view.children[1].disabled = bool(self.view.index == 0)
        self.view.children[2].label = f"{self.view.index + 1}/{self.view.page_count}"
        self.view.children[3].disabled = bool(self.view.index == self.view.page_count - 1)
        self.view.children[4].disabled = bool(self.view.index == self.view.page_count - 1)
        await interaction.response.edit_message(embed=self.view.pages[self.view.index], view=self.view)


class ToFirst(PaginatorButton):
    def __init__(self) -> None:
        super().__init__(label="<<", style=discord.ButtonStyle.red, disabled=True)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.index = 0
        await self.update_buttons(interaction)


class ToBack(PaginatorButton):
    def __init__(self) -> None:
        super().__init__(label="<", style=discord.ButtonStyle.red, disabled=True)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.index -= 1
        await self.update_buttons(interaction)


class PageInfo(PaginatorButton):
    def __init__(self, pagecount: int) -> None:
        super().__init__(label=f"1/{pagecount}", style=discord.ButtonStyle.gray, disabled=False)

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = PageInput(self.view.ctx, self.view)
        await interaction.response.send_modal(modal)


class ToNext(PaginatorButton):
    def __init__(self) -> None:
        super().__init__(label=">", style=discord.ButtonStyle.blurple, disabled=False)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.index += 1
        await self.update_buttons(interaction)


class ToLast(PaginatorButton):
    def __init__(self) -> None:
        super().__init__(label=">>", style=discord.ButtonStyle.blurple, disabled=False)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.index = self.view.page_count - 1
        await self.update_buttons(interaction)


class Paginator(BaseView):
    def __init__(self, ctx: KkutbotContext, pages: list[discord.Embed]):
        super().__init__(ctx=ctx, author_only=True)
        self.pages = pages
        self.ctx = ctx
        self.index = 0
        self.page_count = len(self.pages)
        self.add_item(ToFirst())
        self.add_item(ToBack())
        self.add_item(PageInfo(pagecount=len(pages)))
        self.add_item(ToNext())
        self.add_item(ToLast())
        if self.page_count == 1:
            self.children[3].disabled = True
            self.children[4].disabled = True

    async def run(self) -> None:
        await self.ctx.reply(embed=self.pages[0], view=self)
