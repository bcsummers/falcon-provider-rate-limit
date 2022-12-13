"""Falcon rate limit provider middleware module."""
# third-party
import falcon


class RateLimitMiddleware:
    """Rate limit middleware module.

    Args:
        provider (RateLimitProvider): An instance of rate limit provider (memcache or Redis).
    """

    def __init__(self, provider: object):
        """Initialize class properties."""
        self.provider = provider

    def _testing(self, req) -> None:
        """Update req context with values for testing."""
        if hasattr(self, 'user_id'):
            # inject a test user_id for pytest monkeypatch
            req.context.user_id = self.user_id  # pylint: disable=no-member

        if hasattr(self, 'client_key'):
            # inject a test client_key for pytest monkeypatch
            req.context.client_key = self.client_key  # pylint: disable=no-member

    def process_resource(  # pylint: disable=unused-argument
        self,
        req: falcon.Request,
        resp: falcon.Response,
        resource: object,
        params: dict,
    ) -> None:
        """Process the request after routing and provide rate limit service."""
        # for pytest testing
        self._testing(req)

        # update the rate limit control for the current resource
        rate_limit_control = {}
        if hasattr(resource, 'rate_limit_control') and isinstance(
            resource.rate_limit_control, dict
        ):
            rate_limit_control: dict = resource.rate_limit_control

        # update rate limit control
        self.provider.rate_limit_control(rate_limit_control)

        if not self.provider.enabled:
            return

        # get the client key
        client_key: str = self.provider.client_key(req, resource)

        # check for DOS limit set (0 == unlimited)
        if self.provider.dos_limit != 0:
            dos_data = self.provider.dos_limit_reached(client_key)
            resp.context['rate_limit'] = self.provider.dos_limit
            resp.context['rate_limit_reached'] = dos_data.get('rate_limit_reached')
            resp.context['rate_limit_remaining'] = dos_data.get('rate_limit_remaining')
            resp.context['rate_limit_reset'] = dos_data.get('rate_limit_reset')
            if resp.context.get('rate_limit_reached') is True:
                resp.context[
                    'rate_limit_description'
                ] = f'Client exceeded rate limit of {self.provider.dos_limit} requests per seconds.'
                resp.complete = True  # signal short-circuit for response processing

        # if DOS limit not reached and limit set (0 == unlimited) then check rate limit
        limit = self.provider.limit(req)
        if not resp.context.get('rate_limit_reached') and limit != 0:
            rl_data = self.provider.rate_limit_reached(client_key, limit)
            resp.context['rate_limit'] = limit
            resp.context['rate_limit_reached'] = rl_data.get('rate_limit_reached')
            resp.context['rate_limit_remaining'] = rl_data.get('rate_limit_remaining')
            resp.context['rate_limit_reset'] = rl_data.get('rate_limit_reset')
            resp.context['retry_after'] = rl_data.get('retry_after')
            if resp.context.get('rate_limit_reached') is True:
                resp.context['rate_limit_description'] = (
                    f'Client exceeded rate limit of {limit} requests per '
                    f'{self.provider.limit_window} minutes.'
                )
                resp.complete = True  # signal short-circuit for response processing

    def process_response(  # pylint: disable=unused-argument
        self, req: falcon.Request, resp: falcon.Response, resource: object, req_succeeded: bool
    ) -> None:
        """Handle rate limit for provided resources."""
        if not self.provider.enabled:
            return

        if self.provider.enabled:
            if resp.context.get('rate_limit'):
                # rate limit is on, set headers
                resp.set_header('X-RateLimit-Limit', resp.context.get('rate_limit'))
                resp.set_header('X-RateLimit-Remaining', resp.context.get('rate_limit_remaining'))
                resp.set_header('X-RateLimit-Reset', resp.context.get('rate_limit_reset'))

            if resp.context.get('rate_limit_reached') is True:
                # https://tools.ietf.org/html/rfc6585#section-4
                resp.set_header('Retry-After', resp.context.get('retry_after'))
                raise falcon.HTTPTooManyRequests(
                    title='To Many Request', description=resp.context.get('rate_limit_description')
                )
