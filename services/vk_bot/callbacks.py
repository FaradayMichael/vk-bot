import logging

from vk_api.bot_longpoll import VkBotMessageEvent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from misc import redis
from models.vk import Message
from services.vk_bot.service import VkBotService

logger = logging.getLogger(__name__)

help_kb = VkKeyboard(
    one_time=False,
    inline=True
)
help_kb.add_callback_button(
    label='Кнопка',
    color=VkKeyboardColor.SECONDARY,
    payload={"type": "help_callback", "text": "."}
)

null_kb = VkKeyboard(
    one_time=True,
    inline=False
)


async def help_callback(service: VkBotService, event: VkBotMessageEvent):
    peer_id = event.object['peer_id']
    user_id = event.object['user_id']
    mes_id = event.object['conversation_message_id']

    await service.client.messages.delete(
        peer_id,
        cmids=[mes_id]
    )

    key = "help_callback-attachment"
    attachment = await redis.get(service.redis_conn, key)
    logger.info(f'from redis: {attachment=}')
    if not attachment:
        attachment = await service.client.upload.doc_message(peer_id=peer_id, doc_path='static/test2.gif')
        await redis.set(service.redis_conn, key, {'value': attachment})
    else:
        attachment = attachment['value']

    await service.client.messages.send(
        peer_id,
        message=Message(
            text=f"@id{user_id}",
            attachment=attachment
        ),
        keyboard=help_kb.get_empty_keyboard()
    )
