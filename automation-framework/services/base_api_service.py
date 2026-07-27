"""
BaseAPIService — foundation for all API service wrappers.

Contains core Exception and base service definitions.
"""


class APIError(Exception):
    """Raised when an API endpoint returns an unexpected HTTP status."""

    def __init__(self, endpoint: str, status: int, expected: int = 200):
        self.endpoint = endpoint
        self.status = status
        self.expected = expected
        super().__init__(
            f"API {endpoint} returned status {status} (expected {expected})"
        )


class BaseAPIService:
    """Thin wrapper around the Playwright APIRequestContext for endpoints."""

    def __init__(self, api_context):
        self._ctx = api_context

    def _get(self, endpoint: str) -> dict | list:
        """Perform a GET request and return parsed JSON. Raises APIError on failure."""
        response = self._ctx.get(endpoint)
        if response.status != 200:
            raise APIError(endpoint, response.status)
        return response.json()
