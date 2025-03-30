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
from jinja2 import (
    Environment
)

from business_logic.discord import (
    activities as discord_activities_bl,
)
from db import (
    status_sessions as status_sessions_db
)
from utils.fastapi.depends.db import (
    get as get_db
)
from utils.fastapi.depends.session import (
    get as ges_session
)
from utils.fastapi.depends.jinja import (
    get as get_jinja
)
from models.discord_status_sessions import (
    DiscordStatusSession
)
from models.discord_activity_sessions import (
    DiscordActivitySession
)
from utils.fastapi.session import (
    Session
)
from utils import (
    db
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/statuses')


@router.get('/', response_class=HTMLResponse)
async def status_sessions_view(
        request: Request,
        user_id: str = None,
        from_date: datetime.date = None,
        to_date: datetime.date = None,
        # group: bool = False,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: db.Session = Depends(get_db),
):
    tz = pytz.timezone('Europe/Moscow')
    now = datetime.datetime.now(tz=tz)
    users_data = await status_sessions_db.get_users_data(conn)

    image_base64_data = None
    if user_id:
        activities = await status_sessions_db.get_list(
            session=conn,
            user_id=user_id,
            from_dt=from_date,
            to_dt=to_date,
        )
        if activities:
            activities = list(map(_statuses_model_to_activities_model, activities))

            image_dataurl_gantt = discord_activities_bl.create_figure_image_gantt(activities, now, tz)
            image_base64_data = image_dataurl_gantt.data.decode("utf-8")

        users_data = _insert_current_user_in_head(users_data, user_id)

    from_date_default = from_date or now
    to_date_default = to_date or (now + datetime.timedelta(days=1))
    return jinja.get_template('discord/statuses.html').render(
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


def _statuses_model_to_activities_model(model: DiscordStatusSession) -> DiscordActivitySession:
    return DiscordActivitySession(
        activity_name=model.status,
        user_id=model.user_id,
        user_name=model.user_name,
        started_at=model.started_at,
        finished_at=model.finished_at,
        extra_data=model.extra_data,
    )
