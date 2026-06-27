import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import escape_markdown as e_mk

from config import config
from core import Kkutbot
from tools.utils import fmt, get_tier, is_admin

from .views import ProfileMenu, SelfProfileMenu


class Profile(commands.Cog, name="사용자"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="프로필", usage="{profile}", aliases=("ㅍ", "ㅍㄹㅍ"))
    @app_commands.rename(user="유저")
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    @commands.bot_has_permissions(external_emojis=True)
    async def profile(self, ctx: commands.Context, *, user: discord.User | discord.Member = commands.Author):
        """
        유저의 프로필과 자세한 통계를 확인합니다.

        아래 버튼을 눌러 유저의 자세한 통계를 확인할 수 있습니다.
        자신의 프로필을 확인한 경우, 아래 버튼을 눌러 소개말을 변경할 수 있습니다!

        --사용법
        `/프로필`을 사용하여 자신의 프로필을 확인하고, 소개말을 변경합니다.
        `/프로필 @가나다` - 유저 '가나다'의 프로필과 통계를 확인합니다.
        """
        user_data = await ctx.bot.db.get_user(user)
        if int(user.discriminator):
            name = str(user.name)
        else:
            name = f"{user.display_name} ({user.name})"
        if not user_data.registered:
            embed = discord.Embed(
                title=fmt(f"{{stats}} {e_mk(name)} 님의 통계"), description="끝봇을 사용중인 유저가 아닙니다.", color=config.colors.red
            )
            embed.set_thumbnail(url=self.bot.emoji("denied").url)
            await ctx.reply(embed=embed)
            return

        if (color := user.color.value) == 0:
            if not (color := (await self.bot.fetch_user(user.id)).accent_color):
                color = discord.Color(0xFFFFFF)

        profile_embed = discord.Embed(
            title=fmt(f"{{profile}} {e_mk(name)} {'(' + str(user.id) + ')' if is_admin(ctx) else ''}"),
            description=fmt(
                f"```yaml\n{user_data.bio}```\n"
                f"{{tier}} 랭킹전 티어 - **{get_tier(user_data, 'rank_solo')}** | **{get_tier(user_data, 'rank_online')}**\n​"
            ),
            color=color,
        )
        profile_embed.add_field(name=fmt("{points} **포인트**"), value=f"{user_data.points}")
        profile_embed.add_field(name=fmt("{starter} **승률**"), value=f"{user_data.game.rank_solo.winrate}% | {user_data.game.rank_online.winrate}%")
        profile_embed.add_field(name=fmt("{medals} **메달**"), value=f"{user_data.medals}")
        profile_embed.set_thumbnail(url=user.display_avatar.url)
        profile_embed.set_footer(text=f"더 자세한 정보는 아래 '통계 확인하기' 버튼을 통해 확인할 수 있어요!{' ' * 65}​")

        stats_embed = discord.Embed(
            title=fmt(f"{{stats}} {e_mk(name)} 님의 통계"),
            description=f"가입일 : <t:{user_data.registered}:D>\n마지막 사용일 : <t:{user_data.latest_usage}:D>",
            color=config.colors.blue,
        )

        modes = {
            "rank_solo": user_data.game.rank_solo,
            "rank_online": user_data.game.rank_online,
            "kkd": user_data.game.kkd,
            "long": user_data.game.long,
            "guild_multi": user_data.game.guild_multi,
            "online_multi": user_data.game.online_multi,
        }
        for k, v in config.modelist.items():
            stats_embed.add_field(
                name=f"🔸 {k}", value=f"`{modes[v].win}` / `{modes[v].times}`회 승리 (`{modes[v].winrate}%`)\n최고 점수 : `{modes[v].best}`"
            )
        stats_embed.add_field(
            name="🔸 기타",
            value=f"출석 횟수 : `{user_data.attendance['times']}`\n"
            f"명령어 사용 횟수 : `{user_data.command_used}`\n"
            f"클리어한 퀘스트: `{user_data.quest.total}`",
        )
        stats_embed.set_footer(text=f"티어 정보는 웹사이트에서 확인할 수 있어요.{' ' * 100}​​​")

        if user.id == ctx.author.id:
            view = SelfProfileMenu(ctx, profile_embed=profile_embed, stats_embed=stats_embed)
        else:
            view = ProfileMenu(ctx, profile_embed=profile_embed, stats_embed=stats_embed)
        view.message = await ctx.reply(embed=profile_embed, view=view)
