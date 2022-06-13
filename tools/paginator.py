from typing import List

import discord
from discord.ext import commands

from tools.views import DefaultView, DefaultModal


class PageInput(DefaultModal, title="페이지 이동하기"):
    target_page = discord.ui.TextInput(label='페이지 번호', placeholder="이동할 페이지의 번호를 입력해 주세요.", required=True)

    def __init__(self, ctx: commands.Context, view: "Paginator"):
        super().__init__()
        self.ctx = ctx
        self.target = None
        self.view = view
        self.target_page.label = f"페이지 번호 (1~{view.page_count})"

    async def on_submit(self, interaction: discord.Interaction):
        if self.target_page.value.isdecimal() and (1 <= int(self.target_page.value) <= self.view.page_count):
            self.view.index = int(self.target_page.value) - 1
            await self.view.children[2].update_buttons(interaction)
        else:
            await interaction.response.send_message(f"올바른 값이 아닙니다.\n가능한 값: (1~{self.view.page_count})", ephemeral=True)
            return self.stop()


class PaginatorButton(discord.ui.Button):
    async def update_buttons(self, interaction: discord.Interaction):
        self.view.children[0].disabled = bool(self.view.index == 0)
        self.view.children[1].disabled = bool(self.view.index == 0)
        self.view.children[2].label = f"{self.view.index + 1}/{self.view.page_count}"
        self.view.children[3].disabled = bool(self.view.index == self.view.page_count - 1)
        self.view.children[4].disabled = bool(self.view.index == self.view.page_count - 1)
        await interaction.response.edit_message(embed=self.view.pages[self.view.index], view=self.view)


class ToFirst(PaginatorButton):
    def __init__(self):
        super().__init__(label="<<", style=discord.ButtonStyle.red, disabled=True)

    async def callback(self, interaction: discord.Interaction):
        self.view.index = 0
        await self.update_buttons(interaction)


class ToBack(PaginatorButton):
    def __init__(self):
        super().__init__(label="<", style=discord.ButtonStyle.red, disabled=True)

    async def callback(self, interaction: discord.Interaction):
        self.view.index -= 1
        await self.update_buttons(interaction)


class PageInfo(PaginatorButton):
    def __init__(self, pagecount):
        super().__init__(label=f"1/{pagecount}", style=discord.ButtonStyle.gray, disabled=False)

    async def callback(self, interaction: discord.Interaction):
        modal = PageInput(self.view.ctx, self.view)
        await interaction.response.send_modal(modal)


class ToNext(PaginatorButton):
    def __init__(self):
        super().__init__(label=">", style=discord.ButtonStyle.blurple, disabled=False)

    async def callback(self, interaction: discord.Interaction):
        self.view.index += 1
        await self.update_buttons(interaction)


class ToLast(PaginatorButton):
    def __init__(self):
        super().__init__(label=">>", style=discord.ButtonStyle.blurple, disabled=False)

    async def callback(self, interaction: discord.Interaction):
        self.view.index = self.view.page_count - 1
        await self.update_buttons(interaction)


class Paginator(DefaultView):
    def __init__(self, ctx: commands.Context, pages: List[discord.Embed]):
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

    async def run(self):
        await self.ctx.reply(embed=self.pages[0], view=self)
