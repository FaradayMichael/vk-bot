from pydantic import BaseModel, Field


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
