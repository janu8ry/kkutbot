import asyncio
import linecache
import logging
import os
import random
import time
import traceback
import uuid
from contextlib import suppress
from datetime import datetime

import discord
from discord.ext import commands
from rich.traceback import install as rich_install
from sentry_sdk import capture_exception

import core
from config import config, get_nested_dict
from extensions.economy.point import is_reward_claimable
from tools.logger import KkutbotLogger, setup_logger
from tools.utils import fmt, get_perm_name, is_admin
from views import ServerInvite

logger: KkutbotLogger = logging.getLogger("kkutbot")  # type: ignore

bot = core.Kkutbot()


@bot.event
async def on_ready() -> None:
    await bot.reload_all()

    to_replace = {
        "jishaku sh": ["쉘", "ㅅ", "실행"],
        "jishaku cat": ["캣", "ㅋ", "파일", "ㅍㅇ"],
        "jishaku sync": ["싱크", "ㅅㅋ", "동기화", "ㄷ"],
        "jishaku py": ["파이썬", "ㅍ"],
        "jishaku rtt": ["핑", "ㅍㅍ", "지연"],
        "jishaku exec": ["ㅇ"],
    }
    for name, aliases in to_replace.items():
        bot.add_aliases(name, aliases)

    guilds = len(bot.guilds)
    users = await bot.db.count_users()

    logger.info(f"'{getattr(bot.user, 'name', '_')}'으로 로그인되었습니다! (서버수: {guilds}, 유저수: {users})")

    await bot.update_presence()


@bot.event
async def on_shard_ready(shard_id: int) -> None:
    logger.info(f"{shard_id}번 샤드 준비 완료!")


@bot.before_invoke
async def before_command(ctx: commands.Context) -> None:
    if ctx.author.bot:
        return
    user = await bot.db.get_user(ctx.author)
    user.command_used += 1
    user.latest_usage = round(time.time())

    if guild := ctx.guild:
        guild_data = await bot.db.get_guild(guild)
        guild_data.latest_usage = round(time.time())
        guild_data.command_used += 1
        await bot.db.save(guild_data)

        if not guild.chunked:
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(guild.chunk(), timeout=15)

    public = await bot.db.get_public()
    public.command_used += 1
    public.latest_usage = round(time.time())
    cog_name = ctx.command.cog.qualified_name if ctx.command.cog else ""  # type: ignore
    if cog_name not in ("지샤쿠", "관리자"):
        cmd_name = ctx.command.qualified_name  # type: ignore
        public.commands[cmd_name] = public.commands.get(cmd_name, 0) + 1

    today = datetime.today().toordinal()
    if user.quest.status.date != today or user.quest.cache.keys() != public.quests.keys():
        user.quest.status.date = today
        user.quest.status.completed = []
        dump = user.model_dump()
        user.quest.cache = {data: get_nested_dict(dump, data.split("/")) for data in public.quests}

    await bot.db.save(user)
    await bot.db.save(public)

    if ctx.message.content:
        msg = ctx.message.content
    else:
        msg = f"/{ctx.command}"
    if isinstance(ctx.channel, discord.DMChannel):
        logger.command(f"{ctx.author} [{ctx.author.id}]  |  DM [{ctx.channel.id}]  |  {msg}")
    else:
        logger.command(f"{ctx.author} [{ctx.author.id}]  |  {ctx.guild} [{ctx.guild.id}]  |  {ctx.channel} [{ctx.channel.id}]  |  {msg}")  # type: ignore


