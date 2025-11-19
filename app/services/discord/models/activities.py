import datetime

from pydantic import BaseModel, Field, model_validator


class BaseActivities(BaseModel):
    rel_name: str | None = None

    user_id: str | None = None
    user_name: str | None = None

    before: set[str] = Field(default_factory=set)
    after: set[str] = Field(default_factory=set)

    started: set[str] = Field(default_factory=set)
    finished: set[str] = Field(default_factory=set)
    unmodified: set[str] = Field(default_factory=set)

    @property
    def has_changes(self) -> bool:
        return self.before != self.after

    @model_validator(mode="before")
    def validate_user_id(cls, data: dict):  # noqa
        data["user_id"] = str(data["user_id"])
        return data


class PlayingActivities(BaseActivities):
    rel_name: str = "playing"


class ListeningActivities(BaseActivities):
    rel_name: str = "listening"


class ActivitiesState(BaseModel):
    playing: PlayingActivities = Field(default_factory=PlayingActivities)
    streaming: BaseActivities = Field(default_factory=BaseActivities)
    watching: BaseActivities = Field(default_factory=BaseActivities)
    listening: ListeningActivities = Field(default_factory=ListeningActivities)


class ActivitySessionCreate(BaseModel):
    started_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    finished_at: datetime.datetime | None = None
    user_id: str
    user_name: str
    activity_name: str
    extra_data: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    def validate_user_id(cls, data: dict):
        data["user_id"] = str(data["user_id"])
        return data


class ActivitySessionUpdate(BaseModel):
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    user_id: str | None = None
    user_name: str | None = None
    activity_name: str | None = None
    extra_data: dict | None = None

    @model_validator(mode="before")
    def validate_user_id(cls, data: dict):  # noqa
        if data.get("user_id"):
            data["user_id"] = str(data["user_id"])
        return data


class ActivitySession(ActivitySessionCreate):
    id: int
    started_at_tz: datetime.datetime | None = None
    finished_at_tz: datetime.datetime | None = None


class StatusSessionCreate(BaseModel):
    started_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    finished_at: datetime.datetime | None = None
    user_id: str
    user_name: str
    status: str
    extra_data: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    def validate_user_id(cls, data: dict):
        data["user_id"] = str(data["user_id"])
        return data


class StatusSessionUpdate(BaseModel):
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    user_id: str | None = None
    user_name: str | None = None
    status: str | None = None
    extra_data: dict | None = None

    @model_validator(mode="before")
    def validate_user_id(cls, data: dict):
        if data.get("user_id"):
            data["user_id"] = str(data["user_id"])
        return data


class StatusSession(StatusSessionCreate):
    id: int
    started_at_tz: datetime.datetime | None = None
    finished_at_tz: datetime.datetime | None = None
