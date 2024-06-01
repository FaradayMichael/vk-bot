from discord import Message

from services.discord.events import logger


def log_message(message: Message):
    logger.info(f"{message.author=}")
    logger.info(f"{message.content=}")
    logger.info(f"{message.attachments=}")
    logger.info(f"{message.stickers=}")
