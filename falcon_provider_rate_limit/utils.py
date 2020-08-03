# -*- coding: utf-8 -*-
"""Rate Limit utility."""
# standard library
import time
from typing import Optional, Union

# third-party
import falcon


class RateLimitProvider:
    """Base Rate Limit Provider Class.

    Args:
        rate_limit_control: A default rate limit control dict.
        auth_key: The falcon req.context attribute that contains the key that
            indicates the user is authenticated.
        client_key: The falcon resource property that contains the client key
            that will be used to rate limit client.
    """

    def __init__(
        self,
        rate_limit_control: Optional[dict] = None,
        auth_key: Optional[str] = None,
        client_key: Optional[str] = None,
    ):
        """Initialize class properties

        rate_limit_control::

        authenticated_limit (int): The maximum number of requests per hour for
            authenticated users. If not set there is no limit.
        dos_limit (int): A denial of service limit (hits per second per IP). If not set
            there is no limit.
        global_limit (bool): If True the limits apply globally and not per resource.
        limit_window (30): Limit time window in minutes.
        unauthenticated_limit (int): The maximum number of requests per hour for
            unauthenticated users. If not set there is no limit.

        .. code:: python

            class ApiResource:
                rate_limit_control = {
                    'enabled': True,
                    'authenticated_limit': 5000,
                    'dos_limit': 30,
                    'global_limit': True,
                    'limit_window': 30,
                    'unauthenticated_limit': 2500,
                }
                def on_get(self, req, resp):
                    ...
        """
        self._global_rate_limit_control = {
            'enabled': True,
            'authenticated_limit': None,
            'dos_limit': None,
            'global_limit': True,
            'limit_window': 30,  # limit in minutes
            'unauthenticated_limit': None,
        }
        if rate_limit_control is not None:
            # update global rate limit control with user provided settings
            self._global_rate_limit_control.update(rate_limit_control)
        self._rate_limit_control = dict(self._global_rate_limit_control)
        self.auth_key = auth_key  # the req.context attribute that indicates authentication
        self._client_key = client_key  # the req.context attribute to use to track the client

    def authenticated(self, req: falcon.Request) -> bool:
        """Return True if client is authenticated, else False.

        Authenticated test is simply whether the req.context object has the auth_key attribute and
        that property is not None, False or an empty string. Typically this would be a check for
        username or user_id which would only exist for an authenticated user. If a custom
        authentication module is use a property of "is_authenticated" with a boolen value could
        be used.

        Args:
            resource (object): Resource object to which the request was routed.

        Returns:
            bool: True if client is authenticated, else False.
        """
        try:
            if getattr(req.context, self.auth_key):
                return True
        except (AttributeError, TypeError):
            pass
        return False

    @property
    def authenticated_limit(self) -> int:
        """Return rate limit control authenticated_limit value."""
        return self._rate_limit_control.get('authenticated_limit') or 0

    def client_count(self, client_key):
        """Return the current client count."""
        raise NotImplementedError(  # pragma: no cover
            'This method must be implemented in child class.'
        )

    def client_count_incr(self, client_key):
        """Increment client count."""
        raise NotImplementedError(  # pragma: no cover
            'This method must be implemented in child class.'
        )

    def client_count_set(self, client_key):
        """Set client count and expiration."""
        raise NotImplementedError(  # pragma: no cover
            'This method must be implemented in child class.'
        )

    def client_key(
        self, req: falcon.Request, resource: object  # pylint: disable=unused-argument
    ) -> str:
        """Return the client key for this request.

        Args:
            req: Request object that will be passed to the routed responder.
            resource: Resource object to which the request was routed.

        Returns:
            str: The key used to identify the client.
        """
        try:
            client_key: str = req.access_route[0] or req.remote_addr
        except IndexError:  # pragma: no cover
            client_key: str = req.remote_addr

        if self._client_key:
            # use the client key provided by upstream application
            if hasattr(req.context, self._client_key) and getattr(req.context, self._client_key):
                client_key = str(getattr(req.context, self._client_key))

        # add path if limit are *not* global
        if not self.global_limit:
            client_key = f'{client_key}{req.path}'

        return client_key

    def client_key_expires(self, client_key):
        """Return key expiration in seconds."""
        raise NotImplementedError(  # pragma: no cover
            'This method must be implemented in child class.'
        )

    @property
    def enabled(self) -> bool:
        """Return rate limit control enabled value."""
        enabled = self._rate_limit_control.get('enabled') or False
        if (
            enabled is True
            and self.dos_limit == 0
            and self.authenticated_limit == 0
            and self.unauthenticated_limit == 0
        ):
            enabled = False
        return enabled

    def dos_count(self, client_key):
        """Return dos key from kv store."""
        raise NotImplementedError(  # pragma: no cover
            'This method must be implemented in child class.'
        )

    def dos_count_incr(self, client_key):
        """Return dos key from kv store."""
        raise NotImplementedError(  # pragma: no cover
            'This method must be implemented in child class.'
        )

    @property
    def dos_limit(self) -> int:
        """Return rate limit control dos_limit value."""
        return self._rate_limit_control.get('dos_limit') or 0

    def dos_limit_reached(self, client_key) -> dict:
        """Return True if DOS rate limit reached, else False.

        Args:
            client_key (str): The key for the current client.

        Returns:
            dict: The current rate limit values.
        """
        # get current DOS count
        dos_count = self.dos_count(client_key)
        dlr = {
            'rate_limit_reached': False,
            'rate_limit_remaining': self.dos_limit - dos_count,
            'rate_limit_reset': int(time.time()) + 1,
        }

        # check DOS limit
        if dos_count + 1 > self.dos_limit:
            dlr['rate_limit_reached'] = True
        else:
            # increment count
            self.dos_count_incr(client_key)
            dlr['rate_limit_remaining'] -= 1
        return dlr

    @property
    def global_limit(self) -> bool:
        """Return rate limit control global_limit value."""
        return self._rate_limit_control.get('global_limit', True)

    def limit(self, req: falcon.Request) -> int:
        """Return the rate limit for the current client.

        Args:
            req: The Falcon Request object.

        Returns:
            int: The rate limit for the current client.
        """
        # determine the limit to use
        limit = self.unauthenticated_limit
        if self.authenticated(req):
            limit = self.authenticated_limit
        return limit

    @property
    def limit_window(self) -> int:
        """Return rate limit control limit_window value."""
        return int(self._rate_limit_control.get('limit_window')) or 15

    def rate_limit_control(self, rate_limit_control: Optional[dict] = None) -> dict:
        """Return rate limit control settings.

        Args:
            rate_limit_control: The rate limit control settings.

        Returns:
            dict: Updated rate limit control settings.
        """
        rate_limit_control = rate_limit_control or {}
        self._rate_limit_control = dict(self._global_rate_limit_control)
        self._rate_limit_control.update(rate_limit_control)
        return self._rate_limit_control

    def rate_limit_reached(self, client_key: str, limit: int) -> dict:
        """Return rate limit value.

        Args:
            client_key: The key for the current client.
            limit: The rate limit for the current client.

        Returns:
            dict: A dict of rate limit values.
        """
        client_count = self.client_count(client_key)
        rlr = {
            'rate_limit_reached': False,
            'rate_limit_remaining': limit - client_count,
            'rate_limit_reset': self.client_key_expires(client_key),
            'retry_after': int(self.client_key_expires(client_key) - time.time()),
        }
        if client_count == 0:
            self.client_count_set(client_key)
            rlr['rate_limit_remaining'] -= 1
        elif self.client_count(client_key) + 1 > limit:
            # limit reached
            rlr['rate_limit_reached'] = True
        else:
            # increment count
            self.client_count_incr(client_key)
            rlr['rate_limit_remaining'] -= 1
        return rlr

    @property
    def unauthenticated_limit(self) -> int:
        """Return rate limit control unauthenticated_limit value."""
        return self._rate_limit_control.get('unauthenticated_limit') or 0


