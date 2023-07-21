from typing import Any, Optional, Sequence, Union, Callable, TYPE_CHECKING, TypeVar, Coroutine
import inspect

import discord
from discord.ext import commands
from discord.enums import ButtonStyle
from discord.ui import Button

from .utils import dict_emojis

if TYPE_CHECKING:
    from core import Kkutbot


class FormattingDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class KkutbotContext(commands.Context):
    def __init__(self, bot: "Kkutbot", **kwargs: Any) -> None:
        super().__init__(bot=bot, **kwargs)
        self.bot: "Kkutbot" = bot

    async def send(
            self,
            content: Optional[str] = None,
            *,
            tts: bool = False,
            embed: Optional[discord.Embed] = None,
            embeds: Optional[Sequence[discord.Embed]] = None,
            file: Optional[discord.File] = None,
            files: Optional[Sequence[discord.File]] = None,
            stickers: Optional[Sequence[Union[discord.GuildSticker, discord.StickerItem]]] = None,
            delete_after: Optional[float] = None,
            nonce: Optional[Union[str, int]] = None,
            allowed_mentions: Optional[discord.AllowedMentions] = None,
            reference: Optional[Union[discord.Message, discord.MessageReference, discord.PartialMessage]] = None,
            mention_author: Optional[bool] = None,
            view: Optional[discord.ui.View] = None,
            suppress_embeds: bool = False,
            ephemeral: bool = False,
            silent: bool = False,
            escape_emoji_formatting: bool = False
    ) -> discord.Message:
        if (escape_emoji_formatting is False) and (self.command.qualified_name.split(" ")[0] != "jishaku"):
            content = content.format_map(FormattingDict(dict_emojis())) if content else None
        return await super().send(content=content,  # noqa
                                  tts=tts,
                                  embed=embed,
                                  file=file,
                                  files=files,
                                  nonce=nonce,
                                  delete_after=delete_after,
                                  allowed_mentions=allowed_mentions,
                                  reference=reference,
                                  mention_author=mention_author,
                                  view=view,
                                  embeds=embeds,
                                  stickers=stickers,
                                  suppress_embeds=suppress_embeds,
                                  ephemeral=ephemeral,
                                  silent=silent
                                  )

    async def reply(self, content: Optional[str] = None, mention_author: bool = False, **kwargs: Any) -> discord.Message:
        if (not kwargs.get("escape_emoji_formatting", False)) and (self.command.qualified_name.split(" ")[0] != "jishaku"):
            content = content.format_map(FormattingDict(dict_emojis())) if content else None
        if self.interaction is None:
            return await self.send(
                content, reference=self.message, mention_author=mention_author, **kwargs
            )
        else:
            return await self.send(content, mention_author=mention_author, **kwargs)


class KkutbotEmbed(discord.Embed):
    def __init__(self, **kwargs: Any) -> None:
        if not kwargs.get("escape_emoji_formatting", False):
            if title := kwargs.get("title"):
                kwargs["title"] = title.format_map(FormattingDict(dict_emojis()))
            if description := kwargs.get("description"):
                kwargs["description"] = description.format_map(FormattingDict(dict_emojis()))
        super().__init__(**kwargs)

    def add_field(self, *, name: str, value: str, inline: bool = True, escape_emoji_formatting: bool = False) -> discord.Embed:
        if escape_emoji_formatting is False:
            name = name.format_map(FormattingDict(dict_emojis()))
            value = value.format_map(FormattingDict(dict_emojis()))
        return super().add_field(name=name, value=value, inline=inline)


discord.Embed = KkutbotEmbed


