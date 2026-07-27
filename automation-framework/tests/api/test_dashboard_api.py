"""
Dashboard API Test Suite

Each test validates exactly ONE thing (atomic tests).
Uses DashboardAPIService for all HTTP calls.

Naming convention:
    test_<endpoint>_<what_is_being_checked>
"""

import pytest
from services import DashboardAPIService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dashboard_api(api_context):
    """Provide a DashboardAPIService wired to the authenticated API context."""
    return DashboardAPIService(api_context)


@pytest.fixture(scope="module")
def token_response(dashboard_api):
    """Fetch verify-token response once — shared by all auth tests."""
    return dashboard_api.verify_token()


@pytest.fixture(scope="module")
def stats_response(dashboard_api):
    """Fetch stats response once — shared by all stats schema tests."""
    return dashboard_api.get_stats()


@pytest.fixture(scope="module")
def products_response(dashboard_api):
    """Fetch products list once — shared by all products tests."""
    return dashboard_api.get_products()


@pytest.fixture(scope="module")
def scenes_response(dashboard_api):
    """Fetch scenes response once — shared by all scenes tests."""
    return dashboard_api.get_scenes()


# ---------------------------------------------------------------------------
# Auth API — one assertion per test
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestAuthAPI:
    """Validates the authentication API response."""

    @pytest.mark.smoke
    def test_verify_token_returns_success(self, token_response):
        """The verify-token endpoint should return success=True."""
        assert token_response["success"] is True

    @pytest.mark.smoke
    def test_verify_token_contains_user_object(self, token_response):
        """The response must include a 'user' object."""
        assert "user" in token_response

    @pytest.mark.regression
    def test_verify_token_user_has_email(self, token_response):
        """The user object must contain an email field."""
        assert "email" in token_response["user"]

    @pytest.mark.regression
    def test_verify_token_user_has_access_type(self, token_response):
        """The user object must contain an accessType field."""
        assert "accessType" in token_response["user"]

    @pytest.mark.regression
    def test_verify_token_user_has_role(self, token_response):
        """The user object must contain a role field."""
        assert "role" in token_response["user"]

    @pytest.mark.regression
    def test_verify_token_user_has_tenant(self, token_response):
        """The user object must contain a tenant field."""
        assert "tenant" in token_response["user"]


# ---------------------------------------------------------------------------
# Stats API — one assertion per test
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestDashboardStatsAPI:
    """Validates the dashboard statistics response schema."""

    @pytest.mark.smoke
    def test_stats_models_is_integer(self, stats_response):
        """The 'models' field must be an integer."""
        assert isinstance(stats_response["models"], int)

    @pytest.mark.regression
    def test_stats_scenes_is_integer(self, stats_response):
        """The 'scenes' field must be an integer."""
        assert isinstance(stats_response["scenes"], int)

    @pytest.mark.smoke
    def test_stats_products_is_integer(self, stats_response):
        """The 'products' field must be an integer."""
        assert isinstance(stats_response["products"], int)

    @pytest.mark.regression
    def test_stats_shares_is_integer(self, stats_response):
        """The 'shares' field must be an integer."""
        assert isinstance(stats_response["shares"], int)

    @pytest.mark.regression
    def test_stats_total_sessions_is_integer(self, stats_response):
        """The 'totalSessions' field must be an integer."""
        assert isinstance(stats_response["totalSessions"], int)

    @pytest.mark.regression
    def test_stats_total_users_is_integer(self, stats_response):
        """The 'totalUsers' field must be an integer."""
        assert isinstance(stats_response["totalUsers"], int)

    @pytest.mark.regression
    def test_stats_revenue_is_string(self, stats_response):
        """The 'revenue' field must be a string."""
        assert isinstance(stats_response["revenue"], str)

    @pytest.mark.regression
    def test_stats_user_is_string(self, stats_response):
        """The 'user' field must be a string."""
        assert isinstance(stats_response["user"], str)

    @pytest.mark.regression
    def test_stats_tenant_is_string(self, stats_response):
        """The 'tenant' field must be a string."""
        assert isinstance(stats_response["tenant"], str)


