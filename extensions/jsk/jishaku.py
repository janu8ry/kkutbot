import itertools
import logging
import os.path
import sys
import time
import traceback
from importlib.metadata import distribution, packages_distributions
from typing import Any, Iterable

import discord
import psutil  # noqa
from discord.ext import commands
from humanize import naturalsize
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature
from jishaku.flags import Flags
from jishaku.modules import ExtensionConverter, package_version
from jishaku.types import ContextA

from config import config
from database.models import Guild, Public, User
from tools.utils import get_timestamp

logger = logging.getLogger("kkutbot")

Flags.NO_UNDERSCORE = True
Flags.FORCE_PAGINATOR = True


class CustomJSK(*STANDARD_FEATURES, *OPTIONAL_FEATURES, name="지샤쿠"):
    """jishaku의 커스텀 확장 명령어들입니다."""

    def jsk_python_get_convertables(self, ctx: ContextA) -> tuple[dict[str, Any], dict[str, str]]:
        arg_dict, convertables = super().jsk_python_get_convertables(ctx)
        extra_vars = {
            "e_mk": discord.utils.escape_markdown,
            "e_mt": discord.utils.escape_mentions,
            "db": ctx.bot.db,  # type: ignore
            "User": User,
            "Guild": Guild,
            "General": Public,
            "config": config,
            "logger": logger,
            "get_timestamp": get_timestamp,
        }
        for key, value in extra_vars.items():
            arg_dict[f"{Flags.SCOPE_PREFIX}{key}"] = value
        return arg_dict, convertables

    @Feature.Command(name="jishaku", aliases=["ㅈ", "jsk"], invoke_without_command=True, ignore_extra=False)
    async def jsk(self, ctx: ContextA, days: int = 7):
        """
        The Jishaku debug and diagnostic commands.
        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """

        # Try to locate what vends the `discord` package
        distributions: list[str] = [
            dist
            for dist in packages_distributions()["discord"]
            if any(file.parts == ("discord", "__init__.py") for file in distribution(dist).files)  # type: ignore
        ]

        if distributions:
            dist_version = f"{distributions[0]} `{package_version(distributions[0])}`"
        else:
            dist_version = f"unknown `{discord.__version__}`"

        summary = [
            f"Jishaku `{package_version('jishaku')}`",
            dist_version,
            f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
            f"봇은 <t:{self.load_time.timestamp():.0f}:R>에 로딩되었고, 카테고리는 <t:{self.start_time.timestamp():.0f}:R>에 로딩되었습니다.",
            "",
        ]

        try:
            proc = psutil.Process()

            with proc.oneshot():
                try:
                    mem = proc.memory_full_info()
                    summary.append(
                        f"`{naturalsize(mem.rss)}`의 물리적 메모리와 "
                        f"`{naturalsize(mem.vms)}`의 가상 메모리, "
                        f"`{naturalsize(mem.uss)}`의 고유 메모리를 사용하고 있습니다."
                    )
                except psutil.AccessDenied:
                    pass

                try:
                    name = proc.name()
                    pid = proc.pid
                    thread_count = proc.num_threads()

                    summary.append(f"PID {pid} (`{name}`) 에서 `{thread_count}` 개의 스레드 작동중입니다.")
                except psutil.AccessDenied:
                    pass

                summary.append("")
        except psutil.AccessDenied:
            summary.append("psutil이 설치되어 있지만, 권한이 부족하여 기능을 사용할 수 없습니다.")
            summary.append("")

        cache_summary = (
            f"`{len(self.bot.guilds)}`개의 서버와 `{await self.bot.db.count_users()}`명의 유저,\n"
            f"`{await User.find(User.latest_usage >= round(time.time() - 86400 * days)).count()}`명의 활성화 유저, "  # type: ignore
            f"`{await Guild.find(Guild.latest_usage >= round(time.time() - 86400 * days)).count()}`개 활성화 서버"  # type: ignore
        )

        summary.append(f"샤드 수는 `{self.bot.shard_count}`개이며, {cache_summary}와 활동하고 있습니다.")

        if self.bot._connection.max_messages:  # noqa
            message_cache = f"메시지 캐시가 `{self.bot._connection.max_messages}`(으)로 제한되어있습니다."  # noqa
        else:
            message_cache = "메시지 캐시가 비활성화 되어있습니다."

        *group, last = (
            f"{intent.replace('_', ' ')} 인텐트: `{'활성화' if getattr(self.bot.intents, intent, False) else '비활성화'}`"
            for intent in ("presences", "members", "message_content")
        )

        summary.append(message_cache)
        summary.append(f"{', '.join(group)}, {last}.")
        summary.append("")

        size = 0
        for collection in ("user", "guild", "public"):
            size += float((await self.bot.db.client.command("collstats", collection))["size"])

        t1 = time.time()
        await self.bot.db.client.public.find_one({"_id": "public"})
        t1 = time.time() - t1

        t2 = time.time()
        await self.bot.db.client.public.update_one({"_id": "public"}, {"$set": {"latest_usage": round(time.time())}})
        t2 = time.time() - t2
        database_summary = (
            f"데이터베이스의 용량은 `{naturalsize(size)}`이며,\n"
            f"조회 지연 시간은 `{round(t1 * 1000)}`ms, 업데이트 지연 시간은 `{round(t2 * 1000)}`ms 입니다."
        )

        summary.append(database_summary)
        summary.append("")

        summary.append(f"평균 웹소켓 지연시간: `{round(self.bot.latency * 1000, 2)}`ms")
        summary.append("")
        summary.append(f"출석 유저 수: `{(await self.bot.db.get_public()).attendance}`명")

        await ctx.reply("\n".join(summary))

    @Feature.Command(parent="jsk", name="load", aliases=["reload", "ㄹ"])
    async def jsk_load(self, ctx: ContextA, *extensions: ExtensionConverter):
        """
        Loads or reloads the given extension names.
        Reports any extensions that failed to load.
        """

        extensions: Iterable[list[str]] = extensions  # type: ignore

        paginator = commands.Paginator(prefix="", suffix="")

        # 'jsk reload' on its own just reloads jishaku
        if ctx.invoked_with == "reload" and not extensions:
            extensions = [["extensions.jsk"]]
        elif ctx.invoked_with == "ㄹ" and not extensions:
            extensions = [[f"extensions.{extension}" for extension in os.listdir("extensions") if os.path.isdir(f"extensions/{extension}")]]

        for extension in itertools.chain(*extensions):
            method, icon = (
                (self.bot.try_reload, "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await discord.utils.maybe_coroutine(method, extension)
                logger.info(f"카테고리 '{extension}'을(를) 불러왔습니다!")
            except Exception as exc:
                traceback_data = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, 1))

                paginator.add_line(f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```", empty=True)
            else:
                paginator.add_line(f"{icon} `{extension}`", empty=True)

        for page in paginator.pages:
            await ctx.reply(page)

    @Feature.Command(parent="jsk", name="shutdown", aliases=["logout", "종료", "로그아웃", "ㅈㄹ"])
    async def jsk_shutdown(self, ctx: ContextA):
        """
        Logs this bot out.
        """

        ellipse_character = "\N{BRAILLE PATTERN DOTS-356}" if Flags.USE_BRAILLE_J else "\N{HORIZONTAL ELLIPSIS}"

        await ctx.reply(f"로그아웃합니다{ellipse_character}")
        logger.info("봇이 정상적으로 종료되었습니다!")
        await ctx.bot.close()
