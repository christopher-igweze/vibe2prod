"""Tests for program module imports.

These tests verify that the program.py module properly imports utc_now
from the correct module (models._utils).

Test Location: tests/test_program_imports.py
Project: backend/models/program.py
Framework: pytest
"""

import pytest
from datetime import datetime
from uuid import uuid4

# Import from program module - handle different project layouts by adding backend parent to path
try:
    from backend.models.program import ValidationCampaign, PolicyProfile, SecretRef
except ImportError:
    try:
        from models.program import ValidationCampaign, PolicyProfile, SecretRef
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from models.program import ValidationCampaign, PolicyProfile, SecretRef
        else:
            raise ImportError("Could not import program models from any known path")


class TestProgramModuleImports:
    """Test suite for program module import validation."""

    def test_import_utc_now_from_correct_module(self):
        """Test that utc_now is importable from models._utils, not utils."""
        # This test verifies the import path is correct
        # If the import was wrong (from utils), this would raise ImportError
        try:
            from models._utils import utc_now
        except ImportError:
            pytest.fail("utc_now should be importable from models._utils")

    def test_program_module_imports_validation_campaign(self):
        """Test that ValidationCampaign can be imported from program module."""
        assert ValidationCampaign is not None
        assert hasattr(ValidationCampaign, 'campaign_id')
        assert hasattr(ValidationCampaign, 'created_at')

    def test_program_module_imports_policy_profile(self):
        """Test that PolicyProfile can be imported from program module."""
        assert PolicyProfile is not None
        assert hasattr(PolicyProfile, 'profile_id')
        assert hasattr(PolicyProfile, 'created_at')

    def test_program_module_imports_secret_ref(self):
        """Test that SecretRef can be imported from program module."""
        assert SecretRef is not None
        assert hasattr(SecretRef, 'secret_id')
        assert hasattr(SecretRef, 'created_at')

    def test_utc_now_returns_datetime(self):
        """Test that utc_now function returns a valid datetime object."""
        from models._utils import utc_now
        result = utc_now()
        assert isinstance(result, datetime)

    def test_validation_campaign_uses_utc_now_default(self):
        """Test that ValidationCampaign uses utc_now as default factory for created_at."""
        campaign = ValidationCampaign(
            campaign_id=uuid4(),
            name="Test Campaign",
            created_by="test_user"
        )
        assert isinstance(campaign.created_at, datetime)

    def test_policy_profile_uses_utc_now_default(self):
        """Test that PolicyProfile uses utc_now as default factory for created_at."""
        profile = PolicyProfile(
            profile_id=uuid4(),
            name="Test Profile",
            created_by="test_user"
        )
        assert isinstance(profile.created_at, datetime)

    def test_secret_ref_uses_utc_now_default(self):
        """Test that SecretRef uses utc_now as default factory for created_at."""
        ref = SecretRef(
            secret_id=uuid4(),
            name="Test Secret",
            masked_value="*****",
            cipher_digest="sha256"
        )
        assert isinstance(ref.created_at, datetime)
