"""
BrandingAPIService — wraps all branding and settings-related API calls.

Inherits from BaseAPIService. Raises APIError on non-200 responses.
"""

import allure
from services.base_api_service import BaseAPIService


class BrandingAPIService(BaseAPIService):
    """Thin wrapper around the Playwright APIRequestContext for settings and branding endpoints."""

    @allure.step("API — fetch branding settings")
    def get_settings(self) -> dict:
        """GET /api/settings → Retrieves tenant-specific platform settings."""
        return self._get("/api/settings")
