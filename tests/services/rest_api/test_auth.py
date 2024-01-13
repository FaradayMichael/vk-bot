import pytest
from tests.fixtures.auth import (
    logout
)

from services.rest_api.routers import API_PREFIX


@pytest.mark.asyncio
async def test_unauthorised_me(rest_api_client):
    response = await rest_api_client.get(f"{API_PREFIX}/auth/me")
    assert response.status_code == 200
    assert response.json()['success'] is True

    assert response.json()['data']['token'] != ''
    assert response.json()['data']['me']['id'] == 0


@pytest.mark.asyncio
async def test_login(rest_api_client, user):
    # await logout(user['token'], rest_api_client)

    data = {
        'username_or_email': user['email'],
        'password': user['password']
    }
    response = await rest_api_client.post(f"{API_PREFIX}/auth/login", json=data)

    assert response.status_code == 200, response.text
    assert response.json()['data']['token'] == user['token']
    assert response.json()['data']['me']['id'] == user['me'].id


@pytest.mark.asyncio
async def test_logout(rest_api_client, user):
    await logout(user['token'], rest_api_client)
