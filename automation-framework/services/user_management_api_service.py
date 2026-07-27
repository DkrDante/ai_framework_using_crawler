"""
UserManagementAPIService — wraps all user-management related API calls.

Inherits from BaseAPIService. Raises APIError on non-200 responses.
"""

import allure
from services.base_api_service import BaseAPIService


class UserManagementAPIService(BaseAPIService):
    """Thin wrapper around the Playwright APIRequestContext for User Management endpoints."""

    @allure.step("API — fetch all users")
    def get_users(self) -> dict:
        """GET /api/users → Retrieves all users associated with the current tenant."""
        return self._get("/api/users")
