import asyncio
import datetime
from typing import AsyncIterable, Mapping

from vk_api import (
    VkApi,
    VkUpload,
    VkApiError
)
from vk_api.bot_longpoll import (
    VkBotLongPoll,
    VkBotEvent
)
from vk_api.keyboard import VkKeyboard
from vk_api.utils import get_random_id

from misc.config import VkConfig
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
            config: VkConfig,
            session_group: VkApi,
            session_user: VkApi,
            upload_group: VkUpload,
            upload_user: VkUpload
    ):
        self._config: VkConfig = config
        self._session_group: VkApi = session_group
        self._session_user = session_user
        self._upload_group: VkUpload = upload_group
        self._upload_user: VkUpload = upload_user

    async def _call_group(
            self,
            method: str,
            values: dict | None = None,
            **kwargs
    ):
        return await asyncio.to_thread(
            self._session_group.method,
            method,
            values,
            **kwargs
        )

    async def _call_user(
            self,
            method: str,
            values: dict | None = None,
            **kwargs
    ):
        return await asyncio.to_thread(
            self._session_user.method,
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

        await self._call_group(
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

        await self._call_group(
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
        owner_id = owner_id if owner_id is not None else -self._config.main_group_id
        await self._call_user(
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
        response = await self._call_user(
            'wall.get',
            dict(
                owner_id=-self._config.main_group_id,
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
        await self._call_user(
            'wall.edit',
            dict(
                owner_id=-self._config.main_group_id,
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
            self._upload_group.photo_messages,
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
            self._upload_group.document_message,
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
            self._upload_user.photo_wall,
            photo_paths,
            self._config.main_user_id,
            self._config.main_group_id,
            None
        )
        return [
            f"photo{r['owner_id']}_{r['id']}_{r['access_key']}"
            for r in response
        ]

    async def video_wall_and_post(
            self,
            path: str,
            name: str | None = None
    ) -> Mapping:
        args = dict(
            video_file=path,
            link=None,
            name=name,
            description=None,
            is_private=0,
            wallpost=True,
            group_id=self._config.main_group_id,
            album_id=None,
            privacy_view=None,
            privacy_comment=None,
            no_comments=None,
            repeat=None
        )
        response = await asyncio.to_thread(
            self._upload_user.video,
            **args
        )
        return response


class VkClient:
    def __init__(
            self,
            config: VkConfig
    ):
        self._config: VkConfig = config
        self._stopping = False
        self.user_id = config.main_user_id
        self.group_id = config.main_group_id

        self._session_group: VkApi = VkApi(token=config.vk_token)
        self._session_user = VkApi(token=config.user_token)
        self._upload_group: VkUpload = VkUpload(self._session_group)
        self._upload_user: VkUpload = VkUpload(self._session_user)
        self._bot_long_pool: VkBotLongPoll = VkBotLongPoll(self._session_group, self.group_id)

        self.messages = Messages(config, self._session_group, self._session_user, self._upload_group, self._upload_user)
        self.wall = Wall(config, self._session_group, self._session_user, self._upload_group, self._upload_user)
        self.upload = Upload(config, self._session_group, self._session_user, self._upload_group, self._upload_user)

    async def events_generator(self) -> AsyncIterable[VkBotEvent]:
        while not self._stopping:
            try:
                for event in await asyncio.to_thread(self._bot_long_pool.check):
                    yield event
            except VkApiError:
                raise
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break

    async def close(self):
        self._stopping = True

        if self._bot_long_pool:
            self._bot_long_pool.session.close()
            self._bot_long_pool = None

        if self._session_group:
            self._session_group.http.close()
            self._session_group = None

        if self._session_user:
            self._session_user.http.close()
            self._session_user = None

        if self._upload_group:
            self._upload_group.http.close()
            self._upload_group = None

        if self._upload_user:
            self._upload_user.http.close()
            self._upload_user = None

        if self.messages:
            self.messages = None
        if self.wall:
            self.wall = None
        if self.upload:
            self.upload = None
