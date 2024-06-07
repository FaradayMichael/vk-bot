import datetime

from pydantic import (
    BaseModel,
    Field
)


class BaseActivities(BaseModel):
    rel_name: str | None = None

    before: set[str] = Field(default_factory=set)
    after: set[str] = Field(default_factory=set)

    started: set[str] = Field(default_factory=set)
    finished: set[str] = Field(default_factory=set)
    unmodified: set[str] = Field(default_factory=set)

    @property
    def has_changes(self) -> bool:
        return self.before != self.after


class PlayingActivities(BaseActivities):
    rel_name: str = 'playing'


class ActivitiesState(BaseModel):
    playing: PlayingActivities = PlayingActivities()


class ActivitySessionCreate(BaseModel):
    started_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    finished_at: datetime.datetime | None = None
    user_id: int
    user_name: str
    activity_name: str
    extra_data: dict = Field(default_factory=dict)


class ActivitySessionUpdate(BaseModel):
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    user_id: int | None = None
    user_name: str | None = None
    activity_name: str | None = None
    extra_data: dict | None = None


class ActivitySession(ActivitySessionCreate):
    id: int