@bot.event
async def on_command_completion(ctx: commands.Context) -> None:
    public = await bot.db.get_public()
    user = await bot.db.get_user(ctx.author)
    desc = ""
    for data, info in public.quests.items():
        value: int = get_nested_dict(user.model_dump(), data.split("/"))
        current = value - user.quest.cache.get(data, value)
        if current <= 0:
            user.quest.cache[data] = value
        elif (current >= info["target"]) and (data not in user.quest.status.completed):
            setattr(user, info["reward"][1], getattr(user, info["reward"][1]) + info["reward"][0])
            user.quest.status.completed.append(data)
            user.quest.total += 1
            desc += f"{info['name']} `+{info['reward'][0]}`{{{info['reward'][1]}}}\n"
    if desc:
        embed = discord.Embed(title="퀘스트 클리어!", description=fmt(desc), color=config.colors.green)
        embed.set_thumbnail(url=bot.emoji("congrats").url)
        embed.set_footer(text="'/퀘스트'를 사용하여 남은 퀘스트를 확인해 보세요!")
        await ctx.channel.send(embed=embed)

        if len(user.quest.status.completed) == 3:
            bonus_embed = discord.Embed(title="보너스 보상", description="오늘의 퀘스트를 모두 완료했습니다!", color=config.colors.green)
            bonus_point = random.randint(100, 200)
            bonus_medal = random.randint(1, 5)
            user.points += bonus_point
            user.medals += bonus_medal
            bonus_embed.add_field(name="추가 보상", value=fmt(f"+`{bonus_point}` {{points}}\n+`{bonus_medal}` {{medals}}"))
            bonus_embed.set_thumbnail(url=bot.emoji("bonus").url)
            await ctx.channel.send(embed=bonus_embed)

    alert_message = []
    alerts = {
        "attendance": "오늘의 출석체크를 완료하지 않았습니다.\n`/출석` 명령어를 사용하여 오늘의 출석체크를 완료하세요!",
        "announcements": "읽지 않은 공지가 있습니다.\n`/공지` 명령어를 사용하여 읽지 않은 공지를 확인해 보세요!",
    }
    for path, msg in alerts.items():
        if not getattr(user.alerts, path):
            alert_message.append(msg)
            setattr(user.alerts, path, True)
    if not user.alerts.reward and is_reward_claimable(user):
        alert_message.append("받을 수 있는 포인트가 있습니다.\n`/포인트` 명령어를 사용하여 포인트를 받아가세요!")
        user.alerts.reward = True
    if alert_message:
        await ctx.channel.send(f"{ctx.author.mention}\n\n" + "\n\n".join(alert_message))

    await bot.db.save(user)


@bot.check
async def check(ctx: commands.Context) -> bool:
    if ctx.guild and not ctx.channel.permissions_for(ctx.guild.me).send_messages:  # type: ignore
        try:
            embed = discord.Embed(
                title="오류",
                description=f"{ctx.channel.mention}에서 끝봇에게 메시지 보내기 권한이 없어서 명령어를 사용할 수 없습니다.\n"  # type: ignore
                f"끝봇에게 해당 권한을 지급한 후 다시 시도해주세요.",
                color=config.colors.red,
            )
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass
        return False

    return True


