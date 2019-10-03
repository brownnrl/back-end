import humps
import pytest
import requests
from django import test
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from pytest_mock import MockFixture

from ..unit.test_tasks import run_next_task

def test_update_profile_random_params(
    authed_client: test.Client, user: User, random_profile_dict
):
    res = authed_client.patch(
        reverse("update_profile"), humps.camelize(random_profile_dict)
    )

    assert res.status_code == 200

    user.refresh_from_db()
    profile = user.profile

    for key, val in random_profile_dict.items():
        assert getattr(profile, key) == val


def test_update_profile_frontend_params(
    authed_client: test.Client, user: User, update_profile_params
):
    res = authed_client.patch(
        reverse("update_profile"), humps.camelize(update_profile_params)
    )

    assert res.status_code == 200

    user.refresh_from_db()
    profile = user.profile

    for key, val in update_profile_params.items():
        assert getattr(profile, key) == val


def test_update_profile_random_params_update_task_to_pybot(
        authed_client: test.Client,
        user: User,
        random_profile_dict,
        mocker: MockFixture,
):
    mil_status = 'current'
    slack_id = 'slack1234'
    random_profile_dict['military_status'] = mil_status
    random_profile_dict['slack_id'] = slack_id
    res = authed_client.patch(
        reverse("update_profile"), humps.camelize(random_profile_dict)
    )

    assert res.status_code == 200

    user.refresh_from_db()
    profile = user.profile

    for key, val in random_profile_dict.items():
        assert getattr(profile, key) == val

    mock = mocker.patch.object(requests, "post")
    run_next_task()
    assert mock.called
    assert mock.call_args[0] == (f"{settings.PYBOT_URL}/pybot/api/v1/slack/update",)
    assert "slack_id" in mock.call_args[1]["json"]
    assert "military_status" in mock.call_args[1]["json"]
    assert mock.call_args[1]["json"]["slack_id"] == slack_id
    assert mock.call_args[1]["json"]["military_status"] == mil_status
    
    # Try again not changing slack id or mil status
    mock.reset_mock()
    random_profile_dict['address_2'] = 'something else'
    res = authed_client.patch(
        reverse("update_profile"), humps.camelize(random_profile_dict)
    )
    run_next_task()
    assert not mock.called

@pytest.mark.parametrize(
    argnames="method, status", argvalues=[("post", 405), ("get", 200), ("patch", 200)]
)
def test_update_requires_get_or_patch(
    authed_client: test.Client, method: str, status: int
):
    func = getattr(authed_client, method)
    res = func(reverse("update_profile"))
    assert res.status_code == status


@pytest.mark.parametrize(
    argnames="content_type, status",
    argvalues=[("application/octet-stream", 415), ("text/html", 415)],
)
def test_update_requires_correct_format(
    authed_client: test.Client, content_type: str, status: int, update_profile_params
):
    res = authed_client.patch(
        reverse("update_profile"), update_profile_params, content_type=content_type
    )

    assert res.status_code == status
