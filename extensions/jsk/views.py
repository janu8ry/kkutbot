import discord

from config import config

__all__ = ["AdminTools"]


class AdminTools(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(discord.ui.Button(label="Sentry", style=discord.ButtonStyle.grey, url=config.sentry.url))
        self.add_item(discord.ui.Button(label="Portainer", style=discord.ButtonStyle.grey, url=config.links.portainer))
        self.add_item(discord.ui.Button(label="DB", style=discord.ButtonStyle.grey, url=config.links.dbgate))
        self.add_item(discord.ui.Button(label="Logs", style=discord.ButtonStyle.grey, url=config.links.logs))