@bot.event
async def on_interaction(interaction: discord.Interaction) -> None:
    if interaction.type == discord.InteractionType.component:
        interaction_created = round(interaction.message.created_at.timestamp())  # type: ignore
        if interaction_created < bot.started_at:
            types = ["그룹은", "버튼은", "리스트는", "텍스트박스는"]
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=fmt(
                        f"{{denied}} 이 {types[interaction.data['component_type'] - 1]} 너무 오래되어 사용할 수 없어요.\n명령어를 새로 입력해주세요."  # type: ignore
                    ),
                    color=config.colors.red,
                ),
                ephemeral=True,
            )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError | commands.HybridCommandError) -> None:
    if not ctx.command:
        return
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.reply(
            fmt(
                f"{{denied}} `{ctx.command}` 명령어를 사용하려면 끝봇에게 `{', '.join(get_perm_name(i) for i in error.missing_permissions)}` 권한이 필요합니다."
            )
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply(
            fmt(
                f"{{denied}} `{ctx.command}` 명령어를 사용하시려면 `{', '.join(get_perm_name(i) for i in error.missing_permissions)}` 권한을 보유하고 있어야 합니다."
            )
        )
    elif isinstance(error, commands.errors.NotOwner):
        return
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.reply(fmt("{denied} DM으로는 실행할 수 없는 기능입니다."))
    elif isinstance(error, commands.errors.PrivateMessageOnly):
        await ctx.reply(fmt("{denied} DM으로만 실행할 수 있는 기능입니다."))
    elif isinstance(error, commands.CheckFailure):
        if ctx.command.name.startswith("$"):
            return
    elif isinstance(error, commands.errors.DisabledCommand):
        await ctx.reply(fmt("{denied} 일시적으로 사용할 수 없는 명령어 입니다. 잠시만 기다려 주세요!"))
    elif isinstance(error, commands.CommandOnCooldown):
        if ctx.author.id in config.admin and ctx.command.name != "override":
            try:
                await ctx.reinvoke()
                return
            except TypeError:
                pass
        embed = discord.Embed(
            title="잠깐!", description=f"<t:{round(time.time() + error.retry_after)}:R>에 다시 시도해 주세요.", color=config.colors.red
        )
        embed.set_thumbnail(url=bot.emoji("denied").url)
        await ctx.reply(embed=embed)
    elif isinstance(error, commands.BadUnionArgument):
        embed = discord.Embed(title=fmt("{stats} 프로필 조회 불가"), description="존재하지 않는 유저입니다.", color=config.colors.red)
        embed.set_thumbnail(url=bot.emoji("denied").url)
        await ctx.reply(embed=embed)
    elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.TooManyArguments)):
        usage = "사용법 도움말이 없습니다."
        if ctx.command.name != "jishaku" and ctx.command.help:
            for text in ctx.command.help.split("--"):
                if text.startswith("사용법"):
                    usage = text[3:]
        else:
            usage = ctx.command.help or usage
        embed = discord.Embed(title="잘못된 사용법입니다.", description=f"🔹 `{ctx.command}` **사용법**\n{usage}", color=config.colors.blue)
        embed.set_thumbnail(url=bot.emoji("denied").url)
        embed.set_footer(text="명령어 '/도움'을 사용하여 자세한 설명을 확인할 수 있습니다.")
        await ctx.reply(embed=embed)
    elif isinstance(error, commands.MaxConcurrencyReached):
        if error.per == commands.BucketType.guild:
            await ctx.reply(fmt(f"{{denied}} 해당 서버에서 이미 `{ctx.command}` 명령어가 진행중입니다."))
        elif error.per == commands.BucketType.channel:
            await ctx.reply(fmt(f"{{denied}} 해당 채널에서 이미 `{ctx.command}` 명령어가 진행중입니다."))
        elif error.per == commands.BucketType.user:
            await ctx.reply(fmt(f"{{denied}} 이미 `{ctx.command}` 명령어가 진행중입니다."))
        else:
            await ctx.reply(fmt(f"{{denied}} 이 명령어는 이미 {error.number}개 실행되어 있어 더 이상 실행할 수 없습니다."))
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        if hasattr(error, "original"):
            error = error.original

        te = traceback.TracebackException.from_exception(error, limit=None)
        all_frames = list(te.stack)
        cwd = os.getcwd()
        project_frames = [f for f in all_frames if f.filename.startswith(cwd) and ".venv" not in f.filename.split(os.sep)]
        extension_frames = [f for f in project_frames if f"extensions{os.sep}" in f.filename]
        frame = (extension_frames or project_frames or all_frames)[-1]
        filename = frame.filename
        line_no = frame.lineno or 0
        end_line_no = getattr(frame, "end_lineno", None) or line_no
        if end_line_no > line_no:
            line_text = "\n".join(linecache.getline(filename, ln).rstrip() for ln in range(line_no, end_line_no + 1))
        else:
            line_text = (frame.line or linecache.getline(filename, line_no)).strip()
        if "kkutbot" in filename:
            filename = filename.split("kkutbot/")[1]

        line_range = f"{line_no}~{end_line_no}" if end_line_no > line_no else line_no
        field_prefix = f"- 파일: {filename} (`line {line_range}`)\n```py\n"
        max_code_len = 1024 - len(field_prefix) - 3
        if len(line_text) > max_code_len:
            lines = line_text.splitlines()
            if len(lines) > 1:
                candidate = f"{lines[0]}\n(...)\n{lines[-1]}"
                line_text = candidate if len(candidate) <= max_code_len else f"{lines[0][: max_code_len - 6]}\n(...)"
            else:
                line_text = f"{line_text[: max_code_len - 6]}\n(...)"

        error_id = str(uuid.uuid4())[:6]
        error_embed = discord.Embed(title=":warning: 에러 발생", description=f"에러 ID: `{error_id}`", color=config.colors.red)
        if guild := ctx.guild:
            error_loc = f"- 서버: {guild} (`{guild.id}`)\n- 채널: {ctx.channel} (`{ctx.channel.id}`)"
        else:
            error_loc = f"- 채널: DM (`{ctx.channel.id}`)"
        error_embed.add_field(
            name="에러 발생 위치",
            value=f"- 유저: {ctx.author.name} (`{ctx.author.id}`)\n{error_loc}",
        )
        error_embed.add_field(name="에러 이름", value=f"`{error.__class__.__name__}`", inline=False)
        error_embed.add_field(name="에러 내용", value=f"```py\n{error}```", inline=False)
        error_embed.add_field(name="에러 코드", value=f"{field_prefix}{line_text}```", inline=False)
        error_embed.add_field(name="Sentry 링크", value=f"- [Issues]({config.sentry.url})", inline=False)

        if is_admin(ctx):
            await ctx.reply(embed=error_embed)
        else:
            embed = discord.Embed(title="에러 발생", description=f"알 수 없는 오류가 발생했습니다. (에러 ID: `{error_id}`)", color=config.colors.red)
            await ctx.reply(embed=embed, view=ServerInvite("커뮤니티에 문의하기"))
            await (bot.get_channel(config.channels.error_log)).send(embed=error_embed)  # type: ignore
        logger.error(
            f"에러 발생함. (명령어: {ctx.message.content if ctx.message else ctx.command})\n에러 이름: {error.__class__.__name__}\n에러 ID: {error_id}\n"
            f"에러 파일: {filename}\n에러 코드: {line_text} (line {line_no})",
            exc_info=error,
        )
        capture_exception(error)


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    guild_data = await bot.db.get_guild(guild)
    await bot.db.save(guild_data)
    logger.invite(f"'{guild.name}'에 초대됨. (총 {len(bot.guilds)}서버)")
    announce = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
    embed = discord.Embed(
        description="**끝봇**을 서버에 초대해 주셔서 감사합니다!\n"
        "끝봇은 끝말잇기가 주 기능인 **디스코드 인증**된 한국 디스코드 봇입니다.\n"
        "- **/도움** 명령어를 사용하여 끝봇의 도움말을 확인해 보세요!\n"
        "- 끝봇의 공지와 업데이트, 사용 도움을 받고 싶으시다면\n"
        "  아래 버튼을 눌러 끝봇 커뮤니티에 참가해 보세요!\n"
        "  `#업데이트-공지` 채널을 팔로우하면 끝봇의 업데이트 소식을 빠르게 받을 수 있습니다.\n\n"
        f"끝봇을 서버에 초대한 경우 [약관]({config.links.privacy_policy})에 동의한 것으로 간주됩니다.",
        color=config.colors.blue,
    )
    try:
        if announce:
            await announce.send(embed=embed, view=ServerInvite())
    except discord.errors.Forbidden:
        pass
    try:
        if owner_id := guild.owner_id:
            owner = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
            await owner.send(embed=embed, view=ServerInvite())
    except discord.errors.Forbidden:
        pass

    essential_perms = (
        "send_messages",
        "embed_links",
        "attach_files",
        "read_messages",
        "add_reactions",
        "external_emojis",
        "use_application_commands",
    )

    missing_perms = [p for p in essential_perms if not dict(guild.me.guild_permissions)[p]]

    if missing_perms:
        embed = discord.Embed(
            title="권한이 부족합니다.", description="끝봇이 정상적으로 작동하기 위해 필요한 필수 권한들이 부족합니다.", color=config.colors.red
        )
        embed.add_field(name="필수 권한 목록", value=f"`{'`, `'.join([get_perm_name(p) for p in missing_perms])}`")
        try:
            if announce:
                await announce.send(embed=embed)
            if owner_id := guild.owner_id:
                owner = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
                await owner.send(embed=embed)
        except discord.errors.Forbidden:
            pass


@bot.event
async def on_guild_remove(guild: discord.Guild) -> None:
    logger.leave(f"'{guild.name}'에서 추방됨. (총 {len(bot.guilds)}서버)")
    guild_data = await bot.db.get_guild(guild)
    await guild_data.delete()


if __name__ == "__main__":
    rich_install()
    setup_logger()
    logger.info(f"끝봇 v{config.version} 로그인 하는 중...")
    logger.info(f"{'테스트' if config.is_test else '프로덕션'} 모드로 가동합니다.")
    bot.run_bot()
