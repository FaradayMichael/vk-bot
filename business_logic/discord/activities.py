import datetime

import pandas as pd
from plotly import (
    express as px
)
from plotly.graph_objs import Figure

from misc.dataurl import DataURL
from misc.plotly import figure_to_image_dataurl
from services.discord.models.activities import (
    ActivitySession
)


def create_figure_image_gantt(
        activities: list[ActivitySession],
        now: datetime.datetime | None = None,
        tz: datetime.tzinfo | None = None,
) -> DataURL | None:
    figure = create_figure_gantt(activities, now, tz)
    if not figure:
        return None
    return figure_to_image_dataurl(figure)


def create_figure_gantt(
        activities: list[ActivitySession],
        now: datetime.datetime | None = None,
        tz: datetime.tzinfo | None = None,
) -> Figure | None:
    if not activities:
        return None

    now = now or datetime.datetime.now(tz=tz)

    hours_data: dict = {}
    for activity in activities:
        hours = hours_data.get(activity.activity_name, 0)
        finished_at = activity.finished_at or now
        hours_data[
            activity.activity_name
        ] = round(hours + (finished_at - activity.started_at).total_seconds() / 3600, 1)

    df_list = []
    activities.sort(key=lambda x: hours_data[x.activity_name], reverse=True)
    for a in activities:
        df_list.append({
            'Activity': a.activity_name,
            'Start': (a.started_at_tz or a.started_at).strftime("%Y-%m-%d %H:%M:%S"),
            'Finish': (a.finished_at_tz or a.finished_at or now).strftime("%Y-%m-%d %H:%M:%S"),
            'Total hours': f"{a.activity_name} — {hours_data[a.activity_name]}"
        })
    df = pd.DataFrame(df_list)
    return px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Activity",
        color='Total hours',
        width=1900,
        title='1984',
    )


