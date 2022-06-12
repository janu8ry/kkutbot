from datetime import datetime
from typing import Optional
import asyncio

import discord
from discord.ext import commands
from discord.utils import escape_markdown as e_mk
from discord.utils import escape_mentions as e_mt
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor  # noqa

from tools.db import db, write, read
from tools.utils import disable_buttons, is_admin
from .config import config, get_nested_dict  # noqa


class DefaultView(discord.ui.View):
    def __init__(self, ctx, *args, author_only=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.author_only = author_only
        self.timeout = 120
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_only and (interaction.user != self.ctx.author):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="이 명령어를 실행한 사람만 사용할 수 있어요.\n직접 명령어를 입력하여 사용해주세요.",
                    color=config("colors.error")
                ),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if not getattr(item, "url", None):
                item.disabled = True
        if self.message:
            await self.message.edit(view=self)


class DefaultModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = 120


class ConfirmSendAnnouncement(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label='전송하기', style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = True
        await interaction.channel.send("공지 전송 완료!")
        await disable_buttons(interaction, view=self)
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = False
        await interaction.channel.send("공지 전송이 취소되었습니다.")
        await disable_buttons(interaction, view=self)
        self.stop()


class AnnouncementInput(DefaultModal, title='공지 작성하기'):
    a_title = discord.ui.TextInput(label='공지 제목', required=True, max_length=256)
    description = discord.ui.TextInput(label='공지 본문', style=discord.TextStyle.long, required=True, max_length=1024)

    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{{email}} **{interaction.user.name}** 님의 메일함",
            color=config('colors.help')
        )
        embed.add_field(name=f"🔹 {self.a_title.value} - `1초 전`", value=self.description.value)
        view = ConfirmSendAnnouncement(ctx=self.ctx)
        await interaction.response.send_message("**<공지 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await db.general.update_one(
                {"_id": "general"},
                {
                    '$push': {'announcements': {'title': self.a_title.value, 'value': self.description.value, 'time': datetime.now()}}
                }
            )
            await db.user.update_many(
                {},
                {
                    '$set': {'alerts.announcements': False}
                }
            )


class SendAnnouncement(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.ctx = ctx

    @discord.ui.button(label='내용 작성하기', style=discord.ButtonStyle.blurple)
    async def msg_input(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnnouncementInput(ctx=self.ctx))
        button.disabled = True
        await self.message.edit(view=self)
        self.value = True
        self.stop()


class ConfirmSendNotice(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label='전송하기', style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = True
        await interaction.channel.send("알림 전송 완료!")
        await disable_buttons(interaction, view=self)
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = False
        await interaction.channel.send("알림 전송이 취소되었습니다.")
        await disable_buttons(interaction, view=self)
        self.stop()


class NoticeInput(DefaultModal, title='알림 보내기'):
    msg = discord.ui.TextInput(label='알림 내용', style=discord.TextStyle.long, required=True, max_length=1024)

    def __init__(self, ctx: commands.Context, target: int):
        super().__init__()
        self.target = target
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{{email}} **{interaction.user.name}** 님의 메일함",
            color=config('colors.help')
        )
        embed.add_field(name="🔹 관리자로부터의 알림 - `1초 전`", value=self.msg.value)
        view = ConfirmSendNotice(ctx=self.ctx)
        await interaction.response.send_message("**<알림 미리보기>**", embed=embed, view=view)
        await view.wait()
        if view.value:
            await db.user.update_one(
                {'_id': self.target},
                {
                    '$push': {'mails': {'title': "관리자로부터의 알림", 'value': self.msg.value, 'time': datetime.now()}},
                    '$set': {'alerts.mails': False}
                }
            )


class SendNotice(DefaultView):
    def __init__(self, ctx: commands.Context, target: int):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.target = target
        self.ctx = ctx
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label='내용 작성하기', style=discord.ButtonStyle.blurple)
    async def msg_input(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NoticeInput(ctx=self.ctx, target=self.target))
        button.disabled = True
        await self.message.edit(view=self)
        self.value = True
        self.stop()


class ServerInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="서포트 서버 참가하기", style=discord.ButtonStyle.grey, url=config("links.invite.server")
            )
        )


class BotInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config("links.invite.bot")
            )
        )


class KoreanBotsVote(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="끝봇에게 하트추가", style=discord.ButtonStyle.grey, url=config('links.koreanbots')
            )
        )


