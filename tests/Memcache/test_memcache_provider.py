# -*- coding: utf-8 -*-
"""Test middleware redis provider module."""
# standard library
import os
import time

# third-party
import pytest
from falcon.testing import Result
from falcon_provider_memcache import memcache_client

# first-party
from falcon_provider_rate_limit.middleware import RateLimitMiddleware

# required for monkeypatch
from .app import MemcacheResource

# clear client data from redis
MEMCACHE_HOST = os.getenv('MEMCACHE_HOST', 'localhost')
MEMCACHE_PORT = int(os.getenv('MEMCACHE_PORT', '11211'))
mc = memcache_client((MEMCACHE_HOST, MEMCACHE_PORT))
mc.delete('dos-limit')
mc.delete('rate-limit')
mc.delete('no-auth-key/middleware')
mc.delete('127.0.0.1')
mc.delete('127.0.0.1/middleware')


@pytest.mark.parametrize(
    'param,limit,remaining,status_code,text',
    [
        ('first', '2', '1', 200, 'first-worked'),
        ('second', '2', '0', 200, 'second-worked'),
        (
            'third',
            '2',
            '0',
            429,
            (
                '{"title": "To Many Request", "description": "Client exceeded rate limit of 2 '
                'requests per 1 minutes."}'
            ),
        ),
        (
            'fourth',
            '2',
            '0',
            429,
            (
                '{"title": "To Many Request", "description": "Client exceeded rate limit of 2 '
                'requests per 1 minutes."}'
            ),
        ),
        ('fifth', '2', '1', 200, 'fifth-worked'),
    ],
)
def test_authenticated_rate_limit(
    client_memcache_1: object,
    param: str,
    limit: str,
    remaining: str,
    status_code: int,
    text: str,
    monkeypatch: object,
):
    """Testing authenticated user rate limit.

    Setup and Test
    * set user_id via monkeypatch along with _testing() method
      in middleware to test reading user_id from context.
    * set the authenticated limit via monkeypatch.
    * perform request to ensure rate-limit is reached.
    * validate proper headers are set including retry-after.
    * validate rate-limit timeout expires and request return to normal.

    Args:
        client_memcache_1 (fixture): Pytest fixture for falcon.testing.Testclient.
        param (str): A query param value to send to request.
        limit (str): The expected rate limit value for assert (set in app.py).
        remaining (str): The expected number of remaining rate limit request for assert.
        status_code (int): The expected status code for assert.
        text (str): The expected text of the request response for assert.
        monkeypatch (fixture): Pytest _pytest.monkeypatch.MonkeyPatch object.
    """
    monkeypatch.setattr(RateLimitMiddleware, 'user_id', 123, raising=False)
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'authenticated_limit', int(limit))

    if param == 'fourth':
        # sleep to ensure retry-after value is correct.
        time.sleep(30)
    elif param == 'fifth':
        # sleep to ensure that rate-limit has been cleared
        time.sleep(30)

    # make request
    response: Result = client_memcache_1.simulate_get('/middleware', params={'key': param})

    if param in ['third', 'fourth']:
        # validate retry-after is returned
        assert response.headers.get('retry-after') is not None, f'headers: {response.headers}'
    assert response.headers.get('x-ratelimit-limit') == limit, f'headers: {response.headers}'
    assert (
        response.headers.get('x-ratelimit-remaining') == remaining
    ), f'headers: {response.headers}'
    assert response.headers.get('x-ratelimit-reset') is not None, f'headers: {response.headers}'
    assert response.status_code == status_code, f'status_code: {response.status_code}'
    assert response.text == text, f'text: {response.text}'


@pytest.mark.parametrize(
    'param,limit,remaining,status_code,text',
    [
        ('first', '2', '1', 200, 'first-worked'),
        ('second', '2', '0', 200, 'second-worked'),
        (
            'third',
            '2',
            '0',
            429,
            (
                '{"title": "To Many Request", "description": "Client exceeded rate limit of 2 '
                'requests per 1 minutes."}'
            ),
        ),
    ],
)
def test_unauthenticated_rate_limit(
    client_memcache_2: object,
    param: str,
    limit: str,
    remaining: str,
    status_code: int,
    text: str,
    monkeypatch: object,
):
    """Testing unauthenticated user rate limit.

    Setup and Test
    * set the unauthenticated limit via monkeypatch.
    * set the global limit to off via monkeypatch to ensure the resource limit is being used.
    * perform request to ensure rate-limit is reached.
    * validate proper headers are set including retry-after.

    Args:
        client_memcache_2 (fixture): Pytest fixture for falcon.testing.Testclient.
        param (str): A query param value to send to request.
        limit (str): The expected rate limit value for assert (set in app.py).
        remaining (str): The expected number of remaining rate limit request for assert.
        status_code (int): The expected status code for assert.
        text (str): The expected text of the request response for assert.
        monkeypatch (fixture): Pytest _pytest.monkeypatch.MonkeyPatch object.
    """
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'unauthenticated_limit', int(limit))
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'global_limit', False)

    # make request
    response: Result = client_memcache_2.simulate_get('/middleware', params={'key': param})

    assert response.headers.get('x-ratelimit-limit') == limit
    assert response.headers.get('x-ratelimit-remaining') == remaining
    assert response.headers.get('x-ratelimit-reset') is not None
    assert response.status_code == status_code
    assert response.text == text
    if param in ['third']:
        # validate retry-after is returned
        assert response.headers.get('retry-after') is not None


