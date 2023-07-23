import logging
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Type

import discord
from discord.ext import commands
from rich.traceback import install as rich_install

import core
from config import config, get_nested_dict
from tools.logger import setup_logger
from tools.utils import is_admin
from views import ServerInvite

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

        if not ctx.guild.chunked:
            await ctx.guild.chunk()

    public = await bot.db.get_public()
    public.command_used += 1
    public.latest_usage = round(time.time())
    cmd_name = ctx.command.qualified_name.replace('$', '_')
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


@bot.event
async def on_command_completion(ctx: core.KkutbotContext) -> None:
    public = await bot.db.get_public()
    user = await bot.db.get_user(ctx.author)
    desc = ""
    for data, info in public.quests.items():
        current = get_nested_dict(user.dict(), data.split("/")) - user.quest.cache[data]
        if current < 0:
            user.quest.cache[data] = get_nested_dict(user.dict(), data.split("/"))
        elif (current >= info["target"]) and (data not in user.quest.status.completed):
            setattr(user, info["reward"][1], getattr(user, info["reward"][1]) + info["reward"][0])
            user.quest.status.completed.append(data)
            user.quest.total += 1
            desc += f"{info['name']} `+{info['reward'][0]}`{{{info['reward'][1]}}}\n"
    if desc:
        embed = discord.Embed(
            title="퀘스트 클리어!",
            description=desc,
            color=config.colors.help
        )
        embed.set_thumbnail(url=bot.get_emoji(config.emojis["congrats"]).url)
        embed.set_footer(text="'/퀘스트'를 사용하여 남은 퀘스트를 확인해 보세요!")
        await ctx.reply(embed=embed)

        if len(user.quest.status.completed) == 3:
            bonus_embed = discord.Embed(
                title="보너스 보상",
                description="오늘의 퀘스트를 모두 완료했습니다!",
                color=config.colors.help
            )
            bonus_point = random.randint(100, 200)
            bonus_medal = random.randint(1, 5)
            user.points += bonus_point
            user.medals += bonus_medal
            bonus_embed.add_field(name="추가 보상", value=f"+`{bonus_point}` {{points}}\n+`{bonus_medal}` {{medals}}")
            bonus_embed.set_thumbnail(url=bot.get_emoji(config.emojis["bonus"]).url)
            await ctx.reply(embed=bonus_embed)

    alert_message = []
    alerts = {
        "attendance": "오늘의 출석체크를 완료하지 않았습니다.\n`/출석` 명령어를 사용하여 오늘의 출석체크를 완료하세요!",
        "reward": "일일 포인트를 받지 않았습니다.\n`/포인트` 명령어를 사용하여 일일 포인트를 받아가세요!",
        "announcements": "읽지 않은 공지가 있습니다.\n`/공지` 명령어를 사용하여 읽지 않은 공지를 확인해 보세요!"
    }
    for path, msg in alerts.items():
        if not getattr(user.alerts, path):
            alert_message.append(msg)
            setattr(user.alerts, path, True)
    if alert_message:
        await ctx.reply("\n\n".join(alert_message), mention_author=True)

    await bot.db.save(user)


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


