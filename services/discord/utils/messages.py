import logging

from discord import Message

logger = logging.getLogger(__name__)


def log_message(message: Message):
    logger.info(f"{message.author=}")
    logger.info(f"{message.content=}")
    logger.info(f"{message.attachments=}")
    logger.info(f"{message.stickers=}")
