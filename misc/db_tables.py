from enum import StrEnum


class DBTables(StrEnum):
    USERS = 'users'
    TRIGGERS_ANSWERS = 'triggers_answers'
    VK_TASKS = 'vk_tasks'
    KNOW_IDS = 'know_ids'
    SEND_ON_SCHEDULE = 'send_on_schedule'
    TRIGGERS_HISTORY = 'triggers_history'
    DYNAMIC_CONFIG = 'dynamic_config'
    DISCORD_ACTIVITY_SESSIONS = 'discord_activity_sessions'
    DISCORD_REPLY_COMMANDS = 'discord_reply_commands'
    GIGACHAT_MESSAGES = 'gigachat_messages'
    POLLS = 'polls'
    DISCORD_STATUS_SESSIONS = 'discord_status_sessions'