class MemcacheRateLimitProvider(RateLimitProvider):
    """Memcache Provider Class.

    Args:
        rate_limit_control: A default rate limit control dict.
        auth_key: The falcon resource property that contains the key that
            indicates the user is authenticated.
        client_key: The falcon resource property that contains the client key
            that will be used to rate limit client.
        server: The server settings for memcache, can either be a (host, port) tuple for
            a TCP connection or a string containing the path to a UNIX domain socket.
        max_pool_size (int): The maximum pool size for Pool Client.
        connect_timeout (int, kwargs): Used to set socket timeout values. By default, timeouts
            are disabled.
        deserializer (function or method, kwargs): The deserialization function takes three
            parameters, a key, value and flags and returns the deserialized value.
        no_delay (book, kwargs): Sets TCP_NODELAY socket option.
        serializer (function or method, kwargs): The serialization function takes two arguments,
            a key and a value, and returns a tuple of two elements, the serialized value, and an
            integer in the range 0-65535 (the “flags”).
        timeout (int, kwargs): Used to set socket timeout values. By default, timeouts are
            disabled.
    """

    def __init__(
        self,
        rate_limit_control: Optional[dict] = None,
        auth_key: Optional[str] = None,
        client_key: Optional[str] = None,
        server: Optional[Union[str, tuple]] = None,
        **kwargs,
    ):
        """Initialize class properties."""
        super(MemcacheRateLimitProvider, self).__init__(rate_limit_control, auth_key, client_key)

        try:
            # third-party
            from falcon_provider_memcache.utils import (  # pylint: disable=import-outside-toplevel
                MemcacheClient,
            )
        except ImportError:  # pragma: no cover
            print(
                'MemcacheProvider requires falcon-provider-memcache to be installed '
                'try "pip install falcon-provider-rate-limit[memcache]".'
            )
            raise

        self.memcache_client = MemcacheClient(server, **kwargs).client

    def client_count(self, client_key: str) -> int:
        """Return True if client key exist in DB.

        Args:
            client_key: The key identifying the current client.

        Returns:
            int: The current client count
        """
        client_count = self.memcache_client.get(client_key) or 0
        return int(client_count)

    def client_count_incr(self, client_key: str) -> None:
        """Increment client count.

        Args:
            client_key: The key identifying the current client.
        """
        self.memcache_client.incr(client_key, 1)

    def client_count_set(self, client_key: str) -> None:
        """Set client count and expiration (minutes to seconds).

        Args:
            client_key (str): The key identifying the current client.
        """
        self.memcache_client.set(key=client_key, value=1, expire=(self.limit_window * 60))

        # memcached does allow retrieval of expiration time. the value is stored in a separate key.
        expiration_time_key = f'{client_key}-expires'
        expiration_time = int(time.time()) + (self.limit_window * 60)
        self.memcache_client.set(
            key=expiration_time_key, value=expiration_time, expire=(self.limit_window * 60)
        )

    def client_key_expires(self, client_key: str) -> int:
        """Return key expiration in seconds.

        Because memcached doesn't support retrieving the expiration time the expires timestamp is
        stored in a separate key.

        Args:
            client_key: The key identifying the current client.

        Returns:
            int: The key expiration epoch timestamp.
        """
        expiration_time_key = f'{client_key}-expires'
        expires = self.memcache_client.get(expiration_time_key) or 0
        return int(expires)

    def dos_count(self, client_key: str) -> int:
        """Return dos key from kv store.

        Args:
            client_key: The key identifying the current client.

        Returns:
            int: The current DOS count.
        """
        ts = int(time.time())
        dos_key = f'{client_key}:{ts}'
        dos_count = self.memcache_client.get(dos_key) or 0
        return int(dos_count)

    def dos_count_incr(self, client_key: str) -> None:
        """Increment the DOS key from kv store.

        Args:
            client_key: The key identifying the current client.
        """
        ts = int(time.time())
        dos_key = f'{client_key}:{ts}'

        if self.memcache_client.get(dos_key) is None:
            self.memcache_client.set(key=dos_key, value=0, expire=1)
        self.memcache_client.incr(dos_key, 1)


