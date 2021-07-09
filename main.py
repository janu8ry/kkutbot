import logging
from typing import Type
import traceback

import discord
from discord.ext import commands
from rich.traceback import install as rich_install
import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

import core
from tools.logger import setup_logger
from tools.config import config

logger = logging.getLogger("kkutbot")

bot = core.Kkutbot()


def before_send(event, _):
    logger.debug("sentry에 에러 보고중...")
    return event


sentry_sdk.init(config("sentry_dsn"), release=bot.__version__, before_send=before_send)

ignore_logger("kkutbot")


@bot.event
async def on_ready():
    bot.reload_all()

    guilds = len(bot.guilds)
    users = await bot.db.user.count_documents({})
    unused = await bot.db.unused.count_documents({})

    logger.info(
        f"'{bot.user.name}'으로 로그인됨\n" f"서버수: {guilds}, 유저수: {users}, 미사용 유저수: {unused}"
    )

    await bot.update_presence()


@bot.event
async def on_shard_ready(shard_id):
    logger.info(f"{shard_id}번 샤드 준비 완료!")


@bot.event
async def on_message(message: discord.Message):
    # is_banned = await read(message.author, 'banned')

    if message.author.bot:  # or is_banned:
        return None
    else:
        if message.content.lstrip(
            config(f"prefix.{'test' if config('test') else 'main'}")
        ).startswith("jsk"):
            cls = commands.Context
        else:
            cls = core.KkutbotContext
        ctx = await bot.get_context(message, cls=cls)
        await bot.invoke(ctx)


@bot.event
async def on_command(ctx: core.KkutbotContext):
    if isinstance(ctx.channel, discord.DMChannel):
        logger.command(
            f"{ctx.author} [{ctx.author.id}]  |  DM [{ctx.channel.id}]  |  {ctx.message.content}"
        )
    else:
        logger.command(
            f"{ctx.author} [{ctx.author.id}]  |  {ctx.guild} [{ctx.guild.id}]  |  {ctx.channel} [{ctx.channel.id}]  |  {ctx.message.content}"
        )


@bot.check
async def check(ctx: core.KkutbotContext):
    if ctx.guild and not ctx.guild.me.permissions_in(ctx.channel).send_messages:
        try:
            embed = discord.Embed(
                title="오류",
                description=f"{ctx.channel.mention}에서 끝봇에게 메시지 보내기 권한이 없어서 명령어를 사용할 수 없습니다.\n"
                f"끝봇에게 해당 권한을 지급한 후 다시 시도해주세요.",
                color=config("colors.error"),
            )
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass
        return False
    return True


