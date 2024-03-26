import datetime

from pydantic import BaseModel

from models.know_ids import KnowIds
from models.triggers_answers import TriggerAnswer


class TriggersHistoryNew(BaseModel):
    trigger_answer_id: int
    vk_id: int
    message_data: dict


class TriggersHistory(TriggersHistoryNew):
    id: int
    ctime: datetime.datetime

    know_id: KnowIds | None
    trigger_answer: TriggerAnswer
