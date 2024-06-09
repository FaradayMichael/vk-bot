import base64
import datetime
import logging
import random

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
from plotly.tools import DEFAULT_PLOTLY_COLORS

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
        group: bool = False,
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
            act_names = set([a.activity_name for a in activities])
            colors = DEFAULT_PLOTLY_COLORS.copy()
            if len_diff := len(act_names) - len(colors) > 0:
                for _ in range(len_diff):
                    r = int(random.random() * 255)
                    b = int(random.random() * 255)
                    g = int(random.random() * 255)
                    colors.append(f"rgb({r}, {g}, {b})")

            df = []
            plot_colors = {}
            i = iter(colors)
            for a in activities:
                df.append({'Task': a.activity_name, 'Start': a.started_at, 'Finish': a.finished_at or now})
                plot_colors[a.activity_name] = plot_colors.get(a.activity_name) or next(i)

            fig: Figure = ff.create_gantt(
                df,
                title="1984",
                show_colorbar=True,
                showgrid_x=True,
                showgrid_y=True,
                width=1900,
                group_tasks=group,
                colors=plot_colors,
                index_col='Task'
            )
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
        group=group
    )