class KkutbotInteractionResponse(discord.InteractionResponse):
    async def send_message(
            self,
            content: Optional[Any] = None,
            *,
            embed: discord.Embed = discord.utils.MISSING,
            embeds: Sequence[discord.Embed] = discord.utils.MISSING,
            file: discord.File = discord.utils.MISSING,
            files: Sequence[discord.File] = discord.utils.MISSING,
            view: discord.ui.View = discord.utils.MISSING,
            tts: bool = False,
            ephemeral: bool = False,
            allowed_mentions: discord.AllowedMentions = discord.utils.MISSING,
            suppress_embeds: bool = False,
            silent: bool = False,
            delete_after: Optional[float] = None
    ) -> None:
        content = content.format_map(FormattingDict(dict_emojis())) if content else None
        await super().send_message(
            content,
            embed=embed,
            embeds=embeds,
            file=file,
            files=files,
            view=view,
            tts=tts,
            ephemeral=ephemeral,
            allowed_mentions=allowed_mentions,
            suppress_embeds=suppress_embeds,
            silent=silent,
            delete_after=delete_after
        )


discord.interactions.InteractionResponse = KkutbotInteractionResponse


class KkutbotSelectOption(discord.SelectOption):
    def __init__(
            self,
            *,
            label: str,
            value: str = discord.utils.MISSING,
            description: Optional[str] = None,
            emoji: Optional[Union[str, discord.Emoji, discord.PartialEmoji]] = None,
            default: bool = False,
    ) -> None:
        emoji = emoji.format_map(FormattingDict(dict_emojis())) if emoji else None
        super().__init__(label=label, value=value, description=description, emoji=emoji, default=default)


discord.SelectOption = KkutbotSelectOption

V = TypeVar("V", bound="View", covariant=True)
I = TypeVar("I", bound="Item[Any]")  # noqa
ItemCallbackType = Callable[[V, discord.Interaction[Any], I], Coroutine[Any, Any, Any]]


def button(
        *,
        label: Optional[str] = None,
        custom_id: Optional[str] = None,
        disabled: bool = False,
        style: ButtonStyle = ButtonStyle.secondary,
        emoji: Optional[Union[str, discord.Emoji, discord.PartialEmoji]] = None,
        row: Optional[int] = None,
) -> Callable[[ItemCallbackType[V, Button[V]]], Button[V]]:
    """A decorator that attaches a button to a component.

    The function being decorated should have three parameters, ``self`` representing
    the :class:`discord.ui.View`, the :class:`discord.Interaction` you receive and
    the :class:`discord.ui.Button` being pressed.

    .. note::

        Buttons with a URL cannot be created with this function.
        Consider creating a :class:`Button` manually instead.
        This is because buttons with a URL do not have a callback
        associated with them since Discord does not do any processing
        with it.

    Parameters
    ------------
    label: Optional[:class:`str`]
        The label of the button, if any.
    custom_id: Optional[:class:`str`]
        The ID of the button that gets received during an interaction.
        It is recommended not to set this parameter to prevent conflicts.
    style: :class:`.ButtonStyle`
        The style of the button. Defaults to :attr:`.ButtonStyle.grey`.
    disabled: :class:`bool`
        Whether the button is disabled or not. Defaults to ``False``.
    emoji: Optional[Union[:class:`str`, :class:`.Emoji`, :class:`.PartialEmoji`]]
        The emoji of the button. This can be in string form or a :class:`.PartialEmoji`
        or a full :class:`.Emoji`.
    row: Optional[:class:`int`]
        The relative row this button belongs to. A Discord component can only have 5
        rows. By default, items are arranged automatically into those 5 rows. If you'd
        like to control the relative positioning of the row then passing an index is advised.
        For example, row=1 will show up before row=2. Defaults to ``None``, which is automatic
        ordering. The row number must be between 0 and 4 (i.e. zero indexed).
    """

    def decorator(func: ItemCallbackType[V, Button[V]]) -> ItemCallbackType[V, Button[V]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError('button function must be a coroutine function')

        func.__discord_ui_model_type__ = Button
        func.__discord_ui_model_kwargs__ = {
            'style': style,
            'custom_id': custom_id,
            'url': None,
            'disabled': disabled,
            'label': label,
            'emoji': emoji.format_map(FormattingDict(dict_emojis())) if emoji else emoji,
            'row': row,
        }
        return func

    return decorator  # type: ignore


discord.ui.button = button