class HelpDropdown(discord.ui.Select):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        cog_list = list(dict(ctx.bot.cogs).keys())
        cog_list.remove("지샤쿠")
        if not is_admin(ctx):
            cog_list.remove("관리자")
        options = []
        for cogname in cog_list:
            cog = ctx.bot.get_cog(cogname)
            option = discord.SelectOption(
                label=cog.qualified_name,
                value=cog.qualified_name,
                description=cog.description,
                emoji="<:help:715549237022163005>"
            )
            options.append(option)
        super().__init__(placeholder="카테고리를 선택해 주세요.", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        cog_data = self.ctx.bot.get_cog(self.values[0])
        embed = discord.Embed(
            title=f"{{help}} {self.values[0]} 명령어 도움말",
            description=cog_data.description,
            color=config("colors.help")
        )
        for cmd in cog_data.get_commands():
            if not cmd.hidden:
                embed.add_field(
                    name=f"🔹 {cmd.name}",
                    value=f"{cmd.help}\n\n사용 방법: `{cmd.usage}`",
                    inline=False
                )
        embed.set_footer(text="도움이 필요하다면 서포트 서버에 참가해보세요!")
        self.view.children[0].disabled = False  # noqa
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpMenu(DefaultView):
    def __init__(self, ctx: commands.Context, home_embed: discord.Embed):
        super().__init__(ctx=ctx, author_only=True)
        self.home_embed = home_embed
        self.add_item(
            discord.ui.Button(
                label="끝봇 초대하기", style=discord.ButtonStyle.grey, url=config("links.invite.bot")
            )
        )
        self.add_item(
            discord.ui.Button(
                label="서포트 서버 참가하기", style=discord.ButtonStyle.grey, url=config("links.invite.server")
            )
        )
        self.add_item(
            discord.ui.Button(
                label="하트 누르기", style=discord.ButtonStyle.red, url=f"{config('links.koreanbots')}/vote"
            )
        )
        self.add_item(HelpDropdown(ctx))

    @discord.ui.button(label="홈", style=discord.ButtonStyle.blurple, emoji="🏠", row=2, disabled=True)
    async def go_home(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        await interaction.response.edit_message(embed=self.home_embed, view=self)


class ConfirmModifyData(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None

    @discord.ui.button(label='수정하기', style=discord.ButtonStyle.green)
    async def confirm_send(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = True
        await interaction.channel.send("데이터 수정 완료!")
        await disable_buttons(interaction, view=self)
        self.stop()

    @discord.ui.button(label='취소하기', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        self.value = False
        await interaction.channel.send("데이터 수정이 취소되었습니다.")
        await disable_buttons(interaction, view=self)
        self.stop()


class DataInput(DefaultModal, title="데이터 수정하기"):
    data_target = discord.ui.TextInput(label='타깃 아이디', required=True)
    data_path = discord.ui.TextInput(label='수정할 데이터 경로', required=True)
    data_value = discord.ui.TextInput(label='수정할 값', style=discord.TextStyle.long, required=True)

    def __init__(self, ctx: commands.Context, collection: AsyncIOMotorCollection):
        super().__init__()
        self.colection = collection
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="데이터 수정 확인",
            description=f"수정 대상: {self.colection.name} - {self.data_target.value}",
            color=config('colors.help')
        )
        embed.add_field(name=f"수정할 데이터: {self.data_path.value}", value=self.data_value.value)
        view = ConfirmModifyData(ctx=self.ctx)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        if view.value:
            final_data = self.data_value.value.strip()
            if final_data == "True":
                final_data = True
            elif final_data == "False":
                final_data = False
            elif final_data.isdecimal():
                final_data = int(self.data_value.value)
            await self.colection.update_one(
                {'_id': int(self.data_target.value)},
                {
                    '$set': {self.data_path.value: final_data}
                }
            )


class ModifyData(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.value = None
        self.ctx = ctx

    @discord.ui.button(label='유저', style=discord.ButtonStyle.green)
    async def modify_user(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(DataInput(ctx=self.ctx, collection=db.user))
        self.value = True
        self.stop()

    @discord.ui.button(label='서버', style=discord.ButtonStyle.red)
    async def modify_guild(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(DataInput(ctx=self.ctx, collection=db.guild))
        self.value = True
        self.stop()

    @discord.ui.button(label='일반', style=discord.ButtonStyle.blurple)
    async def modify_general(self, interaction: discord.Interaction, button: discord.ui.Button):  # noqa
        await interaction.response.send_modal(DataInput(ctx=self.ctx, collection=db.general))
        self.value = True
        self.stop()


class InfoInput(DefaultModal, title="소개말 수정하기"):
    info_word = discord.ui.TextInput(
        label='소개말 내용 (최대 50자)', min_length=1, max_length=50, placeholder="소개말을 입력해 주세요.", required=True
    )

    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        self.info_word.value.replace('`', '')
        await write(self.ctx.author, 'info', self.info_word.value)
        await interaction.response.send_message(
            f"<:done:{config('emojis.done')}> 소개말을 '{e_mk(e_mt(self.info_word.value))}'(으)로 변경했습니다!", ephemeral=True
        )


class InfoEdit(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.ctx = ctx

    @discord.ui.button(label='소개말 수정하기', style=discord.ButtonStyle.blurple, emoji="<:edit:984405210870988870>")
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(InfoInput(ctx=self.ctx))
        button.disabled = True
        await self.message.edit(view=self)
        self.stop()


class RankDropdown(discord.ui.Select):
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.categories = {
            "general": {"포인트": 'points', "메달": 'medals', "출석": 'attendance_times', "명령어": 'command_used'},
            "game": {"솔로": 'rank_solo', "쿵쿵따": 'kkd'},  # TODO: 게임모드 완성시 교체: , "온라인": 'rank_online', "긴단어": 'long'},
            "main": ["포인트", "메달", "출석", "솔로", "쿵쿵따"]  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체
        }
        self.query = {
            'banned.isbanned': False,
            '_id': {
                '$nin': config('bot_whitelist'),
                '$ne': self.ctx.bot.owner_id
            }
        }
        options = [
            discord.SelectOption(
                label="종합 랭킹",
                value="종합 랭킹",
                description="여러 분야의 랭킹을 한번에 확인합니다.",
                emoji="<:ranking:985439871004995634>"
            )
        ]
        for category in self.categories["general"] | self.categories["game"]:
            option = discord.SelectOption(
                label=category if category in self.categories['general'] else f"끝말잇기 - {category}",
                value=category,
                description=f"{category + ' 분야' if category in self.categories['general'] else '끝말잇기 ' + category + ' 모드' }의 랭킹을 확인합니다.",
                emoji="<:ranking:985439871004995634>"
            )
            options.append(option)
        super().__init__(placeholder="분야를 선택해 주세요.", options=options, row=1)

    async def get_user_name(self, user_id: int) -> str:
        user = self.ctx.bot.get_user(user_id)
        if hasattr(user, 'name'):
            username = user.name
        else:
            if await read(user_id, 'name'):
                username = await read(user_id, 'name')
            else:
                username = (await self.ctx.bot.fetch_user(user_id)).name
        if len(username) >= 15:
            username = username[:12] + "..."
        return username

    async def format_rank(self, rank: AsyncIOMotorCursor, query: str) -> list:
        rank = await rank.to_list(None)
        names = await asyncio.gather(*[self.get_user_name(i['_id']) for i in rank])
        return [f"**{idx + 1}**. {e_mk(names[idx])} : `{get_nested_dict(i, query.split('.'))}`" for idx, i in enumerate(rank)]

    async def get_overall_rank(self):
        embed = discord.Embed(title="{ranking} 종합 랭킹 top 5", color=config('colors.help'))
        coros = []
        for path in self.categories["main"]:
            if path in self.categories["general"]:
                coros.append(
                    self.format_rank(self.ctx.bot.db.user.find(self.query).sort(self.categories['general'][path], -1).limit(5), self.categories['general'][path]),
                )
            else:
                game_query = self.query.copy()
                game_query[f"game.{self.categories['game'][path]}.times"] = {"$gte": 50}  # type: ignore
                for gpath in ("win", "best", "winrate"):
                    full_path = f"game.{self.categories['game'][path]}.{gpath}"
                    coros.append(
                        self.format_rank(self.ctx.bot.db.user.find(game_query).sort(full_path, -1).limit(5), full_path),
                    )
        overall_rank = await asyncio.gather(*coros)
        gpath = ["승리수", "최고점수", "승률"]
        for i, rank in enumerate(overall_rank):
            if i <= 2:
                embed.add_field(name=f"🔹 {self.categories['main'][i]}", value="\n".join(rank))
            elif 3 <= i <= 5:
                embed.add_field(name=f"🔹 솔로 모드 - {gpath[i % 3]}", value="\n".join(rank))
            else:
                embed.add_field(name=f"🔹 쿵쿵따 모드 - {gpath[i % 3]}", value="\n".join(rank))  # TODO: 온라인모드 완성시 '쿵쿵따'를 '온라인' 으로 교체

        return embed, coros

    async def callback(self, interaction: discord.Interaction):
        for item in self.options:
            item.default = False
            if item.value == self.values[0]:
                item.default = True
        category = self.values[0]
        if category == "종합 랭킹":
            embed, coros = await self.get_overall_rank()
        elif category in self.categories["general"]:
            rank = self.ctx.bot.db.user.find(self.query).sort(self.categories["general"][category], -1).limit(15)
            embed = discord.Embed(
                title=f"{{ranking}} 랭킹 top 15 | {self.values[0]}",
                description="\n".join(await self.format_rank(rank, self.categories["general"][category])),
                color=config('colors.help')
            )
        else:
            self.query[f"game.{self.categories['game'][category]}.times"] = {"$gte": 50}
            embed = discord.Embed(title=f"{{ranking}} 랭킹 top 15 | 끝말잇기 - {category} 모드", color=config('colors.help'))
            coros = []
            for path in ("win", "best", "winrate"):
                full_path = f"game.{self.categories['game'][category]}.{path}"
                coros.append(
                    self.format_rank(self.ctx.bot.db.user.find(self.query).sort(full_path, -1).limit(15), full_path),
                )
            rank = await asyncio.gather(*coros)
            embed.add_field(name="🔹 승리수", value="\n".join(rank[0]))
            embed.add_field(name="🔹 최고점수", value="\n".join(rank[1]))
            embed.add_field(name="🔹 승률", value="\n".join(rank[2]))

        await interaction.response.edit_message(embed=embed, view=self.view)


class RankMenu(DefaultView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx=ctx, author_only=True)
        self.dropdown = RankDropdown(ctx)
        self.add_item(self.dropdown)

    async def get_home_embed(self):
        embed, _ = await self.dropdown.get_overall_rank()
        return embed