@pytest.mark.parametrize(
    'param,limit,remaining,status_code,text', [('first', '2', '1', 200, 'first-worked')]
)
def test_unauthenticated_with_none_auth_keys(
    client_memcache_3: object,
    param: str,
    limit: str,
    remaining: str,
    status_code: int,
    text: str,
    monkeypatch: object,
):
    """Testing authenticated user rate limit.

    Setup and Test
    * set client_key via monkeypatch along with _testing() method
      in middleware to test reading client_key from context.
    * set the unauthenticated limit via monkeypatch.
    * set the global limit to off via monkeypatch to ensure the resource limit is being used.
    * perform request to ensure rate-limit is reached.
    * validate proper headers are set including retry-after.

    Args:
        client_memcache_3 (fixture): Pytest fixture for falcon.testing.Testclient.
        param (str): A query param value to send to request.
        limit (str): The expected rate limit value for assert (set in app.py).
        remaining (str): The expected number of remaining rate limit request for assert.
        status_code (int): The expected status code for assert.
        text (str): The expected text of the request response for assert.
        monkeypatch (fixture): Pytest _pytest.monkeypatch.MonkeyPatch object.
    """
    monkeypatch.setattr(RateLimitMiddleware, 'client_key', 'no-auth-key', raising=False)
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'unauthenticated_limit', int(limit))
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'global_limit', False)

    # make request
    response: Result = client_memcache_3.simulate_get('/middleware', params={'key': param})

    assert response.headers.get('x-ratelimit-limit') == limit
    assert response.headers.get('x-ratelimit-remaining') == remaining
    assert response.headers.get('x-ratelimit-reset') is not None
    assert response.status_code == status_code
    assert response.text == text


@pytest.mark.parametrize(
    'param,limit,remaining,status_code,text',
    [
        ('first', '2', '1', 200, 'first-worked'),
        ('second', '2', '0', 200, 'second-worked'),
        (
            'third',
            '2',
            '0',
            429,
            (
                '{"title": "To Many Request", "description": "Client exceeded rate limit of 2 '
                'requests per seconds."}'
            ),
        ),
    ],
)
def test_dos_limit(
    client_memcache_1: object,
    param: str,
    limit: str,
    remaining: str,
    status_code: int,
    text: str,
    monkeypatch: object,
):
    """Testing dos limits

    Setup and Test
    * set the dos limit via monkeypatch.
    * set the global limit to off via monkeypatch to ensure the resource limit is being used.
    * perform request to ensure rate-limit is reached.
    * validate proper headers are set including retry-after.

    Args:
        client_memcache_1 (fixture): Pytest fixture for falcon.testing.Testclient.
        param (str): A query param value to send to request.
        limit (str): The expected rate limit value for assert (set in app.py).
        remaining (str): The expected number of remaining rate limit request for assert.
        status_code (int): The expected status code for assert.
        text (str): The expected text of the request response for assert.
        monkeypatch (fixture): Pytest _pytest.monkeypatch.MonkeyPatch object.
    """
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'dos_limit', int(limit))
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'global_limit', False)

    # make request
    response: Result = client_memcache_1.simulate_get('/middleware', params={'key': param})

    assert response.headers.get('x-ratelimit-limit') == limit
    assert response.headers.get('x-ratelimit-remaining') == remaining
    assert response.headers.get('x-ratelimit-reset') is not None
    assert response.status_code == status_code
    assert response.text == text
    if param in ['third']:
        # validate retry-after is returned
        assert response.headers.get('retry-after') is not None


@pytest.mark.parametrize('param,status_code,text', [('first', 200, 'first-worked')])
def test_disabled(
    client_memcache_1: object, param: str, status_code: int, text: str, monkeypatch: object,
):
    """Testing disabled rate limit

    Setup and Test
    * disable rate limit at the resource level.

    Args:
        client_memcache_1 (fixture): Pytest fixture for falcon.testing.Testclient.
        param (str): A query param value to send to request.
        status_code (int): The expected status code for assert.
        text (str): The expected text of the request response for assert.
        monkeypatch (fixture): Pytest _pytest.monkeypatch.MonkeyPatch object.
    """
    monkeypatch.setitem(MemcacheResource.rate_limit_control, 'enabled', False)

    # make request
    response: Result = client_memcache_1.simulate_get('/middleware', params={'key': param})

    assert response.headers.get('x-ratelimit-limit') is None
    assert response.headers.get('x-ratelimit-remaining') is None
    assert response.headers.get('x-ratelimit-reset') is None
    assert response.status_code == status_code
    assert response.text == text


@pytest.mark.parametrize('param,status_code,text', [('first', 200, 'first-worked')])
def test_no_limits(client_memcache_3: object, param: str, status_code: int, text: str):
    """Testing disabled rate limit

    Setup and Test
    * with all limits set to 0 test that rate limit is effectively disabled.

    Args:
        client_memcache_3 (fixture): Pytest fixture for falcon.testing.Testclient.
        param (str): A query param value to send to request.
        status_code (int): The expected status code for assert.
        text (str): The expected text of the request response for assert.
    """
    # make request
    response: Result = client_memcache_3.simulate_get('/middleware', params={'key': param})

    assert response.status_code == status_code
    assert response.text == text
