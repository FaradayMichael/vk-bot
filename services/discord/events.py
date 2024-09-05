import datetime
import logging
from typing import Sequence

from discord import (
    Message,
    VoiceClient,
    ActivityType,
    Reaction,
)
from discord.member import (
    Member,
    VoiceState
)

from db import (
    dynamic_config as dynamic_config_db,
    activity_sessions as activity_sessions_db
)
from models.base import AttachmentType
from models.images import ImageTags
from .consts import (
    DISCORD_MEDIA_PREFIX,
    DISCORD_ATTACHMENT_PREFIX,
    IMG_EXT,
    VIDEO_EXT,
    BINARY_VOTE_REACTIONS
)
from .utils.messages import (
    log_message,
    create_binary_voting
)
from .utils.voice_channels import (
    leave_from_empty_voice_channel,
    connect_to_voice_channel,
    play_file
)
from .models.activities import (
    ActivitiesState,
    BaseActivities,
    ActivitySessionCreate,
    ActivitySessionUpdate
)
from .service import DiscordService

logger = logging.getLogger(__name__)


# https://discordpy.readthedocs.io/en/stable/api.html?highlight=event#event-reference

async def on_message(service: DiscordService, message: Message):
    if message.author.bot:
        return None

    log_message(message)

    if message.author.id in (292615364448223233,):
        await message.add_reaction("🤡")

    if message.mentions and message.mentions[0].id == service.bot.user.id:
        try:
            response_message = await service.gigachat_client.chat(
                message.author.id,
                message.content
            )
            if response_message:
                return await message.reply(content=response_message.content)
        except Exception as e:
            logger.error(e)

    await service.bot.process_commands(message)

    image_urls = _get_image_attachment_urls_from_message(message)
    video_urls = _get_video_attachment_urls_from_message(message)

    if image_urls:
        result_tags: list[ImageTags] = []
        for image_url in image_urls:
            tags = await service.parser_client.get_image_tags(image_url)
            if tags and (tags.tags or tags.description):
                result_tags.append(tags)
        logger.info(f"{result_tags=}")
        if result_tags:
            await message.reply(
                content='\n\n'.join(
                    [f"{i + 1}. {m.text()}" for i, m in enumerate(result_tags)]
                )
            )

    if (image_urls or video_urls) and message.channel.id in (1241728108768264215, 960928970629582918,):
        vote_message = await create_binary_voting(message)

        d_config = await dynamic_config_db.get(service.db_pool)
        if d_config is not None:
            vote_messages_ids = d_config.get('vote_messages_ids', None)
            if vote_messages_ids is None:
                vote_messages_ids = []
            vote_messages_ids.append(vote_message.id)

            await dynamic_config_db.update(service.db_pool, d_config, vote_messages_ids=vote_messages_ids)


async def on_raw_reaction_add(service: DiscordService, reaction: Reaction, user: Member):
    async def on_binary_vote(vote_cap: int = 3):
        d_config = await dynamic_config_db.get(service.db_pool)
        if d_config is None:
            logger.error("Dynamic config not set!")
            return None

        vote_messages_ids: list | None = d_config.get('vote_messages_ids', None)
        if vote_messages_ids is None:
            logger.error("Vote messages ids not set!")
            return None

        if reaction.message.id not in vote_messages_ids:
            logger.info(f"Message {reaction.message.id} is not Vote Message")
            return None

        p_reacts, n_reacts = 0, 0
        for r in reaction.message.reactions:
            flag = BINARY_VOTE_REACTIONS.get(r.emoji, None)
            if flag is not None:
                if flag:
                    p_reacts = r.count
                else:
                    n_reacts = r.count

        if p_reacts >= vote_cap or n_reacts >= vote_cap:
            orig_message = await reaction.message.channel.fetch_message(reaction.message.reference.message_id)
            if not orig_message:
                logger.error(f"Original Vote Message {reaction.message.reference.message_id} not found")

            if p_reacts >= vote_cap:
                logger.info(f"Drop Voting for message {reaction.message.id} [Positive]")
                image_urls = _get_image_attachment_urls_from_message(orig_message)
                video_urls = _get_video_attachment_urls_from_message(orig_message)

                for i_url in image_urls:
                    await service.vk_pot_client.vk_bot_post(image_url=i_url)

                for v_url in video_urls:
                    await service.vk_pot_client.vk_bot_post(video_url=v_url)

            if n_reacts >= vote_cap:
                logger.info(f"Drop Voting for message {reaction.message.id} [Negative]")

            await reaction.message.delete()
            await orig_message.add_reaction(reaction.emoji)
            vote_messages_ids.remove(reaction.message.id)
            await dynamic_config_db.update(service.db_pool, d_config, vote_messages_ids=vote_messages_ids)

    if user.bot:
        return None

    logger.info(f"User {user.name} react {str(reaction.emoji)} message {reaction.message.id}")

    if str(reaction.emoji) in BINARY_VOTE_REACTIONS:
        await on_binary_vote()


