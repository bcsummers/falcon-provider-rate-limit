"""Falcon app used for testing."""
# standard library
import os

# third-party
import falcon

# first-party
from falcon_provider_rate_limit.middleware import RateLimitMiddleware
from falcon_provider_rate_limit.utils import MemcacheRateLimitProvider

# Memcached
MEMCACHE_HOST = os.getenv('MEMCACHE_HOST', 'localhost')
MEMCACHE_PORT = int(os.getenv('MEMCACHE_PORT', '11211'))
global_rate_limit_control = {
    'enabled': False,
    'authenticated_limit': 0,
    'dos_limit': 0,
    'global_limit': True,
    'limit_window': 1,
    'unauthenticated_limit': 0,
}


class MemcacheResource:
    """Memcache middleware testing resource."""

    rate_limit_control = {
        'enabled': True,
        'authenticated_limit': 0,
        'dos_limit': 0,
        'global_limit': True,
        'limit_window': 1,
        'unauthenticated_limit': 0,
    }

    def on_get(self, req, resp):
        """Support GET method."""
        key = req.get_param('key')
        resp.text = f'{key}-worked'
        resp.status_code = falcon.HTTP_OK


# Provider using auth_key and client_key
memcache_provider_1 = MemcacheRateLimitProvider(
    server=(MEMCACHE_HOST, MEMCACHE_PORT),
    rate_limit_control=global_rate_limit_control,
    auth_key='user_id',
    client_key='client_key',
)
app_memcache_1 = falcon.App(middleware=[RateLimitMiddleware(memcache_provider_1)])
app_memcache_1.add_route('/middleware', MemcacheResource())

# Provider using no client_key
memcache_provider_2 = MemcacheRateLimitProvider(
    server=(MEMCACHE_HOST, MEMCACHE_PORT),
    rate_limit_control=global_rate_limit_control,
    auth_key='is_authenticated',
    client_key=None,
)
app_memcache_2 = falcon.App(middleware=[RateLimitMiddleware(memcache_provider_2)])
app_memcache_2.add_route('/middleware', MemcacheResource())

# Provider with no auth_key
memcache_provider_3 = MemcacheRateLimitProvider(
    server=(MEMCACHE_HOST, MEMCACHE_PORT),
    rate_limit_control=global_rate_limit_control,
    auth_key=None,
    client_key='client_key',
)
app_memcache_3 = falcon.App(middleware=[RateLimitMiddleware(memcache_provider_3)])
app_memcache_3.add_route('/middleware', MemcacheResource())
