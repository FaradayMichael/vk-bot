import asyncio
import datetime

from vk_api import VkApi, VkUpload
from vk_api.keyboard import VkKeyboard
from vk_api.utils import get_random_id

from misc.config import Config
from models.vk import (
    Message,
    WallPost
)
from services.vk_bot.models import (
    WallItem,
    WallItemFilter
)


class BaseMethod:
    def __init__(
            self,
            config: Config,
            session_group: VkApi,
            session_user: VkApi,
            upload_group: VkUpload,
            upload_user: VkUpload
    ):
        self.config: Config = config
        self.session_group: VkApi = session_group
        self.session_user = session_user
        self.upload_group: VkUpload = upload_group
        self.upload_user: VkUpload = upload_user

    async def call_group(
            self,
            method: str,
            values: dict | None = None,
            **kwargs
    ):
        return await asyncio.to_thread(
            self.session_group.method,
            method,
            values,
            **kwargs
        )

    async def call_user(
            self,
            method: str,
            values: dict | None = None,
            **kwargs
    ):
        return await asyncio.to_thread(
            self.session_user.method,
            method,
            values,
            **kwargs
        )


class Messages(BaseMethod):

    async def send(
            self,
            peer_id: int,
            message: Message,
            keyboard: VkKeyboard | str | dict | None = None
    ):
        if isinstance(keyboard, VkKeyboard):
            keyboard = keyboard.get_keyboard()

        await self.call_group(
            "messages.send",
            dict(
                message=message.text,
                attachment=message.attachment,
                random_id=get_random_id(),
                peer_id=peer_id,
                keyboard=keyboard
            ),
        )

    async def send_event(
            self,
            event_id: str,
            user_id: int,
            peer_id: int,
            event_data: str
    ):
        pass

    async def delete(
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

        await self.call_group(
            "messages.delete",
            data
        )


class Wall(BaseMethod):

    async def post(
            self,
            post: WallPost,
            owner_id: int | None = None,
            from_group: bool = True,
            post_time: datetime.datetime | None = None
    ):
        owner_id = owner_id if owner_id is not None else -self.config.vk.main_group_id
        await self.call_user(
            'wall.post',
            dict(
                owner_id=owner_id,
                message=post.message_text,
                attachments=post.attachments,
                from_group=1 if from_group else 0,
                publish_date=post_time.timestamp() if post_time else None
            )
        )

    async def get(
            self,
            type_filter: WallItemFilter | None = None
    ) -> list[WallItem]:
        response = await self.call_user(
            'wall.get',
            dict(
                owner_id=-self.config.vk.main_group_id,
                filter=type_filter.value if type_filter else None
            )
        )
        return [WallItem.model_validate(i) for i in response['items']]

    async def edit(
            self,
            post_id: int,
            post: WallPost,
            post_time: datetime.datetime | None = None
    ):
        await self.call_user(
            'wall.edit',
            dict(
                owner_id=-self.config.vk.main_group_id,
                post_id=post_id,
                message=post.message_text,
                attachments=post.attachments,
                publish_date=post_time.timestamp() if post_time else None
            )
        )


class Upload(BaseMethod):

    async def photos_message(
            self,
            peer_id: int,
            photo_paths: list[str]
    ) -> list[str]:  # list 'attachment' str
        response = await asyncio.to_thread(
            self.upload_group.photo_messages,
            photo_paths,
            peer_id
        )
        return [
            f"photo{r['owner_id']}_{r['id']}_{r['access_key']}"
            for r in response
        ]

    async def doc_message(
            self,
            peer_id: int,
            doc_path: str,
            **kwargs
    ):
        response = await asyncio.to_thread(
            self.upload_group.document_message,
            doc_path,
            peer_id=peer_id,
            **kwargs
        )
        doc = response['doc']
        return f"doc{doc['owner_id']}_{doc['id']}"

    async def photo_wall(
            self,
            photo_paths: list[str]
    ) -> list[str]:  # list 'attachment' str
        response = await asyncio.to_thread(
            self.upload_user.photo_wall,
            photo_paths,
            self.config.vk.main_user_id,
            self.config.vk.main_group_id,
            None
        )
        return [
            f"photo{r['owner_id']}_{r['id']}_{r['access_key']}"
            for r in response
        ]


class VkClient:
    def __init__(
            self,
            config: Config
    ):
        self.config: Config = config
        self.session_group: VkApi = VkApi(token=config.vk.vk_token)
        self.session_user = VkApi(token=config.vk.user_token)
        self.upload_group: VkUpload = VkUpload(self.session_group)
        self.upload_user: VkUpload = VkUpload(self.session_user)

        self.messages = Messages(config, self.session_group, self.session_user, self.upload_group, self.upload_user)
        self.wall = Wall(config, self.session_group, self.session_user, self.upload_group, self.upload_user)
        self.upload = Upload(config, self.session_group, self.session_user, self.upload_group, self.upload_user)

    async def close(self):
        if self.session_group:
            await asyncio.to_thread(self.session_group.http.close)
            self.session_group = None

        if self.session_user:
            await asyncio.to_thread(self.session_user.http.close)
            self.session_user = None

        if self.upload_group:
            await asyncio.to_thread(self.upload_group.http.close)
            self.upload_group = None

        if self.upload_user:
            await asyncio.to_thread(self.upload_user.http.close)
            self.upload_user = None

        if self.messages:
            self.messages = None
        if self.wall:
            self.wall = None
        if self.upload:
            self.upload = None
