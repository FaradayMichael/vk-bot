import datetime
import logging

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

from business_logic.discord import (
    activities as discord_activities_bl,
)
from db import (
    activity_sessions as activity_sessions_db
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
    users_data = await activity_sessions_db.get_users_data(conn)

    image_base64_data = None
    if user_id:
        activities = await activity_sessions_db.get_all(
            conn=conn,
            user_id=user_id,
            from_dt=from_date,
            to_dt=to_date,
            with_tz=tz
        )
        if activities:
            image_dataurl_gantt = discord_activities_bl.create_figure_image_gantt(activities, now, tz)
            image_base64_data = image_dataurl_gantt.data.decode("utf-8")

        users_data = _insert_current_user_in_head(users_data, user_id)

    from_date_default = from_date or now
    to_date_default = to_date or (now + datetime.timedelta(days=1))
    return jinja.get_template('discord/activities.html').render(
        user=session.user,
        request=request,
        users_data=users_data,
        image=image_base64_data,
        from_date_default=from_date_default.strftime('%Y-%m-%d'),
        to_date_default=to_date_default.strftime('%Y-%m-%d'),
        user_id=user_id,
        # group=group
    )


def _insert_current_user_in_head(users_data, user_id):
    u_d = list(filter(lambda x: x[0] == user_id, users_data))
    if u_d:
        users_data.insert(0, users_data.pop(users_data.index(u_d[0])))
    return users_data
