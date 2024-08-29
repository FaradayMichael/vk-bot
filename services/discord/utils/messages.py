import logging
from typing import Iterable

from discord import (
    Message,
    Embed,
    Color
)
from ..consts import (
    POSITIVE_VOTE_REACTION,
    NEGATIVE_VOTE_REACTION
)

logger = logging.getLogger(__name__)


async def create_binary_voting(
        target_message: Message,
        title: str = 'Голосование!',
        description: str = '?Mem?',
) -> Message:
    """
    :param target_message:
    :param title:
    :param description:
    :return: vote message
    """
    return await create_voting(
        target_message=target_message,
        reactions_set=(POSITIVE_VOTE_REACTION, NEGATIVE_VOTE_REACTION,),
        title=title,
        description=description
    )


async def create_voting(
        target_message: Message,
        reactions_set: Iterable[str],
        title: str = 'Голосование!',
        description: str = '?Mem?',
) -> Message:
    """
    :param target_message:
    :param reactions_set:
    :param title:
    :param description:
    :return: vote message
    """
    emb = Embed(title=title, description=description, colour=Color.purple())
    vote_message = await target_message.reply(embed=emb)
    for reaction in reactions_set:
        await vote_message.add_reaction(reaction)

    return vote_message


def log_message(message: Message):
    logger.info(f"{message.author=}")
    logger.info(f"{message.content=}")
    logger.info(f"{message.attachments=}")
    logger.info(f"{message.stickers=}")
