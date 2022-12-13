==========================
falcon-provider-rate-limit
==========================

|build| |coverage| |code-style| |pre-commit|

A falcon middleware rate limit provider using Memcached or Redis.

------------
Installation
------------

Install the extension via pip. For memcache provider use ``[memcache]`` and for redis provider use ``[redis]``.

.. code:: bash

    > pip install falcon-provider-rate-limit[memcache]
    > pip install falcon-provider-rate-limit[redis]

--------
Overview
--------

This package provides a middleware rate limit component for the falcon framework. This component uses either the **falcon-provider-memcache** or **falcon-provider-redis** package depending on install options. These memcache and redis provider modules use singletons to enable sharing the backend connections.

The default client_key is the request ``access_route`` or ``remote_addr`` provided by the Falcon Request object (the IP Address of the client). This can be overwritten with a key defined in the resource object (e.g. user_key value).  Using a user_key value allows rate limits to be applied for a user regardless of their IP address, however it requires the user to be logged in to use the rate limit value.

The auth_key (authenticated key) is an optional property in the Falcon resource object that if exists indicates that a user is authenticated to the service.  If this value exists and is not None the ``authenticated_limit`` will be used for the current client.  If auth_key is not defined or the property does not exist then the ``unauthenticated_limit`` will be used instead.

For rate limit enabled API endpoints the middleware will add the following headers:

* X-RateLimit-Limit - The limit for the current client.
* X-RateLimit-Remaining - The remaining limit count.
* X-RateLimit-Reset - The time the limit resets (epoch seconds).

--------
Requires
--------
* falcon - https://pypi.org/project/falcon/

Extra Requires
--------------
* falcon_provider_memcache - https://github.com/bcsummers/falcon-provider-memcache
* falcon_provider_redis - https://github.com/bcsummers/falcon-provider-redis

------------------
Rate Limit Control
------------------

The rate_limit_control dictionary defines the rate limit behavior. The rate limit control configuration can be globally defined when creating the rate limit provider or in each API resource. Global settings will be overwritten by resource settings.

+-----------------------+-----------+--------------------------------------------------------------+
| Control               | Default   | Description                                                  |
+=======================+===========+==============================================================+
| enabled               | False     | Set to True to enable rate limit.                            |
+-----------------------+-----------+--------------------------------------------------------------+
| authenticated_limit   | None      | The number of request that can be made by an authenticated   |
|                       |           | user.                                                        |
+-----------------------+-----------+--------------------------------------------------------------+
| dos_limit             | None      | The number of request any client can make in 1 second.       |
+-----------------------+-----------+--------------------------------------------------------------+
| global_limit          | True      | All limits apply globally when True.  If set to False the    |
|                       |           | limits apply per resource.                                   |
+-----------------------+-----------+--------------------------------------------------------------+
| limit_window          | 30        | The reset window in minutes. All hits will be reset after    |
|                       |           | the provided number of minutes starting from when the first  |
|                       |           | request was made.                                            |
+-----------------------+-----------+--------------------------------------------------------------+
| unauthenticated_limit | None      | The number of request that can be made by an unauthenticated |
|                       |           | user.                                                        |
+-----------------------+-----------+--------------------------------------------------------------+

.. code:: python

    rate_limit_control = {
        'enabled': True,
        'authenticated_limit': 5000,
        'dos_limit': 30,
        'global_limit': True,
        'limit_window': 30,
        'unauthenticated_limit': 2500,
    }

--------
Memcache
--------

.. code:: python

    import os
    import falcon
    from falcon_provider_rate_limit.middleware import RateLimitMiddleware
    from falcon_provider_rate_limit.utils import MemcacheRateLimitProvider

    # Memcached
    MEMCACHE_HOST = os.getenv('MEMCACHE_HOST', 'localhost')
    MEMCACHE_PORT = int(os.getenv('MEMCACHE_PORT', '11211'))

    class MemcacheResource(object):
        """Memcache middleware rate limit resource."""

        rate_limit_control = {
            'enabled': True,
            'authenticated_limit': 1000,
            'dos_limit': 50,
            'global_limit': True,
            'limit_window': 60,
            'unauthenticated_limit': 500,
        }

        def on_get(self, req, resp):
            """Support GET method."""
            key = req.get_param('key')
            resp.text = f'{key}-worked'
            resp.status_code = falcon.HTTP_OK

    rate_limit_provider = MemcacheRateLimitProvider(
        server=(MEMCACHE_HOST, MEMCACHE_PORT),
        auth_key=None,
        client_key=None,
    )

    app = falcon.App(middleware=[RateLimitMiddleware(rate_limit_provider)])
    app.add_route('/middleware', MemcacheResource())

-----
Redis
-----

.. code:: python

    import os

    import falcon
    import redis

    from falcon_provider_rate_limit.middleware import RateLimitMiddleware
    from falcon_provider_rate_limit.utils import RedisRateLimitProvider

    # redis server
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))


    class RedisResource(object):
        """Redis cache middleware testing resource."""

        rate_limit_control = {
            'enabled': True,
            'authenticated_limit': 1000,
            'dos_limit': 50,
            'global_limit': True,
            'limit_window': 60,
            'unauthenticated_limit': 500,
        }

        def on_get(self, req, resp):
            """Support GET method."""
            key = req.get_param('key')
            resp.text = f'{key}-worked'
            resp.status_code = falcon.HTTP_OK

    rate_limit_provider = RedisRateLimitProvider(
        host=REDIS_HOST,
        port=REDIS_PORT,
        auth_key=None,
        client_key=None,
    )

    app = falcon.App(middleware=[RateLimitMiddleware(rate_limit_provider)])
    app.add_route('/middleware', RedisResource())

-----------
Development
-----------

Installation
------------

After cloning the repository, all development requirements can be installed via pip. For linting and code consistency the pre-commit hooks should be installed.

.. code:: bash

    > poetry install --with dev --all-extras
    > pre-commit install

Testing
-------

Testing requires that Memcache and Redis be installed and running.

For Redis the default host is localhost and the default port is 6379. These values can be overwritten by using the REDIS_HOST and REDIS_PORT environment variables.

For Memcache the default host is localhost and the default port is 11211. These values can be overwritten by using the MEMCACHE_HOST and MEMCACHE_PORT environment variables.

.. code:: bash

    > poetry install --with dev,test --all-extras
    > pytest --cov=falcon_provider_rate_limit --cov-report=term-missing tests/

.. |build| image:: https://github.com/bcsummers/falcon-provider-rate-limit/workflows/build/badge.svg
    :target: https://github.com/bcsummers/falcon-provider-rate-limit/actions

.. |coverage| image:: https://codecov.io/gh/bcsummers/falcon-provider-rate-limit/branch/master/graph/badge.svg?token=2j0dOwnJQp
    :target: https://codecov.io/gh/bcsummers/falcon-provider-rate-limit

.. |code-style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/python/black

.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
