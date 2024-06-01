import logging

from discord import (
    Message,
    VoiceClient,
    ActivityType
)
from discord.member import (
    Member,
    VoiceState
)

from business_logic.images import parse_image_tags
from db import (
    dynamic_config as dynamic_config_db
)
from models.base import AttachmentType
from models.images import ImageTags
from .utils.messages import log_message
from .utils.voice_channels import (
    leave_from_empty_voice_channel,
    connect_to_voice_channel,
    play_file
)
from .models import (
    ActivitiesState,
    BaseActivities
)
from .service import DiscordService

logger = logging.getLogger(__name__)

DISCORD_MEDIA_PREFIX = 'https://media'
IMG_EXT = ('jpg', 'jpeg', 'png', 'gif', 'bmp')


# https://discordpy.readthedocs.io/en/stable/api.html?highlight=event#event-reference

async def on_message(service: DiscordService, message: Message):
    if message.author.bot:
        return None

    log_message(message)

    if message.author.id in (292615364448223233,):
        await message.add_reaction("🤡")

    await service.bot.process_commands(message)

    image_urls = _get_image_urls_from_text(message.content)
    if message.attachments:
        logger.info(message.attachments)
        for attachment in message.attachments:
            if AttachmentType.by_content_type(attachment.content_type) is AttachmentType.PHOTO:
                image_urls.append(attachment.url)

    if image_urls:
        result_tags: list[ImageTags] = []
        for image_url in image_urls:
            tags = await parse_image_tags(image_url)
            if tags and (tags.tags or tags.description):
                result_tags.append(tags)
        logger.info(f"{result_tags=}")
        if result_tags:
            await message.reply(
                content='\n\n'.join(
                    [f"{i + 1}. {m.text()}" for i, m in enumerate(result_tags)]
                )
            )


async def on_ready():
    logger.info('Ready')


async def on_presence_update(service: DiscordService, before: Member, after: Member):
    def get_activities_state() -> ActivitiesState:
        state_dict = {}
        for a_type in ActivityType:
            a_type_name = a_type.name.lower()

            before_activities = set([a.name for a in before.activities if a.type is a_type])
            after_activities = set([a.name for a in after.activities if a.type is a_type])
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
            await _execute_cyberbool(service, state, after)


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


def _get_image_urls_from_text(text: str) -> list[str]:
    if not text:
        return []

    urls = []
    words = text.split()
    for word in words:
        if word.startswith(DISCORD_MEDIA_PREFIX):
            if any(ext in word for ext in IMG_EXT):
                urls.append(word)
    return urls
