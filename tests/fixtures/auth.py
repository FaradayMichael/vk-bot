import base64
import re
from typing import Tuple

import pytest

from db import (
    users as users_db
)

from misc import db
from models.users import User
from tests.fixtures.app import reset_table
from tests.fixtures.mailhog import MailHOG


@pytest.fixture(scope="session")
async def user(
        rest_api_client,
        mailhog: MailHOG,
        db_pool
) -> dict:
    data = {
        "email": "test@mail.ru",
        'username': 'test'
    }
    user, password = await create_user(
        data,
        rest_api_client,
        mailhog,
    )
    token = await user_login(user.email, password, rest_api_client)
    yield {
        'token': token,
        'me': user,
        'password': password,
        'email': data['email']
    }
    await reset_table("users", db_pool)


async def create_user(
        data: dict,
        app_client,
        mailhog,
) -> Tuple[User, str]:
    response = await app_client.post("/api/v1/admin/users/", json=data)
    assert response.status_code == 200, f'status_code={response.status_code}, response={response.text}'

    password = await get_password_from_mail(data['email'], mailhog)

    return User.model_validate(response.json()['data']), password


async def get_password_from_mail(email, mailhog):
    messages = await mailhog.messages()

    message = messages[0]
    assert email in message['Content']['Headers']['To']
    body = base64.decodebytes(bytes(message['MIME']['Parts'][0]['Body'], 'utf8')).decode('utf-8')
    result = re.search(r'<b>([0-9a-zA-Z]{8,12})</b>', body)
    return result.group(1)


async def logout(token, rest_api_client):
    response = await rest_api_client.post("/api/v1/auth/logout")
    assert response.status_code == 200, response.text
    assert response.json()['success'] is True

    assert response.json()['data']['token'] == token
    assert response.json()['data']['me']['id'] == 0


async def user_login(login: str, password: str, rest_api_client) -> str:
    data = {
        "username_or_email": login,
        "password": password,
    }
    response = await rest_api_client.post("/api/v1/auth/login", json=data)
    assert response.status_code == 200, f"Response: {response.text}"
    json = response.json()
    return json['data']['token']


async def delete_user(db_pool: db.Connection, user_id: int):
    await db_pool.execute("UPDATE users set en=false WHERE id=$1", user_id)


async def make_admin(db_pool: db.Connection, user: User):
    await db.update(
        db_pool,
        'users',
        user['id'],
        {"is_admin": False}
    )