@bot.event
async def on_command_error(
    ctx: core.KkutbotContext, error: Type[commands.CommandError]
):
    if isinstance(error, commands.errors.BotMissingPermissions):
        await ctx.send(
            f"`{ctx.command}` 명령어를 사용하려면 끝봇에게 `{', '.join(config('perms')[i] for i in error.missing_perms)}` 권한이 필요합니다."
        )
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.send(
            f"`{ctx.command}` 명령어를 사용하시려면 `{', '.join(config('perms')[i] for i in error.missing_perms)}` 권한을 보유하고 있어야 합니다."
        )
    elif isinstance(error, commands.errors.NotOwner):
        return
    elif isinstance(error, commands.errors.NoPrivateMessage):
        await ctx.send("DM으로는 실행할 수 없는 기능입니다.")
    elif isinstance(error, commands.errors.PrivateMessageOnly):
        await ctx.send("DM으로만 실행할 수 있는 기능입니다.")
    elif isinstance(error, commands.errors.CheckFailure):
        if ctx.command.name.startswith("$"):
            return
    elif isinstance(error, commands.errors.DisabledCommand):
        await ctx.send("현 버전에서는 사용할 수 없는 명령어 입니다. 다음 업데이트를 기다려 주세요!")
    # elif isinstance(error, commands.errors.CommandOnCooldown):
    #     if ctx.author.id == bot.owner_id:
    #         return await ctx.reinvoke()
    #     embed = discord.Embed(
    #         title="잠깐!",
    #         description=f"`{time_convert(round(error.retry_after, 1))}` 후에 다시 시도해 주세요.",
    #         color=config('colors.error')
    #     )
    #     await ctx.send(embed=embed)
    elif isinstance(
        error, (commands.errors.MissingRequiredArgument, commands.errors.BadArgument)
    ):
        embed = discord.Embed(
            title="잘못된 사용법입니다.",
            description=f"`{ctx.command}` 사용법:\n{ctx.command.usage}\n\n",
            color=config("colors.general"),
        )
        embed.set_footer(
            text=f"명령어 'ㄲ도움 {ctx.command.name}' 을(를) 사용하여 자세한 설명을 확인할 수 있습니다."
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.errors.MaxConcurrencyReached):
        if ctx.author.id == bot.owner_id:
            return await ctx.reinvoke()
        if error.per == commands.BucketType.guild:
            await ctx.send(f"해당 서버에서 이미 `{ctx.command}` 명령어가 진행중입니다.")
        elif error.per == commands.BucketType.channel:
            await ctx.send(f"해당 채널에서 이미 `{ctx.command}` 명령어가 진행중입니다.")
        elif error.per == commands.BucketType.user:
            await ctx.send(f"이미 `{ctx.command}` 명령어가 진행중입니다.")
        else:
            await ctx.send(f"이 명령어는 이미 {error.number}개 실행되어 있어 더 이상 실행할 수 없습니다.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        if error.__cause__:
            error = error.__cause__

        error_log = "".join(
            traceback.format_exception(
                type(error), error, error.__traceback__, chain=False
            )
        )

        embed = discord.Embed(title="에러", color=config("colors.error"))
        embed.add_field(name="에러 코드", value=f"```{error}```")
        embed.set_footer(text="끝봇 공식 커뮤니티에서 개발자에게 제보해 주세요!")
        await ctx.send(embed=embed)
        logger.error(f"에러 발생함. (명령어: {ctx.command.name})\n에러 내용: {error_log}")
        sentry_sdk.capture_exception(error)


@bot.event
async def on_guild_join(guild: discord.Guild):
    # await write(guild, 'invited', datetime.now())
    logger.invite(f"'{guild.name}'에 초대됨. (총 {len(bot.guilds)}개)")
    announce = [
        ch
        for ch in guild.text_channels
        if dict(ch.permissions_for(guild.me))["send_messages"]
    ]
    embed = discord.Embed(
        description=f"""
**끝봇**을 서버에 초대해 주셔서 감사합니다!
끝봇은 끝말잇기가 주 기능인 **디스코드 인증**된 한국 디스코드 봇입니다.
- **ㄲ도움** 을 입력하여 끝봇의 도움말을 확인해 보세요!
- 끝봇의 공지와 업데이트, 사용 도움을 받고 싶으시다면
[끝봇 공식 커뮤니티]({config('links.invite.server')})에 참가해 보세요!
끝봇을 서버에 초대한 경우 [약관]({config('links.privacy-policy')})에 동의한 것으로 간주됩니다.
""",
        color=config("colors.general"),
    )
    try:
        await announce[0].send(embed=embed)
    except discord.errors.Forbidden:
        pass

    essential_perms = (
        "send_messages",
        "embed_links",
        "attach_files",
        "read_messages",
        "add_reactions",
        "external_emojis",
    )

    missing_perms = [
        p for p in essential_perms if not dict(guild.me.guild_permissions)[p]
    ]

    if missing_perms:
        embed = discord.Embed(
            title="권한이 부족합니다.",
            description="끝봇이 정상적으로 작동하기 위해 필요한 필수 권한들이 부족합니다.",
            color=config("colors.error"),
        )
        embed.add_field(
            name="더 필요한 권한 목록",
            value=f"`{'`, `'.join([config('perms')[p] for p in missing_perms])}`",
        )
        try:
            await announce[0].send(embed=embed)
            owner = await bot.fetch_user(guild.owner_id)
            await owner.send(embed=embed)
        except discord.errors.Forbidden:
            pass


@bot.event
async def on_guild_remove(guild: discord.Guild):
    logger.leave(f"'{guild.name}'에서 추방됨. (총 {len(bot.guilds)}개)")
    # await delete(guild)


if __name__ == "__main__":
    rich_install()
    setup_logger()
    bot.run_bot()
