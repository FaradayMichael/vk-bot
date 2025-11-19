from app.schemas.vk import Message
from app.services.vk_bot.models.vk import VkMessage
from app.services.vk_bot.service import VkBotService
from . import callbacks


async def on_help(service: VkBotService, message_model: VkMessage):
    await service.client_vk.messages.send(
        peer_id=message_model.peer_id,
        message=Message(
            text=f"{f'@id{message_model.from_id} ' if message_model.from_chat else ''} help"
        ),
        keyboard=callbacks.help_kb,
    )


COMMANDS_MAP = {"/help": on_help}
