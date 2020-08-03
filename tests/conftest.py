# -*- coding: utf-8 -*-
"""Testing conf module."""
# third-party
import pytest
from falcon import testing

from .Memcache.app import app_memcache_1, app_memcache_2, app_memcache_3
from .Redis.app import app_redis_1, app_redis_2, app_redis_3


@pytest.fixture
def client_memcache_1() -> testing.TestClient:
    """Create testing client fixture for hook app"""
    return testing.TestClient(app_memcache_1)


@pytest.fixture
def client_memcache_2() -> testing.TestClient:
    """Create testing client fixture for hook app"""
    return testing.TestClient(app_memcache_2)


@pytest.fixture
def client_memcache_3() -> testing.TestClient:
    """Create testing client fixture for hook app"""
    return testing.TestClient(app_memcache_3)


@pytest.fixture
def client_redis_1() -> testing.TestClient:
    """Create testing client fixture for middleware app"""
    return testing.TestClient(app_redis_1)


@pytest.fixture
def client_redis_2() -> testing.TestClient:
    """Create testing client fixture for middleware app"""
    return testing.TestClient(app_redis_2)


@pytest.fixture
def client_redis_3() -> testing.TestClient:
    """Create testing client fixture for middleware app"""
    return testing.TestClient(app_redis_3)
