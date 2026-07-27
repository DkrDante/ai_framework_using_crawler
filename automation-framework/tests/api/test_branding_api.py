"""
Branding API Test Suite

Uses BrandingAPIService for all settings and branding configuration validation.
Combined test cases to reduce overall test count while maintaining extensive coverage.
"""

import pytest
from services import BrandingAPIService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def branding_api(api_context):
    """Provide a BrandingAPIService wired to the authenticated API context."""
    return BrandingAPIService(api_context)


@pytest.fixture(scope="module")
def settings_response(branding_api):
    """Fetch settings once — shared by all branding API tests."""
    return branding_api.get_settings()


# ---------------------------------------------------------------------------
# Branding API Tests
# ---------------------------------------------------------------------------

@pytest.mark.api
class TestBrandingAPI:
    """Validates the tenant branding and platform configuration response schema."""

    @pytest.mark.smoke
    def test_settings_response_success_and_metadata(self, settings_response):
        """Verify the API responds successfully and contains core metadata."""
        assert settings_response["success"] is True
        assert isinstance(settings_response["tenant"], str)
        assert isinstance(settings_response["settings"], dict)

    @pytest.mark.regression
    def test_settings_branding_fields(self, settings_response):
        """Verify the primary branding configuration and metadata fields are valid."""
        settings = settings_response["settings"]

        # Validate required companyColor
        assert "companyColor" in settings
        assert isinstance(settings["companyColor"], str)
        assert settings["companyColor"].startswith("#")

        # Validate nullable companyLogo
        assert "companyLogo" in settings
        assert settings["companyLogo"] is None or isinstance(settings["companyLogo"], str)

        # Validate optional companyName if present
        if "companyName" in settings:
            assert isinstance(settings["companyName"], str)

        # Validate optional timestamps if present
        if "createdAt" in settings:
            assert isinstance(settings["createdAt"], str)
        if "updatedAt" in settings:
            assert isinstance(settings["updatedAt"], str)

    @pytest.mark.regression
    def test_settings_feature_flags(self, settings_response):
        """Verify the features object structure and all key feature flag types."""
        settings = settings_response["settings"]
        assert "features" in settings
        assert isinstance(settings["features"], dict)

        features = settings["features"]
        expected_flags = [
            "analytics",
            "sharing",
            "collaboration",
            "customBranding",
            "digitalTwin",
            "aiFeatures",
        ]

        for flag in expected_flags:
            assert flag in features, f"Feature flag '{flag}' is missing from features dictionary"
            assert isinstance(features[flag], bool), f"Feature flag '{flag}' must be a boolean"
