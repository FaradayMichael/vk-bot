import datetime
import logging

import aiofiles
from discord import (
    Message,
    ActivityType,
)
from discord.activity import ActivityTypes, CustomActivity, Spotify
from discord.member import Member, VoiceState

from app.db import (
    dynamic_config as dynamic_config_db,
    activity_sessions as activity_sessions_db,
    status_sessions as status_sessions_db,
)
from app.schemas.images import ImageTags
from .utils.attachments import (
    get_image_attachment_urls_from_message,
)
from .utils.messages import (
    log_message,
)
from .utils.voice_channels import (
    leave_from_empty_voice_channel,
)
from .models.activities import (
    ActivitiesState,
    BaseActivities,
    ActivitySessionCreate,
    StatusSessionCreate,
)
from .service import DiscordService

logger = logging.getLogger(__name__)


# https://discordpy.readthedocs.io/en/stable/api.html?highlight=event#event-reference


async def on_message(service: DiscordService, message: Message):
    log_message(message)

    if message.author.bot:
        return None

    async with service.db_helper.get_session() as session:
        d_config = await dynamic_config_db.get(session)
        d_config_changed: bool = False

        reactions_map = d_config.get("reactions_map", {})
        reaction: str | None = reactions_map.get(str(message.author.id), None)
        if reaction is not None:
            await message.add_reaction(reaction)

        if message.mentions and message.mentions[0].id == service.bot.user.id:
            response_message = await service.utils_client.gpt_chat(
                message.author.id,
                message.content,
            )
            if response_message:
                return await message.reply(response_message.message)

        await service.bot.process_commands(message)

        image_urls = get_image_attachment_urls_from_message(message)
        # video_urls = _get_video_attachment_urls_from_message(message)
        # yt_urls = _get_yt_urls_from_message(message)

        if image_urls:
            result_tags: list[ImageTags] = []
            for image_url in image_urls:
                tags = await service.utils_client.get_image_tags(image_url)
                if tags and (tags.tags or tags.description):
                    result_tags.append(tags)
            logger.info(f"{result_tags=}")
            if result_tags:
                await message.reply(
                    content="\n\n".join(
                        [
                            f"{i + 1}. {m.text(limit=1500)}"
                            for i, m in enumerate(result_tags)
                        ]
                    )
                )

        if d_config_changed:
            await dynamic_config_db.update(session, d_config)


async def on_ready_event(*args, **kwargs):
    logger.info(f"{args=} {kwargs=}")


async def on_ready(service: DiscordService):
    bot = service.bot

    try:
        avatar_path = "static/avatar.jpg"
        async with aiofiles.open(avatar_path, "rb") as f:
            await bot.user.edit(
                avatar=await f.read(),
            )
        logger.info(f"Loaded avatar {avatar_path}")
    except FileNotFoundError as e:
        logger.error(e)

    async with service.db_helper.get_session() as session:
        d_config = await dynamic_config_db.get(session)
        bot_activity_name = d_config.get("bot_activity_name")
        if bot_activity_name:
            await bot.change_presence(activity=CustomActivity(name=bot_activity_name))


async def on_presence_update(service: DiscordService, before: Member, after: Member):
    await _handel_activities_update(service, before, after)
    await _handle_status_update(service, before, after)


async def on_voice_state_update(
    service: DiscordService, member: Member, before: VoiceState, after: VoiceState
):
    async def on_leave_channel():
        channel = before.channel
        logger.info(f"Member {member.name} has left the voice channel {channel.name}")

    async def on_join_channel():
        channel = after.channel
        logger.info(f"Member {member.name} joined voice channel {channel.name}")

    async def on_move():
        from_channel = before.channel
        to_channel = after.channel
        logger.info(
            f"Member {member.name} moved from {from_channel.name} to {to_channel.name}"
        )

    async def on_start_stream():
        channel = after.channel
        logger.info(f"Member {member.name} started streaming in {channel.name}")

    bot = service.bot
    await leave_from_empty_voice_channel(bot)
    if before.channel and after.channel:
        if before.channel.id == after.channel.id:
            if not before.self_stream and after.self_stream:
                await on_start_stream()
            return None
        await on_move()
    else:
        if before.channel:
            await on_leave_channel()
        if after.channel:
            await on_join_channel()
    return None


