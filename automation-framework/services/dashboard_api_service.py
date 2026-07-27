"""
DashboardAPIService — wraps all dashboard-related API calls.

Inherits from BaseAPIService. Raises APIError on non-200 responses.
"""

import allure
from services.base_api_service import BaseAPIService


class DashboardAPIService(BaseAPIService):
    """Thin wrapper around the Playwright APIRequestContext for dashboard endpoints."""

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @allure.step("API — verify auth token")
    def verify_token(self) -> dict:
        """GET /api/auth/verify-token → full response JSON."""
        return self._get("api/auth/verify-token")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @allure.step("API — fetch dashboard stats")
    def get_stats(self) -> dict:
        """GET /api/stats → full response JSON."""
        return self._get("/api/stats")

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    @allure.step("API — fetch products list")
    def get_products(self) -> list[dict]:
        """GET /api/products → list of product dicts."""
        return self._get("/api/products")

    @allure.step("API — count active (non-archived) products")
    def get_active_products_count(self) -> int:
        """Return the number of products whose status ≠ 'archived'."""
        products = self.get_products()
        return len([p for p in products if p.get("status") != "archived"])

    @allure.step("API — get all products")
    def get_active_products(self) -> list[dict]:
        """Return the number of products whose status ≠ 'archived'."""
        products = self.get_products()
        products = [p for p in products if p.get("status") != "archived"]
        return products

    # ------------------------------------------------------------------
    # Scenes / Experiences
    # ------------------------------------------------------------------

    @allure.step("API — fetch scenes list")
    def get_scenes(self) -> dict:
        """GET /api/scenes → full response JSON (contains a 'scenes' key)."""
        return self._get("/api/scenes")

    @allure.step("API — get all active experiences")
    def get_active_experiences(self) -> list[dict]:
        """Return active experiences whose status ≠ 'archived'."""
        scenes_data = self.get_scenes()
        scenes = scenes_data.get("scenes", [])
        return [s for s in scenes if s.get("status") != "archived"]

    @allure.step("API — count active (non-archived) experiences")
    def get_active_experiences_count(self) -> int:
        """Return the number of active experiences whose status ≠ 'archived'."""
        return len(self.get_active_experiences())
