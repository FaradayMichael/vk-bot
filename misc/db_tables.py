from enum import StrEnum


class DBTables(StrEnum):
    USERS = 'users'
    TRIGGERS_ANSWERS = 'triggers_answers'
    VK_TASKS = 'vk_tasks'
    KNOW_IDS = 'know_ids'
    SEND_ON_SCHEDULE = 'send_on_schedule'
    TRIGGERS_HISTORY = 'triggers_history'
    DYNAMIC_CONFIG = 'dynamic_config'