@bot.event
async def on_command_error(ctx: core.KkutbotContext, error: Type[commands.CommandError | commands.HybridCommandError]) -> None:
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.reply(f"{{denyed}} `{ctx.command}` 명령어를 사용하려면 끝봇에게 `{', '.join(config.perms[i] for i in error.missing_permissions)}` 권한이 필요합니다.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.reply(f"{{denyed}} `{ctx.command}` 명령어를 사용하시려면 `{', '.join(config.perms[i] for i in error.missing_permissions)}` 권한을 보유하고 있어야 합니다.")
    elif isinstance(error, commands.errors.NotOwner):
        return
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.reply("{denyed} DM으로는 실행할 수 없는 기능입니다.")
    elif isinstance(error, commands.errors.PrivateMessageOnly):
        await ctx.reply("{denyed} DM으로만 실행할 수 있는 기능입니다.")
    elif isinstance(error, commands.CheckFailure):
        if ctx.command.name.startswith("$"):
            return
    elif isinstance(error, commands.errors.DisabledCommand):
        await ctx.reply("{denyed} 일시적으로 사용할 수 없는 명령어 입니다. 잠시만 기다려 주세요!")
    elif isinstance(error, commands.CommandOnCooldown):
        if ctx.author.id in config.admin and ctx.command.name != "override":
            try:
                return await ctx.reinvoke()
            except TypeError:
                pass
        embed = discord.Embed(
            title="잠깐!",
            description=f"<t:{round(time.time() + error.retry_after)}:R>에 다시 시도해 주세요.",
            color=config.colors.error
        )
        embed.set_thumbnail(url=bot.get_emoji(config.emojis["denyed"]).url)
        await ctx.reply(embed=embed)
    elif isinstance(error, commands.BadUnionArgument):
        embed = discord.Embed(
            title="{stats} 프로필 조회 불가",
            description="존재하지 않는 유저입니다.",
            color=config.colors.error
        )
        embed.set_thumbnail(url=bot.get_emoji(config.emojis["denyed"]).url)
        await ctx.reply(embed=embed)
    elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.TooManyArguments)):
        usage = "사용법 도움말이 없습니다."
        if ctx.command.name != "jishaku":
            for text in ctx.command.help.split("--"):
                if text.startswith("사용법"):
                    usage = text[3:]
        else:
            usage = ctx.command.help
        embed = discord.Embed(
            title="잘못된 사용법입니다.",
            description=f"🔹 `{ctx.command}` **사용법**\n{usage}",
            color=config.colors.general
        )
        embed.set_thumbnail(url=bot.get_emoji(config.emojis["denyed"]).url)
        embed.set_footer(text="명령어 '/도움'을 사용하여 자세한 설명을 확인할 수 있습니다.")
        await ctx.reply(embed=embed)
    elif isinstance(error, commands.MaxConcurrencyReached):
        if ctx.author.id in config.admin:
            try:
                await ctx.reinvoke()
            except TypeError:
                pass
        if error.per == commands.BucketType.guild:
            await ctx.reply(f"{{denyed}} 해당 서버에서 이미 `{ctx.command}` 명령어가 진행중입니다.")
        elif error.per == commands.BucketType.channel:
            await ctx.reply(f"{{denyed}} 해당 채널에서 이미 `{ctx.command}` 명령어가 진행중입니다.")
        elif error.per == commands.BucketType.user:
            await ctx.reply(f"{{denyed}} 이미 `{ctx.command}` 명령어가 진행중입니다.")
        else:
            await ctx.reply(f"{{denyed}} 이 명령어는 이미 {error.number}개 실행되어 있어 더 이상 실행할 수 없습니다.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        if error.__cause__:
            error = error.__cause__

        error_id = str(uuid.uuid4())[:6]
        error_embed = discord.Embed(title="에러 발생", description=f"에러 ID: `{error_id}`", color=config.colors.error)
        error_embed.add_field(name="에러 발생 위치", value=f"유저: {ctx.author}(`{ctx.author.id}`)\n서버: {ctx.guild}(`{ctx.guild.id}`)\n채널: {ctx.channel}(`{ctx.channel.id}`)")
        error_embed.add_field(name="에러 이름", value=f"`{error.__class__.__name__}`", inline=False)
        error_embed.add_field(name="에러 내용", value=f"```{error}```", inline=False)

        if is_admin(ctx):
            await ctx.reply(embed=error_embed)
        else:
            embed = discord.Embed(title="에러 발생", description=f"알 수 없는 오류가 발생했습니다. (에러 ID: `{error_id}`)", color=config.colors.error)
            await ctx.reply(embed=embed, view=ServerInvite("커뮤니티에 문의하기"))
            await (bot.get_channel(config.channels.error_log)).send(embed=error_embed)
        logger.error(
            f"에러 발생함. (명령어: {ctx.message.content if ctx.message else ctx.command})\n에러 이름: {error.__class__.__name__}\n에러 ID: {error_id}"
        )
        raise error


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    guild_data = await bot.db.get_guild(guild)
    await bot.db.save(guild_data)
    logger.invite(f"'{guild.name}'에 초대됨. (총 {len(bot.guilds)}서버)")
    announce = [ch for ch in guild.text_channels if dict(ch.permissions_for(guild.me))["send_messages"]][0]
    embed = discord.Embed(
        description="**끝봇**을 서버에 초대해 주셔서 감사합니다!\n"
                    "끝봇은 끝말잇기가 주 기능인 **디스코드 인증**된 한국 디스코드 봇입니다.\n"
                    "- **/도움** 명령어를 사용하여 끝봇의 도움말을 확인해 보세요!\n"
                    "- 끝봇의 공지와 업데이트, 사용 도움을 받고 싶으시다면\n"
                    "  아래 버튼을 눌러 끝봇 커뮤니티에 참가해 보세요!\n"
                    "  `#업데이트-공지` 채널을 팔로우하면 끝봇의 업데이트 소식을 빠르게 받을 수 있습니다.\n\n"
                    f"끝봇을 서버에 초대한 경우 [약관]({config.links.privacy_policy})에 동의한 것으로 간주됩니다.",
        color=config.colors.general
    )
    try:
        await announce.send(embed=embed, view=ServerInvite())
    except discord.errors.Forbidden:
        pass
    try:
        owner = await bot.fetch_user(guild.owner_id)
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
        "use_application_commands"
    )

    missing_perms = [p for p in essential_perms if not dict(guild.me.guild_permissions)[p]]

    if missing_perms:
        embed = discord.Embed(
            title="권한이 부족합니다.",
            description="끝봇이 정상적으로 작동하기 위해 필요한 필수 권한들이 부족합니다.",
            color=config.colors.error)
        embed.add_field(
            name="필수 권한 목록",
            value=f"`{'`, `'.join([config.perms[p] for p in missing_perms])}`"
        )
        try:
            await announce.send(embed=embed)
            owner = await bot.fetch_user(guild.owner_id)
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
    bot.run_bot()
