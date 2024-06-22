from gigachat import GigaChatAsyncClient
from gigachat.models import Chat, Messages, MessagesRole

from misc.config import GigachatConfig

user_alias = str | int


class GigachatClient:
    def __init__(
            self,
            config: GigachatConfig,
            role: MessagesRole = MessagesRole.SYSTEM,
            init_payload_message: str = "Ты внимательный бот-психолог, который помогает пользователю решить его проблемы.",
            temperature: float = 0.7,
            max_tokens: int = 100,
    ):
        self.config = config
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

    def _init_payload(self, user: user_alias) -> Chat:
        payload = Chat(
            messages=[
                Messages(role=self._role, content=self._init_payload_message),
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        self._payloads[user] = payload
        return payload

    async def chat(self, user: user_alias, message_text: str) -> Messages:
        payload = self._payloads.get(user, None)
        if not payload:
            payload = self._init_payload(user)

        payload.messages.append(
            Messages(role=MessagesRole.USER, content=message_text)
        )
        response = await self._giga.achat(payload)
        payload.messages.append(response.choices[0].message)
        return response.choices[0].message

    def prune_chat_history(self, user: user_alias):
        self._init_payload(user)

    async def close(self):
        if self._giga:
            await self._giga.aclose()
            self._giga = None
