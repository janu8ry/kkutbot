import os
import time
import traceback
from datetime import date, datetime
from typing import Type

import discord
from discord.ext import commands

from ext.core import Kkutbot, KkutbotContext
from ext.db import add, append, config, delete, read, write
from ext.utils import time_convert

os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'  # jishaku config

bot = Kkutbot(
    command_prefix=commands.when_mentioned_or(config('prefix')),
    help_command=None,  # disables the default help command
    intents=discord.Intents.default(),
    activity=discord.Game("봇 로딩"),
    owner_id=610625541157945344,
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
    strip_after_prefix=True  # allows 'ㄲ ' prefix
)


@bot.event
async def on_ready():
    print("-" * 75)
    for cogname in os.listdir("cogs"):
        if cogname.endswith(".py"):
            bot.try_reload(cogname[:-3])
            print(f"카테고리 '{cogname[:-3]}'을(를) 불러왔습니다!")
    print("-" * 75)
    print(f"'{bot.user.name}'으로 로그인됨")

    guilds = len(bot.guilds)
    users = await bot.db.user.count_documents({})
    unused = await bot.db.unused.count_documents({})

    print(f"서버수: {guilds}, 유저수: {users}, 미사용 유저수: {unused}")
    print("-" * 75)
    await bot.update_presence()


@bot.event
async def on_shard_ready(shard_id):
    print(f"{shard_id}번 샤드 준비 완료!")


@bot.event
async def on_message(message: discord.Message):
    is_banned = await read(message.author, 'banned')
    is_bot = message.author.bot and (message.author.id not in config('bot_whitelist'))

    if is_banned or is_bot:
        return None
    else:
        if message.content.lstrip("ㄲ").startswith("jsk"):
            cls = commands.Context
        else:
            cls = KkutbotContext
        ctx = await bot.get_context(message, cls=cls)
        await bot.invoke(ctx)


@bot.event
async def on_command(ctx: KkutbotContext):
    if isinstance(ctx.channel, discord.DMChannel):
        await bot.log(f"{ctx.author} [`{ctx.author.id}`]  |  DM [`{ctx.channel.id}`]  |  {ctx.message.content}")
    else:
        await bot.log(f"{ctx.author} [`{ctx.author.id}`]  |  {ctx.guild} [`{ctx.guild.id}`]  |  {ctx.channel} [`{ctx.channel.id}`]  |  {ctx.message.content}")


@bot.event
async def on_command_completion(ctx: KkutbotContext):
    await add(ctx.author, 'command_used', 1)
    await write(ctx.author, 'last_command', time.time())

    if ctx.guild:
        await write(ctx.guild, 'last_command', time.time())
        await add(ctx.guild, 'command_used', 1)

    await add(None, 'command_used', 1)
    await write(None, 'last_command', time.time())
    await add(None, f"commands.{ctx.command.qualified_name.replace('$', '_')}", 1)

    if (await read(ctx.author, 'quest.status.date')) != (today := date.today().toordinal()):
        await write(ctx.author, 'quest.status', {'date': today, 'completed': []})
        cache = {}
        for data in (await read(None, 'quest')).keys():
            cache[data] = await read(ctx.author, data.replace("/", "."))
        await write(ctx.author, 'quest.cache', cache)

    desc = ""
    for data, info in (await read(None, 'quest')).items():
        current = await read(ctx.author, data.replace("/", ".")) - (await read(ctx.author, f'quest.cache.{data}'))
        if current < 0:
            await write(ctx.author, f'quest.cache.{data}', await read(ctx.author, data.replace("/", ".")))
        elif (current >= info['target']) and (data not in await read(ctx.author, 'quest.status.completed')):
            await add(ctx.author, info['reward'][1], info['reward'][0])
            await append(ctx.author, 'quest.status.completed', data)
            desc += f"{info['name']} `+{info['reward'][0]}`{{{info['reward'][1]}}}\n"
    if desc:
        embed = discord.Embed(
            title="퀘스트 클리어!",
            description=desc,
            color=config('colors.help')
        )
        embed.set_thumbnail(url=bot.get_emoji(config('emojis.congrats')).url)
        embed.set_footer(text="'ㄲ퀘스트' 명령어를 입력하여 남은 퀘스트를 확인해 보세요!")
        await ctx.send(ctx.author.mention, embed=embed)

    if not (await read(ctx.author, 'alert.daily')):
        await ctx.send(
            f"{ctx.author.mention}님, 오늘의 출석체크를 완료하지 않았습니다.\n`ㄲ출석`을 입력하여 오늘의 출석체크를 완료하세요!"
        )
        await write(ctx.author, 'alert.daily', True)

    if not (await read(ctx.author, 'alert.heart')):
        await ctx.send(
            f"{ctx.author.mention}님, 일일 포인트를 받지 않았습니다.\n`ㄲ포인트`을 입력하여 일일 포인트를 받아가세요!"
        )
        await write(ctx.author, 'alert.heart', True)

    if not (await read(ctx.author, 'alert.mail')):
        mails = len([x for x in (await read(ctx.author, 'mail')) if (datetime.now() - x['time']).days <= 14])
        if mails > 0:
            await ctx.send(
                f"{ctx.author.mention}님, 읽지 않은 메일이 "
                f"`{len([x for x in (await read(ctx.author, 'mail')) if (datetime.now() - x['time']).days <= 14])}`개 있습니다.\n"
                "`ㄲ메일`을 입력하여 읽지 않은 메일을 확인해 보세요!"
            )
        await write(ctx.author, 'alert.mail', True)