class RedisRateLimitProvider(RateLimitProvider):
    """Redis Rate Limit Provider Class.

    Args:
        rate_limit_control: A default rate limit control dict.
        auth_key: The falcon resource property that contains the key that
            indicates the user is authenticated.
        client_key: The falcon resource property that contains the client key
            that will be used to rate limit client.
        host: The REDIS host.
        port: The REDIS port.
        db: The REDIS db.
        blocking_pool: Use BlockingConnectionPool instead of ConnectionPool.
        errors (str, kwargs): The REDIS errors policy (e.g. strict).
        max_connections (int, kwargs): The maximum number of connections to REDIS.
        password (str, kwargs): The REDIS password.
        socket_timeout (int, kwargs): The REDIS socket timeout.
        timeout (int, kwargs): The REDIS Blocking Connection Pool timeout value.
    """

    def __init__(
        self,
        rate_limit_control: Optional[dict] = None,
        auth_key: Optional[str] = None,
        client_key: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        blocking_pool: Optional[bool] = False,
        **kwargs,
    ):
        """Initialize class properties."""
        super(RedisRateLimitProvider, self).__init__(rate_limit_control, auth_key, client_key)
        try:
            # third-party
            from falcon_provider_redis.utils import (  # pylint: disable=import-outside-toplevel
                RedisClient,
            )
        except ImportError:  # pragma: no cover
            print(
                'RedisRateLimitProvider requires falcon-provider-redis to be installed '
                'try "pip install falcon-provider-rate-limit[redis]".'
            )
            raise

        self.redis_client = RedisClient(host, port, db, blocking_pool, **kwargs).client

    def client_count(self, client_key: str) -> int:
        """Set client count and expiration (minutes to seconds).

        Args:
            client_key: The key identifying the current client.
        """
        client_count = self.redis_client.get(client_key) or 0
        return int(client_count)

    def client_count_incr(self, client_key: str) -> None:
        """Increment client count.

        Args:
            client_key: The key identifying the current client.
        """
        self.redis_client.incrby(client_key, 1)

    def client_count_set(self, client_key: str) -> None:
        """Set client count and expiration (minutes to seconds).

        Args:
            client_key: The key identifying the current client.
        """
        self.redis_client.setex(client_key, (self.limit_window * 60), 1)

    def client_key_expires(self, client_key: str) -> int:
        """Return key expiration in seconds.

        Args:
            client_key: The key identifying the current client.

        Returns:
            int: The key expiration epoch timestamp.
        """
        expires = self.redis_client.ttl(client_key)
        if expires in [-1, -2]:
            expires = 0
        return int(time.time()) + expires

    def dos_count(self, client_key: str) -> int:
        """Return dos key from kv store.

        Args:
            client_key: The key identifying the current client.

        Returns:
            int: The current DOS count.
        """
        ts = int(time.time())
        dos_key = f'{client_key}:{ts}'
        dos_count = self.redis_client.get(dos_key) or 0
        return int(dos_count)

    def dos_count_incr(self, client_key: str) -> None:
        """Return dos key from kv store.

        Args:
            client_key: The key identifying the current client.
        """
        ts = int(time.time())
        dos_key = f'{client_key}:{ts}'
        self.redis_client.incrby(dos_key, 1)
        self.redis_client.expire(dos_key, 5)
