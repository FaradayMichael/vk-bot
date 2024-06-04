import base64
import datetime
import logging

from fastapi import (
    APIRouter,
    Depends,
    Request
)
from fastapi.responses import (
    HTMLResponse
)
from jinja2 import Environment
import plotly.figure_factory as ff
from plotly.graph_objs import Figure

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
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: Connection = Depends(get_conn),
):
    now = datetime.datetime.utcnow()
    users_data = await activity_sessions_db.get_users_data(conn)

    base64_encoded_image = None
    if user_id:
        activities = await activity_sessions_db.get_all(
            conn=conn,
            user_id=user_id,
            from_dt=from_date,
            to_dt=to_date,
        )
        if activities:
            df = [
                {'Task': a.activity_name, 'Start': a.started_at, 'Finish': a.finished_at or now}
                for a in activities
            ]
            fig: Figure = ff.create_gantt(df, show_colorbar=True)
            img_bytes = fig.to_image(format='png')
            base64_encoded_image = base64.b64encode(img_bytes).decode("utf-8")

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
    )
