"""
User Management API Test Suite

Each test validates exactly ONE thing (atomic tests).
Uses UserManagementAPIService for all HTTP calls.

Naming convention:
    test_<endpoint>_<what_is_being_checked>
"""

import pytest
from services import UserManagementAPIService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def user_management_api(api_context):
    """Provide a UserManagementAPIService wired to the authenticated API context."""
    return UserManagementAPIService(api_context)


@pytest.fixture(scope="module")
def users_response(user_management_api):
    """Fetch users response once — shared by all user management tests."""
    return user_management_api.get_users()


# ---------------------------------------------------------------------------
# User Management API — one assertion per test
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestUserManagementAPI:
    """Validates the user management response schema."""

    @pytest.mark.smoke
    def test_users_returns_success(self, users_response):
        """The users endpoint should return success=True."""
        assert users_response["success"] is True

    @pytest.mark.smoke
    def test_users_tenant_is_string(self, users_response):
        """The tenant field must be a string."""
        assert isinstance(users_response["tenant"], str)

    @pytest.mark.smoke
    def test_users_total_is_integer(self, users_response):
        """The total field must be an integer."""
        assert isinstance(users_response["total"], int)

    @pytest.mark.regression
    def test_users_supports_last_login_at_is_boolean(self, users_response):
        """The supportsLastLoginAt field must be a boolean."""
        assert isinstance(users_response["supportsLastLoginAt"], bool)

    @pytest.mark.regression
    def test_users_user_removal_policy_is_string(self, users_response):
        """The userRemovalPolicy field must be a string."""
        assert isinstance(users_response["userRemovalPolicy"], str)

    @pytest.mark.smoke
    def test_users_list_is_list(self, users_response):
        """The users field must be a JSON array/list."""
        assert isinstance(users_response["users"], list)

    @pytest.mark.regression
    def test_first_user_has_email(self, users_response):
        """The first user must have an email field."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned — cannot validate schema."
        assert "email" in users[0]
        assert isinstance(users[0]["email"], str)

    @pytest.mark.regression
    def test_first_user_has_access_type(self, users_response):
        """The first user must have an accessType field."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned."
        assert "accessType" in users[0]
        assert isinstance(users[0]["accessType"], str)


    @pytest.mark.regression
    def test_first_user_has_role(self, users_response):
        """The first user must have a role field."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned."
        assert "role" in users[0]
        assert isinstance(users[0]["role"], str)

    @pytest.mark.regression
    def test_first_user_is_active_is_boolean(self, users_response):
        """The first user isActive field must be a boolean."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned."
        assert isinstance(users[0]["isActive"], bool)

    @pytest.mark.regression
    def test_first_user_has_is_protected(self, users_response):
        """The first user must have an isProtected field."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned."
        assert "isProtected" in users[0]
        assert isinstance(users[0]["isProtected"], bool)

    @pytest.mark.regression
    def test_first_user_has_is_system(self, users_response):
        """The first user must have an isSystem field."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned."
        assert "isSystem" in users[0]
        assert isinstance(users[0]["isSystem"], bool)

    @pytest.mark.regression
    def test_first_user_has_last_login_at(self, users_response):
        """The first user must have a lastLoginAt field."""
        users = users_response["users"]
        assert len(users) > 0, "No users returned."
        assert "lastLoginAt" in users[0]
        assert isinstance(users[0]["lastLoginAt"], str)

