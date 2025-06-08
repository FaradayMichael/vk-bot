from gigachat import (
    GigaChatAsyncClient
)
from gigachat.models import (
    Chat,
    Messages,
    MessagesRole
)

from app.db import gigachat as gigachat_db
from app.utils.config import GigachatConfig
from app.utils.db import DBHelper

user_alias = str | int


class GigachatClient:
    def __init__(
            self,
            config: GigachatConfig,
            db_helper: DBHelper,
            role: MessagesRole = MessagesRole.SYSTEM,
            init_payload_message: str = "Ты внимательный бот, который помогает пользователю решить его проблемы.",
            temperature: float = 0.7,
            max_tokens: int = 500,
    ):
        self.config = config
        self.db_helper = db_helper
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
        async with self.db_helper.get_session() as session:
            messages_db = await gigachat_db.get_by_user(session, user)
            if not messages_db:
                messages_db = [
                    await gigachat_db.create(
                        session, user, Messages(role=self._role, content=self._init_payload_message)
                    )
                ]
        return Chat(
            messages=messages_db,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

    async def chat(self, user: user_alias, message_text: str) -> Messages:
        user = str(user)
        async with self.db_helper.get_session() as session:
            await gigachat_db.create(session, user, Messages(role=MessagesRole.USER, content=message_text))
            payload = await self._get_payload(user)

            response = await self._giga.achat(payload)
            message = response.choices[0].message
            await gigachat_db.create(session, user, message)
        return message

    async def prune_chat_history(self, user: user_alias):
        user = str(user)
        async with self.db_helper.get_session() as session:
            await gigachat_db.delete_by_user(session, user)

    async def close(self):
        if self._giga:
            await self._giga.aclose()
            self._giga = None
