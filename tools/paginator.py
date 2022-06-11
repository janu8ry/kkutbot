from typing import List

import discord
from discord.ext import commands

from tools.views import DefaultView


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


class PageInfo(discord.ui.Button):
    def __init__(self, pagecount):
        super().__init__(label=f"1/{pagecount}", style=discord.ButtonStyle.gray, disabled=True)


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

    async def run(self):
        await self.ctx.reply(embed=self.pages[0], view=self)
