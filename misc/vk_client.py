import asyncio

from vk_api import VkApi, VkUpload
from vk_api.keyboard import VkKeyboard
from vk_api.utils import get_random_id
from vk_api.vk_api import VkApiMethod

from misc.config import Config
from models.vk import Message


class VkClient:
    def __init__(
            self,
            config: Config,
            session: VkApi,
            api: VkApiMethod,
            upload: VkUpload
    ):
        self.config: Config = config
        self.session: VkApi = session
        self.api: VkApiMethod = api
        self.upload: VkUpload = upload

    async def send_message(
            self,
            peer_id: int,
            message: Message,
            keyboard: VkKeyboard | str | dict | None = None
    ):
        if isinstance(keyboard, VkKeyboard):
            keyboard = keyboard.get_keyboard()

        await self.call(
            "messages.send",
            dict(
                message=message.text,
                attachment=message.attachment,
                random_id=get_random_id(),
                peer_id=peer_id,
                keyboard=keyboard
            ),
        )

    async def send_event_message(
            self,
            event_id: str,
            user_id: int,
            peer_id: int,
            event_data: str
    ):
        pass

    async def delete_message(
            self,
            peer_id: int,
            message_ids: list[int] = None,
            cmids: list[int] = None,
            delete_for_all: bool = True
    ):
        data = dict(
            peer_id=peer_id,
            delete_for_all=1 if delete_for_all else 0
        )
        if message_ids:
            data['message_ids'] = ','.join([str(i) for i in message_ids])
        if cmids:
            data['cmids'] = ','.join([str(i) for i in cmids])

        await self.call(
            "messages.delete",
            data
        )

    async def upload_photos_message(
            self,
            peer_id: int,
            photo_paths: list[str]
    ) -> list[str]:  # list 'attachment' str
        response = await asyncio.to_thread(
            self.upload.photo_messages,
            photo_paths,
            peer_id
        )
        return [
            f"photo{r['owner_id']}_{r['id']}_{r['access_key']}"
            for r in response
        ]

    async def upload_doc_message(
            self,
            peer_id: int,
            doc_path: str,
            **kwargs
    ):
        response = await asyncio.to_thread(
            self.upload.document_message,
            doc_path,
            peer_id=peer_id,
            **kwargs
        )
        doc = response['doc']
        return f"doc{doc['owner_id']}_{doc['id']}"

    async def call(
            self,
            method: str,
            values: dict | None = None,
            **kwargs
    ):
        return await asyncio.to_thread(
            self.session.method,
            method,
            values,
            **kwargs
        )

    @classmethod
    async def create(
            cls,
            config: Config
    ) -> "VkClient":
        session = VkApi(token=config.vk.vk_token)
        api = session.get_api()
        upload = VkUpload(session)
        return cls(config, session, api, upload)

    async def close(self):
        if self.session:
            await asyncio.to_thread(self.session.http.close)
            self.session = None

        if self.api:
            self.api = None

        if self.upload:
            await asyncio.to_thread(self.upload.http.close)
            self.upload = None