async def on_ready():
    logger.info('Ready')


async def on_presence_update(service: DiscordService, before: Member, after: Member):
    def get_activities_state() -> ActivitiesState:
        state_dict = {}
        for a_type in ActivityType:
            a_type_name = a_type.name.lower()

            before_activities = set([act.name for act in before.activities if act.type is a_type])
            after_activities = set([act.name for act in after.activities if act.type is a_type])
            started_activities = after_activities.difference(before_activities)
            finished_activities = before_activities.difference(after_activities)
            unmodified_activities = before_activities.intersection(after_activities)

            state_dict[a_type_name] = {
                'before': before_activities,
                'after': after_activities,
                'started': started_activities,
                'finished': finished_activities,
                'unmodified': unmodified_activities
            }
        return ActivitiesState.model_validate(state_dict)

    def log_activities(activity_model: BaseActivities) -> None:
        activity = activity_model.rel_name
        if activity_model.started:
            logger.info(f"{before.name} start {activity=} {activity_model.started}")
        if activity_model.finished:
            logger.info(f"{before.name} finish {activity=} {activity_model.finished}")

    state = get_activities_state()
    if state.playing.has_changes:
        log_activities(state.playing)
        if state.playing.started:
            for a in state.playing.started:
                await activity_sessions_db.create(
                    service.db_pool,
                    ActivitySessionCreate(
                        user_id=after.id,
                        user_name=after.name,
                        activity_name=a
                    )
                )
            await _execute_cyberbool(service, state, after)
        if state.playing.finished:
            for a in state.playing.finished:
                activity_db = await activity_sessions_db.get_unfinished(service.db_pool, after.id, a)
                if activity_db:
                    await activity_sessions_db.update(
                        service.db_pool, activity_db.id, ActivitySessionUpdate(finished_at=datetime.datetime.utcnow())
                    )


async def on_voice_state_update(
        service: DiscordService,
        member: Member,
        before: VoiceState,
        after: VoiceState
):
    async def on_leave_channel():
        channel = before.channel
        logger.info(f"Member {member.display_name} has left the voice channel {channel.name}")

    async def on_join_channel():
        channel = after.channel
        logger.info(f"Member {member.display_name} joined voice channel {channel.name}")

    async def on_move():
        from_channel = before.channel
        to_channel = after.channel
        logger.info(f"Member {member.display_name} moved from {from_channel.name} to {to_channel.name}")

    async def on_start_stream():
        channel = after.channel
        logger.info(f"Member {member.display_name} started streaming in {channel.name}")

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


async def _execute_cyberbool(service: DiscordService, state: ActivitiesState, member: Member):
    async with service.db_pool.acquire() as conn:
        d_conf = await dynamic_config_db.get(conn)
        print(d_conf)
    if any([i in state.playing.started for i in d_conf.get('cyberbool', [])]):
        if voice := member.voice:
            bot_voice: VoiceClient = await connect_to_voice_channel(service.bot, voice.channel)
            try:
                await play_file(bot_voice, 'static/boris.mp4')
            except Exception as e:
                logger.error(e)


def _get_video_attachment_urls_from_message(
        message: Message
) -> list[str]:
    video_urls = _get_urls_from_text(message.content, VIDEO_EXT)
    if message.attachments:
        for attachment in message.attachments:
            if AttachmentType.by_content_type(attachment.content_type) is AttachmentType.VIDEO:
                video_urls.append(attachment.url)
    return video_urls


def _get_image_attachment_urls_from_message(
        message: Message
) -> list[str]:
    image_urls = _get_urls_from_text(message.content)
    if message.attachments:
        for attachment in message.attachments:
            if AttachmentType.by_content_type(attachment.content_type) is AttachmentType.PHOTO:
                image_urls.append(attachment.url)
    return image_urls


def _get_urls_from_text(text: str, ext_set: Sequence = IMG_EXT) -> list[str]:
    if not text:
        return []

    urls = []
    words = text.split()
    for word in words:
        if word.startswith(DISCORD_MEDIA_PREFIX) or word.startswith(DISCORD_ATTACHMENT_PREFIX):
            if any(ext in word.lower() for ext in ext_set):
                urls.append(word)
    return urls
