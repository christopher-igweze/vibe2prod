"""Tests for sandbox manager Daytona client initialization error handling.

These tests verify that the SandboxManager properly handles errors during
Daytona client initialization and raises appropriate RuntimeErrors instead of
allowing raw exceptions to propagate.

Test Location: tests/test_sandbox_manager_daytona_error_handling.py
Project: backend/sandbox/manager.py
Framework: pytest
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import UUID

try:
    from backend.sandbox.manager import SandboxManager
except ImportError:
    try:
        from sandbox.manager import SandboxManager
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from sandbox.manager import SandboxManager
        else:
            raise ImportError("Could not import SandboxManager from any known path")


BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "DAYTONA_API_URL": "http://localhost:50001",
    "FORGE_SOURCE": "https://github.com/codespin-io/forge-engine",
    "SANDBOX_TIMEOUT_MINUTES": "30",
    "DOCKER_IMAGE_URI": "ubuntu:22.04",
}


class TestSandboxManagerDaytonaErrorHandling:
    """Test suite for sandbox manager Daytona client initialization error handling."""

    def test_daytona_initialization_value_error_caught_and_wrapped(self):
        """Test that ValueError during Daytona initialization is caught and wrapped in RuntimeError."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                mock_daytona_class.side_effect = ValueError("Invalid API key format")
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                error_msg = str(exc_info.value)
                assert "Sandbox service unavailable" in error_msg
                assert "Daytona client could not be initialized" in error_msg
                assert "Invalid API key format" in error_msg
                assert exc_info.value.__cause__ is not None
                assert isinstance(exc_info.value.__cause__, ValueError)

    def test_daytona_initialization_generic_exception_caught_and_wrapped(self):
        """Test that generic Exception during Daytona initialization is caught and wrapped."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                mock_daytona_class.side_effect = Exception("Network connection failed")
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                error_msg = str(exc_info.value)
                assert "Sandbox service unavailable" in error_msg
                assert "Network connection failed" in error_msg
                assert exc_info.value.__cause__ is not None

    def test_daytona_initialization_attribute_error_caught_and_wrapped(self):
        """Test that AttributeError during Daytona initialization is caught and wrapped."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                mock_daytona_class.side_effect = AttributeError("'NoneType' object has no attribute 'connect'")
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                error_msg = str(exc_info.value)
                assert "Sandbox service unavailable" in error_msg
                assert "Daytona client could not be initialized" in error_msg
                assert exc_info.value.__cause__ is not None
                assert isinstance(exc_info.value.__cause__, AttributeError)

    def test_daytona_initialization_runtime_error_caught_and_reraised(self):
        """Test that RuntimeError during Daytona initialization is caught and wrapped with context."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                mock_daytona_class.side_effect = RuntimeError("Daytona probe failed")
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                error_msg = str(exc_info.value)
                assert "Sandbox service unavailable" in error_msg
                assert "Daytona probe failed" in error_msg

    def test_daytona_initialization_type_error_caught_and_wrapped(self):
        """Test that TypeError during Daytona initialization is caught and wrapped."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                mock_daytona_class.side_effect = TypeError("__init__() missing 1 required positional argument: 'config'")
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                error_msg = str(exc_info.value)
                assert "Sandbox service unavailable" in error_msg
                assert "Daytona client could not be initialized" in error_msg

    def test_daytona_successful_initialization_no_error(self):
        """Test that successful Daytona initialization does not raise RuntimeError."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                mock_daytona_instance = MagicMock()
                mock_daytona_class.return_value = mock_daytona_instance
                
                with patch("sandbox.manager.SandboxExecutor") as mock_executor_class:
                    mock_executor_instance = MagicMock()
                    mock_executor_class.return_value = mock_executor_instance
                    
                    sandbox_manager = SandboxManager()
                    assert sandbox_manager._daytona == mock_daytona_instance
                    assert sandbox_manager._executor == mock_executor_instance

    def test_error_contains_original_exception_details(self):
        """Test that the RuntimeError message contains specific details from the original exception."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                original_error_msg = "Connection refused on endpoint http://localhost:50001"
                mock_daytona_class.side_effect = ConnectionError(original_error_msg)
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                error_msg = str(exc_info.value)
                assert original_error_msg in error_msg
                assert exc_info.value.__cause__.__class__.__name__ == "ConnectionError"

    def test_exception_chain_preserved_for_debugging(self):
        """Test that the exception chain is preserved for debugging via 'from exc'."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            with patch("sandbox.manager.Daytona") as mock_daytona_class:
                original_exception = KeyError("DAYTONA_CONFIG_KEY")
                mock_daytona_class.side_effect = original_exception
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                runtime_error = exc_info.value
                assert runtime_error.__cause__ is original_exception
                assert runtime_error.__context__ is None or isinstance(runtime_error.__context__, Exception)
