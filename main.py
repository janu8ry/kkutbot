import logging
import random
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Type, Union

import discord
from discord.ext import commands
from rich.traceback import install as rich_install
from beanie.operators import Push

import core
from config import config, get_nested_dict
from tools.logger import setup_logger
from tools.utils import is_admin
from views.general import ServerInvite
from database.models import User

logger = logging.getLogger("kkutbot")

bot = core.Kkutbot()


@bot.event
async def on_ready() -> None:
    await bot.reload_all()

    to_replace = {
        "jishaku sh": ["쉘", "ㅅ", "실행"],
        "jishaku cat": ["캣", "ㅋ", "파일", "ㅍㅇ"],
        "jishaku sync": ["ㅅㅋ", "동기화", "ㄷ"]
    }
    for name, aliases in to_replace.items():
        bot.add_aliases(name, aliases)

    guilds = len(bot.guilds)
    users = await bot.db.client.user.count_documents({})

    logger.info(f"'{bot.user.name}'으로 로그인됨\n"
                f"서버수: {guilds}, 유저수: {users}")

    await bot.update_presence()


@bot.event
async def on_shard_ready(shard_id: int) -> None:
    logger.info(f"{shard_id}번 샤드 준비 완료!")


@bot.before_invoke
async def before_command(ctx: core.KkutbotContext) -> None:
    user = await bot.db.get_user(ctx.author)
    user.command_used += 1
    user.latest_usage = round(time.time())

    if ctx.guild:
        guild = await bot.db.get_guild(ctx.guild)
        guild.latest_usage = round(time.time())
        guild.command_used += 1
        await bot.db.save(guild)

    public = await bot.db.get_public()
    public.command_used += 1
    public.latest_usage = round(time.time())
    cmd_name = ctx.command.qualified_name.replace('$', '_')  # TODO: 뭔지모를 버그 해결
    if cmd_name in public.commands:
        public.commands[cmd_name] += 1
    else:
        public.commands[cmd_name] = 1

    if user.quest.status.date != (today := datetime.today().toordinal()):
        user.quest.status.date = today
        user.quest.status.completed = []
        cache = {}
        for data in public.quests.keys():
            cache[data] = get_nested_dict(user.dict(), data.split("/"))
        user.quest.cache = cache

    await bot.db.save(user)
    await bot.db.save(public)

    if ctx.message.content:
        msg = ctx.message.content
    else:
        msg = f"/{ctx.command}"
    if isinstance(ctx.channel, discord.DMChannel):
        logger.command(f"{ctx.author} [{ctx.author.id}]  |  DM [{ctx.channel.id}]  |  {msg}")
    else:
        logger.command(f"{ctx.author} [{ctx.author.id}]  |  {ctx.guild} [{ctx.guild.id}]  |  {ctx.channel} [{ctx.channel.id}]  |  {msg}")


@bot.check
async def check(ctx: core.KkutbotContext) -> bool:
    if ctx.guild and not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        try:
            embed = discord.Embed(
                title="오류",
                description=f"{ctx.channel.mention}에서 끝봇에게 메시지 보내기 권한이 없어서 명령어를 사용할 수 없습니다.\n"
                            f"끝봇에게 해당 권한을 지급한 후 다시 시도해주세요.",
                color=config.colors.error
            )
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass
        return False

    return True


@bot.event
async def on_interaction(interaction: discord.Interaction) -> None:
    if interaction.type == discord.InteractionType.component:
        kst = timezone(timedelta(hours=9))
        interaction_created = round(time.mktime(interaction.message.created_at.astimezone(kst).timetuple()))
        if interaction_created < bot.started_at:
            types = ["그룹은", "버튼은", "리스트는", "텍스트박스는"]
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{{denyed}} 이 {types[interaction.data['component_type'] - 1]} 너무 오래되어 사용할 수 없어요.\n"
                                f"명령어를 새로 입력해주세요.",
                    color=config.colors.error
                ),
                ephemeral=True
            )


if __name__ == "__main__":
    rich_install()
    setup_logger()
    bot.run_bot()