async def _handel_activities_update(
    service: DiscordService, before: Member, after: Member
):
    async with service.db_helper.get_session() as session:

        async def handle_activities_on_db(activities: BaseActivities):
            if activities.started:
                for a in activities.started:
                    if a in exclude_activities:
                        continue
                    await activity_sessions_db.create(
                        session,
                        ActivitySessionCreate(
                            user_id=activities.user_id,
                            user_name=activities.user_name,
                            activity_name=a,
                        ),
                    )

            if activities.finished:
                for a in activities.finished:
                    activity_db = await activity_sessions_db.get_first_unfinished(
                        session, activities.user_id, a
                    )
                    if activity_db:
                        await activity_sessions_db.update(
                            session,
                            activity_db.id,
                            finished_at=datetime.datetime.utcnow(),
                        )

        dynamic_config = await dynamic_config_db.get(session)
        exclude_activities = dynamic_config.get("exclude_activities", [])

        state = _get_activities_state(before, after)
        if state.watching.has_changes:
            _log_activities(state.watching, "watching")
        if state.streaming.has_changes:
            _log_activities(state.streaming, "streaming")
        if state.playing.has_changes:
            _log_activities(state.playing)
            await handle_activities_on_db(state.playing)
        if state.listening.has_changes:
            _log_activities(state.listening)


async def _handle_status_update(service: DiscordService, before: Member, after: Member):
    if before.status == after.status:
        return None

    async with service.db_helper.get_session() as session:

        before_status = str(before.status)
        after_status = str(after.status)

        logger.info(
            f"{before.name} change status from {before_status} to {after_status}"
        )

        session_db = await status_sessions_db.get_first_unfinished(
            session, after.id, before_status
        )
        if session_db:
            await status_sessions_db.update(
                session, session_db.id, finished_at=datetime.datetime.utcnow()
            )
        await status_sessions_db.create(
            session,
            StatusSessionCreate(
                user_id=after.id, user_name=after.name, status=after_status
            ),
        )


def _get_activities_state(before: Member, after: Member) -> ActivitiesState:
    def get_core_attr(activity: ActivityTypes) -> str:
        if activity.type == ActivityType.listening:
            activity: Spotify
            return f"{activity.artist} - {activity.title}"
        if activity.type not in (
            ActivityType.playing,
            ActivityType.custom,
        ):
            logger.info(f"Unknown activity: {repr(activity)}")
        return activity.name

    user_id = before.id
    user_name = before.name

    state_dict = {}
    for a_type in ActivityType:
        a_type_name = a_type.name.lower()

        before_activities = set(
            [get_core_attr(act) for act in before.activities if act.type is a_type]
        )
        after_activities = set(
            [get_core_attr(act) for act in after.activities if act.type is a_type]
        )
        started_activities = after_activities.difference(before_activities)
        finished_activities = before_activities.difference(after_activities)
        unmodified_activities = before_activities.intersection(after_activities)

        state_dict[a_type_name] = {
            "user_id": user_id,
            "user_name": user_name,
            "before": before_activities,
            "after": after_activities,
            "started": started_activities,
            "finished": finished_activities,
            "unmodified": unmodified_activities,
        }
    return ActivitiesState.model_validate(state_dict)


def _log_activities(
    activity_model: BaseActivities, rel_name: str | None = None
) -> None:
    activity = rel_name or activity_model.rel_name
    if activity_model.started:
        logger.info(
            f"{activity_model.user_name} start {activity=} {activity_model.started}"
        )
    if activity_model.finished:
        logger.info(
            f"{activity_model.user_name} finish {activity=} {activity_model.finished}"
        )
