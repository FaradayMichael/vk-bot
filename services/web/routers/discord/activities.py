import base64
import datetime
import logging

import pandas as pd
import pytz
from fastapi import (
    APIRouter,
    Depends,
    Request
)
from fastapi.responses import (
    HTMLResponse
)
from jinja2 import Environment
from plotly import (
    express as px
)

from misc.db import Connection
from misc.depends.db import (
    get as get_conn
)
from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.session import Session
from db import (
    activity_sessions as activity_sessions_db
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/activities')


@router.get('/', response_class=HTMLResponse)
async def vk_messages_view(
        request: Request,
        user_id: int = None,
        from_date: datetime.date = None,
        to_date: datetime.date = None,
        # group: bool = False,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: Connection = Depends(get_conn),
):
    tz = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(tz=tz)
    # utcnow = datetime.datetime.utcnow()
    users_data = await activity_sessions_db.get_users_data(conn)

    base64_encoded_image = None
    if user_id:
        activities = await activity_sessions_db.get_all(
            conn=conn,
            user_id=user_id,
            from_dt=from_date,
            to_dt=to_date,
            with_tz=tz
        )
        if activities:
            hours_data: dict = {}
            for activity in activities:
                hours = hours_data.get(activity.activity_name, 0)
                finished_at = activity.finished_at or now
                hours_data[
                    activity.activity_name
                ] = round(hours + (finished_at - activity.started_at).total_seconds() / 3600, 1)

            df_list = []
            for a in activities:
                df_list.append({
                    'Activity': a.activity_name,
                    'Start': (a.started_at_tz or a.started_at).strftime("%Y-%m-%d %H:%M:%S"),
                    'Finish': (a.finished_at_tz or a.finished_at or now).strftime("%Y-%m-%d %H:%M:%S"),
                    f'Total hours': f"{a.activity_name} — {hours_data[a.activity_name]}"
                })
            df = pd.DataFrame(df_list)
            fig = px.timeline(
                df,
                x_start="Start",
                x_end="Finish",
                y="Activity",
                color='Total hours',
                width=1900,
                title='1984',
            )
            img_bytes = fig.to_image(format='png')
            base64_encoded_image = base64.b64encode(img_bytes).decode("utf-8")

        u_d = list(filter(lambda x: x[0] == user_id, users_data))
        if u_d:
            users_data.insert(0, users_data.pop(users_data.index(u_d[0])))

    from_date_default = from_date or now
    to_date_default = to_date or (now + datetime.timedelta(days=1))
    return jinja.get_template('discord/activities.html').render(
        user=session.user,
        request=request,
        users_data=users_data,
        image=base64_encoded_image,
        from_date_default=from_date_default.strftime('%Y-%m-%d'),
        to_date_default=to_date_default.strftime('%Y-%m-%d'),
        user_id=user_id,
        # group=group
    )