@bot.check
async def check(ctx: KkutbotContext):
    if ctx.guild and not ctx.guild.me.permissions_in(ctx.channel).send_messages:
        try:
            embed = discord.Embed(
                title="오류",
                description=f"{ctx.channel.mention}에서 끝봇에게 메시지 보내기 권한이 없어서 명령어를 사용할 수 없습니다.\n"
                            f"끝봇에게 해당 권한을 지급한 후 다시 시도해주세요.", color=config('colors.error')
            )
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            pass
        return False
    return True


@bot.event
async def on_command_error(ctx: KkutbotContext, error: Type[commands.CommandError]):
    if isinstance(error, commands.errors.BotMissingPermissions):
        await ctx.send(f"`{ctx.command}` 명령어를 사용하려면 끝봇에게 `{', '.join(config('perms')[i] for i in error.missing_perms)}` 권한이 필요합니다.")
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.send(f"`{ctx.command}` 명령어를 사용하시려면 `{', '.join(config('perms')[i] for i in error.missing_perms)}` 권한을 보유하고 있어야 합니다.")
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
    elif isinstance(error, commands.errors.CommandOnCooldown):
        if ctx.author.id == bot.owner_id:
            return await ctx.reinvoke()
        embed = discord.Embed(
            title="잠깐!",
            description=f"`{time_convert(round(error.retry_after, 1))}` 후에 다시 시도해 주세요.",
            color=config('colors.error')
        )
        await ctx.send(embed=embed)
    elif isinstance(error, (commands.errors.MissingRequiredArgument, commands.errors.BadArgument)):
        embed = discord.Embed(
            title="잘못된 사용법입니다.",
            description=f"`{ctx.command}` 사용법:\n{ctx.command.usage}\n\n",
            color=config('colors.general')
        )
        embed.set_footer(text=f"명령어 'ㄲ도움 {ctx.command.name}' 을(를) 사용하여 자세한 설명을 확인할 수 있습니다.")
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
        if not error.__cause__:
            err = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))
        else:
            err = ''.join(traceback.format_exception(type(error.__cause__), error.__cause__, error.__cause__.__traceback__))

        embed = discord.Embed(title="에러", color=config('colors.error'))
        embed.add_field(name="에러 코드", value=f"```{error}```")
        embed.set_footer(text="끝봇 공식 커뮤니티에서 개발자에게 제보해 주세요!")
        await ctx.send(embed=embed)
        embed.add_field(name="에러 traceback", value=f"""```py\n{err}```""", inline=False, escape_emoji_formatting=True)  # noqa
        await bot.log(f"에러 발생함. \n명령어: {ctx.command.name}", embed=embed)
        if config('test'):
            print(err)


@bot.event
async def on_guild_join(guild: discord.Guild):
    await write(guild, 'invited', datetime.now())
    await bot.log(f"{guild.name}에 봇 새로 초대됨. 현재 {len(bot.guilds)}개 서버 참여중")
    if len(bot.guilds) % 100 == 0:
        await bot.log(f"<@610625541157945344> `{len(bot.guilds)}`서버 달성", nomention=False)
    announce = [ch for ch in guild.text_channels if dict(ch.permissions_for(guild.me))['send_messages']]
    embed = discord.Embed(
        description=f"""
**끝봇**을 서버에 초대해 주셔서 감사합니다!
끝봇은 끝말잇기가 주 기능인 **디스코드 인증**된 한국 디스코드 봇입니다.

- **ㄲ도움** 을 입력하여 끝봇의 도움말을 확인해 보세요!
- 끝봇의 공지와 업데이트, 사용 도움을 받고 싶으시다면
[끝봇 공식 커뮤니티]({config('links.invite.server')})에 참가해 보세요!

끝봇을 서버에 초대한 경우 [약관]({config('links.privacy-policy')})에 동의한 것으로 간주됩니다.
""",
        color=config('colors.general')
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
        "external_emojis"
    )

    missing_perms = [p for p in essential_perms if not dict(guild.me.guild_permissions)[p]]

    if missing_perms:
        embed = discord.Embed(
            title="권한이 부족합니다.",
            description="끝봇이 정상적으로 작동하기 위해 필요한 필수 권한들이 부족합니다.",
            color=config('colors.error'))
        embed.add_field(
            name="더 필요한 권한 목록",
            value=f"`{'`, `'.join([config('perms')[p] for p in missing_perms])}`"
        )
        try:
            await announce[0].send(embed=embed)
            owner = await bot.fetch_user(guild.owner_id)
            await owner.send(embed=embed)
        except discord.errors.Forbidden:
            pass


@bot.event
async def on_guild_remove(guild: discord.Guild):
    await bot.log(f"{guild.name}에서 봇 추방됨. 현재 {len(bot.guilds)}개 서버 참여중")
    await delete(guild)


print("로그인하는 중...")
bot.run(config(f"token.{'test' if config('test') else 'main'}"))  # todo: 모든 명령어 도움말 웹사이트에 추가
