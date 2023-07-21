import discord

from config import config

__all__ = ["KoreanBotsVote"]


class KoreanBotsVote(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="끝봇에게 하트추가", style=discord.ButtonStyle.grey, url=config.links.koreanbots
            )
        )
