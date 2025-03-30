import datetime

from pydantic import BaseModel

from models_old.know_ids import KnowIds
from models_old.triggers_answers import TriggerAnswer
from services.vk_bot.models.vk import VkMessage


class TriggersHistoryNew(BaseModel):
    trigger_answer_id: int
    vk_id: int
    message_data: VkMessage


class TriggersHistory(TriggersHistoryNew):
    id: int
    ctime: datetime.datetime

    know_id: KnowIds | None
    trigger_answer: TriggerAnswer
