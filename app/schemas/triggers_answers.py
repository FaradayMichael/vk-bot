import datetime

from pydantic import BaseModel, model_validator


class TriggerBase(BaseModel):
    trigger: str


class AnswerBase(BaseModel):
    answer: str
    attachment: str | None = None

    def __hash__(self):
        return hash(f"{self.answer} {self.attachment}")


class TriggerAnswerCreate(TriggerBase, AnswerBase):
    trigger: str
    answer: str
    attachment: str | None = None


class TriggerAnswer(TriggerAnswerCreate):
    id: int
    en: bool
    ctime: datetime.datetime


class Answer(AnswerBase):
    id: int


class TriggerGroup(TriggerBase):
    trigger: str
    answers: list[Answer]

    # @model_validator(mode='before')
    # def json_to_list(cls, data: dict):  # noqa
    #     if data.get('answers', None) is not None:
    #         data['answers'] = json.loads(data['answers'])
    #     return data


class AnswerGroup(AnswerBase):
    triggers: list[TriggerBase]
