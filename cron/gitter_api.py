
import http
import json
import urllib.parse
from datetime import datetime, timezone


class GitterException(Exception):

    """Base exception for this library."""


class HTTPException(GitterException):

    """A general exception to represent HTTP responses."""

    def __init__(self, status_code, *args):
        self.status_code = status_code
        if args:
            super().__init__(*args)
        else:
            super().__init__(status_code.phrase)


class RedirectionException(HTTPException):

    """Exception for 3XX HTTP responses."""


class BadRequest(HTTPException):
    """The request is invalid.

    Used for 4XX HTTP errors.
    """


class RateLimitExceeded(BadRequest):

    """Request rejected due to the rate limit being exceeded."""

    def __init__(self, rate_limit, *args):
        self.rate_limit = rate_limit

        if not args:
            super().__init__(http.HTTPStatus.FORBIDDEN,
                             "rate limit exceeded")
        else:
            super().__init__(http.HTTPStatus.FORBIDDEN, *args)


class InvalidField(BadRequest):

    """A field in the request is invalid.

    Represented by a 422 HTTP Response. Details of what fields were
    invalid are stored in the errors attribute.
    """

    def __init__(self, errors, *args):
        """Store the error details."""
        self.errors = errors
        super().__init__(http.HTTPStatus.UNPROCESSABLE_ENTITY, *args)


class GitterBroken(HTTPException):

    """Exception for 5XX HTTP responses."""

class RateLimit():
    def __init__(self, *, limit, remaining,
                 reset_epoch):
        """Instantiate a RateLimit object.

        The reset_epoch argument should be in seconds since the UTC epoch.
        """

        self.limit = limit
        self.remaining = remaining
        self.reset_datetime = datetime.fromtimestamp(reset_epoch/1000,
                                                              timezone.utc)

    def __bool__(self):
        """True if requests are remaining or the reset datetime has passed."""
        if self.remaining > 0:
            return True
        else:
            now = datetime.now(timezone.utc)
            return now > self.reset_datetime

    def __str__(self):
        """Provide all details in a reasonable format."""
        return f"< {self.remaining:,}/{self.limit:,} until {self.reset_datetime} >"

    @classmethod
    def from_http(cls, headers):
        """Gather rate limit information from HTTP headers.

        The mapping providing the headers is expected to support lowercase
        keys.  Returns ``None`` if ratelimit info is not found in the headers.
        """
        try:
            limit = int(headers["x-ratelimit-limit"])
            remaining = int(headers["x-ratelimit-remaining"])
            reset_epoch = float(headers["x-ratelimit-reset"])
        except KeyError:
            return None
        else:
            return cls(limit=limit, remaining=remaining,
                       reset_epoch=reset_epoch)



class GitterAPI():

    def __init__(self, session, requester, oauth_token, cache=None):

        self.domain = "https://api.gitter.im"
        self._session = session
        self.requester = requester
        self.oauth_token = oauth_token
        self._cache = cache
        self.rate_limit = None

    async def _request(self, method, url, headers,
                       body=b''):
        """Make an HTTP request."""
        async with self._session.request(method, url, headers=headers,
                                             data=body) as response:
            return response.status, response.headers, await response.read()


    def create_request_headers(self):
        """Create the request headers"""
        return {"user-agent": self.requester,
                   "authorization": f"bearer {self.oauth_token}",
                   "accept": "application/json"}


    def format_url(self, url):
        return urllib.parse.urljoin(self.domain, url)


    async def _make_request(self, method, url,
                            data,
                            ):
        """Construct and make an HTTP request."""
        filled_url = self.format_url(url)
        request_headers = self.create_request_headers()
        cached = cacheable = False
        # Can't use None as a "no body" sentinel as it's a legitimate JSON type.
        if data == b"":
            body = b""
            request_headers["content-length"] = "0"
            if method == "GET" and self._cache is not None:
                cacheable = True
                try:
                    etag, last_modified, data = self._cache[filled_url]
                    cached = True
                except KeyError:
                    pass
                else:
                    if etag is not None:
                        request_headers["if-none-match"] = etag
                    if last_modified is not None:
                        request_headers["if-modified-since"] = last_modified
        else:
            charset = "utf-8"
            body = json.dumps(data).encode(charset)
            request_headers['content-type'] = f"application/json; charset={charset}"
            request_headers['content-length'] = str(len(body))
        if self.rate_limit is not None:
            self.rate_limit.remaining -= 1
        response = await self._request(method, filled_url, request_headers, body)
        if not (response[0] == 304 and cached):
            data, self.rate_limit = self.decipher_response(*response)
            has_cache_details = ("etag" in response[1]
                                 or "last-modified" in response[1])
            if self._cache is not None and cacheable and has_cache_details:
                etag = response[1].get("etag")
                last_modified = response[1].get("last-modified")
                self._cache[filled_url] = etag, last_modified, data
        return data


    def decipher_response(self, status_code, headers,
                          body):
        """Decipher an HTTP response for a GitHub API request.

        The mapping providing the headers is expected to support lowercase keys.

        The parameters of this function correspond to the three main parts
        of an HTTP response: the status code, headers, and body. Assuming
        no errors which lead to an exception being raised, a 3-item tuple
        is returned. The first item is the decoded body (typically a JSON
        object, but possibly None or a string depending on the content
        type of the body). The second item is an instance of RateLimit
        based on what the response specified.

        The last item of the tuple is the URL where to request the next
        part of results. If there are no more results then None is
        returned. Do be aware that the URL can be a URI template and so
        may need to be expanded.

        If the status code is anything other than 200, 201, or 204, then
        an HTTPException is raised.
        """

        data = json.loads(body.decode("utf-8"))
        if status_code in {200, 201, 204}:
            return data, RateLimit.from_http(headers)
        else:
            try:
                message = data["message"]
            except (TypeError, KeyError):
                message = None
            exc_type = None
            if status_code >= 500:
                exc_type = GitterBroken
            elif status_code >= 400:
                exc_type = BadRequest
                if status_code == 403:
                    rate_limit = RateLimit.from_http(headers)
                    if rate_limit and not rate_limit.remaining:
                        raise RateLimitExceeded(rate_limit, message)
                elif status_code == 422:
                    errors = data.get("errors", None)
                    if errors:
                        fields = ", ".join(repr(e["field"]) for e in errors)
                        message = f"{message} for {fields}"
                    else:
                        message = data["message"]
                    raise InvalidField(errors, message)
            elif status_code >= 300:
                exc_type = RedirectionException
            else:
                exc_type = HTTPException
            status_code_enum = http.HTTPStatus(status_code)
            args = None
            if message:
                args = status_code_enum, message
            else:
                args = status_code_enum,
            raise exc_type(*args)


    async def getitem(self, url: str):
        """Send a GET request for a single item to the specified endpoint."""

        data = await self._make_request("GET", url, b"")
        return data

    async def post(self, url: str, data):
        data = await self._make_request("POST", url, data)
        return data

    async def patch(self, url: str, data):
        data = await self._make_request("PATCH", url, data)
        return data

    async def put(self, url: str, data):
        data = await self._make_request("PUT", url, data)
        return data

    async def delete(self, url: str):
        data = await self._make_request("DELETE", url, data=b"")
        return data
