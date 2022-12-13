"""Falcon app used for testing."""
# standard library
import os

# third-party
import falcon

# first-party
from falcon_provider_rate_limit.middleware import RateLimitMiddleware
from falcon_provider_rate_limit.utils import RedisRateLimitProvider

# redis server
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
global_rate_limit_control = {
    'enabled': False,
    'authenticated_limit': 0,
    'dos_limit': 0,
    'global_limit': True,
    'limit_window': 1,
    'unauthenticated_limit': 0,
}


class RedisResource:
    """Redis cache middleware testing resource."""

    rate_limit_control = {
        'enabled': True,
        'authenticated_limit': 0,
        'dos_limit': 0,
        'global_limit': True,
        'limit_window': 1,
        'unauthenticated_limit': 0,
    }

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """Support GET method."""
        key = req.get_param('key')
        resp.text = 'test'
        resp.text = f'{key}-worked'
        resp.status_code = falcon.HTTP_OK


# Provider using auth_key and client_key
redis_provider_1 = RedisRateLimitProvider(
    host=REDIS_HOST,
    port=REDIS_PORT,
    rate_limit_control=global_rate_limit_control,
    auth_key='user_id',
    client_key='client_key',
)
app_redis_1 = falcon.App(middleware=[RateLimitMiddleware(redis_provider_1)])
app_redis_1.add_route('/middleware', RedisResource())


# Provider using no client_key
redis_provider_2 = RedisRateLimitProvider(
    host=REDIS_HOST,
    port=REDIS_PORT,
    rate_limit_control=global_rate_limit_control,
    auth_key='is_authenticated',
    client_key=None,
)
app_redis_2 = falcon.App(middleware=[RateLimitMiddleware(redis_provider_2)])
app_redis_2.add_route('/middleware', RedisResource())


# Provider with no auth_key
redis_provider_3 = RedisRateLimitProvider(
    host=REDIS_HOST,
    port=REDIS_PORT,
    rate_limit_control=global_rate_limit_control,
    auth_key=None,
    client_key='client_key',
)
app_redis_3 = falcon.App(middleware=[RateLimitMiddleware(redis_provider_3)])
app_redis_3.add_route('/middleware', RedisResource())
