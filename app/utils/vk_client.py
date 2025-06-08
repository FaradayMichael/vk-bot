import asyncio
import datetime
import json
import logging
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

from app.utils.config import VkConfig
from app.schemas.vk import (
    Message,
    WallPost
)
from app.services.vk_bot.models.vk import (
    WallItemFilter,
    WallItem,
    Poll
)

logger = logging.getLogger(__name__)


def with_retries(f):
    async def wrapper(*args, **kwargs):
        max_tries = 3
        for _ in range(max_tries - 1):
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                logger.error(e)
                await asyncio.sleep(5)
        return await f(*args, **kwargs)

    return wrapper


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

    @with_retries
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

    @with_retries
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
            keyboard: VkKeyboard | str | dict | None = None,
            reply_to: int | None = None,
    ):
        if isinstance(keyboard, VkKeyboard):
            keyboard = keyboard.get_keyboard()

        return await self._call_group(
            "messages.send",
            dict(
                message=message.text,
                attachment=message.attachment,
                random_id=get_random_id(),
                peer_id=peer_id,
                keyboard=keyboard,
                reply_to=reply_to,
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
    ) -> int:
        owner_id = owner_id if owner_id is not None else -self._config.main_group_id
        result = await self._call_user(
            'wall.post',
            dict(
                owner_id=owner_id,
                message=post.message_text,
                attachments=post.attachments,
                from_group=1 if from_group else 0,
                publish_date=int(post_time.timestamp()) if post_time else None
            )
        )
        return result['post_id']

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

    async def get_by_id(
            self,
            id_: int,
            owner_id: int | None = None,
    ) -> WallItem | None:
        owner_id = owner_id if owner_id is not None else -self._config.main_group_id
        response = await self._call_user(
            'wall.getById',
            dict(
                posts=f"{owner_id}_{id_}"
            )
        )
        if response:
            return WallItem.model_validate(response[0])

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
                publish_date=int(post_time.timestamp()) if post_time else None
            )
        )


class Upload(BaseMethod):

    @with_retries
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

    @with_retries
    async def doc_message(
            self,
            peer_id: int,
            doc_path: str,
            **kwargs
    ) -> str:
        response = await asyncio.to_thread(
            self._upload_group.document_message,
            doc_path,
            peer_id=peer_id,
            **kwargs
        )
        doc = response['doc']
        return f"doc{doc['owner_id']}_{doc['id']}"

    @with_retries
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

    @with_retries
    async def video_wall_and_post(
            self,
            path: str | None = None,
            name: str | None = None,
            link: str | None = None
    ) -> Mapping:
        if not path and not link:
            raise ValueError("Either path or link is required")

        args = dict(
            video_file=path,
            link=link,
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


class Polls(BaseMethod):

    async def create(
            self,
            question: str,
            add_answers: list[str],
            is_anonymous: bool = False,
            is_multiple: bool = False,
    ) -> Poll:
        result = await self._call_user(
            method="polls.create",
            values=dict(
                add_answers=json.dumps(add_answers),
                question=question,
                is_anonymous=int(is_anonymous),
                is_multiple=int(is_multiple),
                owner_id=-self._config.main_group_id,
            )
        )
        return Poll.model_validate(result)

    async def get_by_id(
            self,
            id_: int,
            owner_id: int | None = None,
    ) -> Poll | None:
        owner_id = owner_id if owner_id is not None else -self._config.main_group_id
        response = await self._call_user(
            method="polls.getById",
            values=dict(
                owner_id=owner_id,
                poll_id=id_,
                extended=0
            )
        )
        if response:
            print(response)
            return Poll.model_validate(response)


    async def edit(
            self,
            id_: int,
            owner_id: int | None = None,
            question: str | None = None,
    ):
        owner_id = owner_id if owner_id is not None else -self._config.main_group_id
        response = await self._call_user(
            method="polls.edit",
            values=dict(
                owner_id=owner_id,
                poll_id=id_,
                question=question,
            )
        )
        if response:
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
        self.polls = Polls(config, self._session_group, self._session_user, self._upload_group, self._upload_user)

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
