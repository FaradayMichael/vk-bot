import asyncpg
from gigachat import GigaChatAsyncClient
from gigachat.models import Chat, Messages, MessagesRole

from db import (
    gigachat as gigachat_db,
)
from misc.config import GigachatConfig

user_alias = str | int


class GigachatClient:
    def __init__(
            self,
            config: GigachatConfig,
            db_pool: asyncpg.Pool,
            role: MessagesRole = MessagesRole.SYSTEM,
            init_payload_message: str = "Ты внимательный бот-психолог, который помогает пользователю решить его проблемы.",
            temperature: float = 0.7,
            max_tokens: int = 100,
    ):
        self.config = config
        self.db_pool = db_pool
        self._giga = GigaChatAsyncClient(
            credentials=config.token,
            verify_ssl_certs=False,
            scope=config.scope,
        )
        self._payloads: dict[user_alias, Chat] = {}

        self._role = role
        self._init_payload_message = init_payload_message
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def _get_payload(self, user: user_alias) -> Chat:
        user = str(user)
        messages_db = await gigachat_db.get_by_user(self.db_pool, user)
        if not messages_db:
            messages_db = [
                await gigachat_db.create(
                    self.db_pool, user, Messages(role=self._role, content=self._init_payload_message)
                )
            ]
        return Chat(
            messages=messages_db,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

    async def chat(self, user: user_alias, message_text: str) -> Messages:
        user = str(user)
        await gigachat_db.create(self.db_pool, user, Messages(role=MessagesRole.USER, content=message_text))
        payload = await self._get_payload(user)

        response = await self._giga.achat(payload)
        message = response.choices[0].message
        await gigachat_db.create(self.db_pool, user, message)
        return message

    async def prune_chat_history(self, user: user_alias):
        await gigachat_db.delete_by_user(self.db_pool, user)

    async def close(self):
        if self._giga:
            await self._giga.aclose()
            self._giga = None