@pytest.mark.api
class TestStatsVsProducts:
    """Cross-endpoint consistency checks."""

    @pytest.mark.regression
    def test_stats_products_matches_active_products_count(self, dashboard_api):
        """The products count in /stats must equal the filtered /products list length."""
        stats = dashboard_api.get_stats()
        active_count = dashboard_api.get_active_products_count()
        assert stats["products"] == active_count, (
            f"Stats reports {stats['products']} products but "
            f"/products has {active_count} active entries."
        )


# ---------------------------------------------------------------------------
# Products API — one assertion per test
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestProductsAPI:
    """Validates the products list endpoint."""

    @pytest.mark.smoke
    def test_products_returns_list(self, products_response):
        """The /products endpoint must return a JSON array."""
        assert isinstance(products_response, list)

    @pytest.mark.regression
    def test_first_product_has_id(self, products_response):
        """The first product must have an 'id' field."""
        assert len(products_response) > 0, "No products returned — cannot validate schema."
        assert "id" in products_response[0]

    @pytest.mark.regression
    def test_first_product_has_name(self, products_response):
        """The first product must have a 'name' field."""
        assert len(products_response) > 0, "No products returned."
        assert "name" in products_response[0]

    @pytest.mark.regression
    def test_first_product_has_type(self, products_response):
        """The first product must have a 'type' field."""
        assert len(products_response) > 0, "No products returned."
        assert "type" in products_response[0]

    @pytest.mark.regression
    def test_first_product_has_date(self, products_response):
        """The first product must have a 'date' field."""
        assert len(products_response) > 0, "No products returned."
        assert "date" in products_response[0]

    @pytest.mark.regression
    def test_first_product_has_status(self, products_response):
        """The first product must have a 'status' field."""
        assert len(products_response) > 0, "No products returned."
        assert "status" in products_response[0]

    @pytest.mark.regression
    def test_first_product_model_count_is_integer(self, products_response):
        """The 'modelCount' of the first product must be an integer."""
        assert len(products_response) > 0, "No products returned."
        assert isinstance(products_response[0]["modelCount"], int)

    @pytest.mark.regression
    def test_first_product_experience_count_is_integer(self, products_response):
        """The 'experienceCount' of the first product must be an integer."""
        assert len(products_response) > 0, "No products returned."
        assert isinstance(products_response[0]["experienceCount"], int)


# ---------------------------------------------------------------------------
# Scenes API — one assertion per test
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestScenesAPI:
    """Validates the scenes list endpoint."""

    @pytest.mark.smoke
    def test_scenes_response_has_scenes_key(self, scenes_response):
        """The /scenes response must contain a 'scenes' key."""
        assert "scenes" in scenes_response

    @pytest.mark.regression
    def test_scenes_is_a_list(self, scenes_response):
        """The 'scenes' value must be a JSON array."""
        assert isinstance(scenes_response["scenes"], list)

    @pytest.mark.regression
    def test_first_scene_has_id(self, scenes_response):
        """The first scene must have an 'id' field."""
        scenes = scenes_response["scenes"]
        assert len(scenes) > 0, "No scenes returned — cannot validate schema."
        assert "id" in scenes[0]

    @pytest.mark.regression
    def test_first_scene_has_name(self, scenes_response):
        """The first scene must have a 'name' field."""
        scenes = scenes_response["scenes"]
        assert len(scenes) > 0, "No scenes returned."
        assert "name" in scenes[0]

    @pytest.mark.regression
    def test_first_scene_has_display_title(self, scenes_response):
        """The first scene must have a 'displayTitle' field."""
        scenes = scenes_response["scenes"]
        assert len(scenes) > 0, "No scenes returned."
        assert "displayTitle" in scenes[0]

    @pytest.mark.regression
    def test_first_scene_has_product_id(self, scenes_response):
        """The first scene must have a 'productId' field."""
        scenes = scenes_response["scenes"]
        assert len(scenes) > 0, "No scenes returned."
        assert "productId" in scenes[0]

    @pytest.mark.regression
    def test_first_scene_has_status(self, scenes_response):
        """The first scene must have a 'status' field."""
        scenes = scenes_response["scenes"]
        assert len(scenes) > 0, "No scenes returned."
        assert "status" in scenes[0]
