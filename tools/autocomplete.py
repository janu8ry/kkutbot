import discord
from discord import app_commands

__all__ = ["member_autocomplete"]


async def member_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    choices = []
    if interaction.guild:
        for member in interaction.guild.members:
            if current.lower() in member.name.lower():
                choices.append(app_commands.Choice(name=member.name, value=str(member.id)))
            elif current.lower() in member.display_name.lower():
                choices.append(app_commands.Choice(name=member.display_name, value=str(member.id)))
    return choices[:25]