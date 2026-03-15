"""Tests for sandbox manager Daytona client initialization error handling.

These tests verify that the SandboxManager properly handles errors during
Daytona client initialization and raises appropriate RuntimeErrors instead of
allowing raw exceptions to propagate.

Test Location: tests/test_sandbox_manager_error_handling.py
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


class TestSandboxManagerErrorHandling:
    """Test suite for sandbox manager Daytona client initialization error handling."""

    def test_daytona_initialization_exception_caught(self):
        """Test that exceptions during Daytona initialization are caught and wrapped."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            # Configure mock to raise an exception during initialization
            mock_daytona_class.side_effect = ValueError("Invalid API key format")
            
            with patch("sandbox.manager.settings") as mock_settings:
                mock_settings.daytona_api_key = "invalid-key"
                mock_settings.daytona_api_url = "http://localhost:50001"
                mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                mock_settings.github_token = None
                mock_settings.sandbox_timeout_minutes = 30
                mock_settings.docker_image_uri = "ubuntu:22.04"
                
                # Should raise RuntimeError, not ValueError
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                assert "Sandbox service unavailable" in str(exc_info.value)
                assert "Daytona client could not be initialized" in str(exc_info.value)
                assert "Invalid API key format" in str(exc_info.value)

    def test_daytona_initialization_generic_exception_caught(self):
        """Test that generic exceptions during Daytona initialization are caught."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            # Configure mock to raise a generic exception
            mock_daytona_class.side_effect = Exception("Network connection failed")
            
            with patch("sandbox.manager.settings") as mock_settings:
                mock_settings.daytona_api_key = "test-key"
                mock_settings.daytona_api_url = "http://localhost:50001"
                mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                mock_settings.github_token = None
                mock_settings.sandbox_timeout_minutes = 30
                mock_settings.docker_image_uri = "ubuntu:22.04"
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                assert "Sandbox service unavailable" in str(exc_info.value)
                assert "Network connection failed" in str(exc_info.value)

    def test_daytona_initialization_attribute_error_caught(self):
        """Test that AttributeError during Daytona initialization is caught."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            # Configure mock to raise AttributeError
            mock_daytona_class.side_effect = AttributeError("'NoneType' object has no attribute 'connect'")
            
            with patch("sandbox.manager.settings") as mock_settings:
                mock_settings.daytona_api_key = "test-key"
                mock_settings.daytona_api_url = "http://localhost:50001"
                mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                mock_settings.github_token = None
                mock_settings.sandbox_timeout_minutes = 30
                mock_settings.docker_image_uri = "ubuntu:22.04"
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                assert "Sandbox service unavailable" in str(exc_info.value)

    def test_daytona_initialization_success_no_exception(self):
        """Test that successful Daytona initialization does not raise an exception."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            # Configure mock to succeed
            mock_instance = MagicMock()
            mock_daytona_class.return_value = mock_instance
            
            with patch("sandbox.manager.settings") as mock_settings:
                mock_settings.daytona_api_key = "valid-key"
                mock_settings.daytona_api_url = "http://localhost:50001"
                mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                mock_settings.github_token = None
                mock_settings.sandbox_timeout_minutes = 30
                mock_settings.docker_image_uri = "ubuntu:22.04"
                
                # Should not raise any exception
                manager = SandboxManager()
                assert manager._daytona is mock_instance

    def test_daytona_initialization_exception_preserves_cause(self):
        """Test that RuntimeError preserves the original exception as __cause__."""
        original_error = RuntimeError("Daytona service unreachable")
        
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            mock_daytona_class.side_effect = original_error
            
            with patch("sandbox.manager.settings") as mock_settings:
                mock_settings.daytona_api_key = "test-key"
                mock_settings.daytona_api_url = "http://localhost:50001"
                mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                mock_settings.github_token = None
                mock_settings.sandbox_timeout_minutes = 30
                mock_settings.docker_image_uri = "ubuntu:22.04"
                
                with pytest.raises(RuntimeError) as exc_info:
                    SandboxManager()
                
                # Verify exception chaining
                assert exc_info.value.__cause__ is original_error

    def test_daytona_initialization_executor_created_on_success(self):
        """Test that SandboxExecutor is created even after Daytona initialization."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            mock_instance = MagicMock()
            mock_daytona_class.return_value = mock_instance
            
            with patch("sandbox.manager.SandboxExecutor") as mock_executor_class:
                mock_executor_instance = MagicMock()
                mock_executor_class.return_value = mock_executor_instance
                
                with patch("sandbox.manager.settings") as mock_settings:
                    mock_settings.daytona_api_key = "valid-key"
                    mock_settings.daytona_api_url = "http://localhost:50001"
                    mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                    mock_settings.github_token = None
                    mock_settings.sandbox_timeout_minutes = 30
                    mock_settings.docker_image_uri = "ubuntu:22.04"
                    
                    manager = SandboxManager()
                    # Executor should be created and assigned
                    mock_executor_class.assert_called_once()
                    assert manager._executor is mock_executor_instance

    def test_daytona_initialization_error_prevents_executor_creation(self):
        """Test that SandboxExecutor is not reached if Daytona initialization fails."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            mock_daytona_class.side_effect = Exception("Init failed")
            
            with patch("sandbox.manager.SandboxExecutor") as mock_executor_class:
                with patch("sandbox.manager.settings") as mock_settings:
                    mock_settings.daytona_api_key = "test-key"
                    mock_settings.daytona_api_url = "http://localhost:50001"
                    mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                    mock_settings.github_token = None
                    mock_settings.sandbox_timeout_minutes = 30
                    mock_settings.docker_image_uri = "ubuntu:22.04"
                    
                    with pytest.raises(RuntimeError):
                        SandboxManager()
                    
                    # SandboxExecutor should not have been instantiated
                    mock_executor_class.assert_not_called()

    def test_daytona_initialization_sessions_dict_initialized_on_success(self):
        """Test that _sessions dict is initialized upon successful creation."""
        with patch("sandbox.manager.Daytona") as mock_daytona_class:
            mock_instance = MagicMock()
            mock_daytona_class.return_value = mock_instance
            
            with patch("sandbox.manager.settings") as mock_settings:
                mock_settings.daytona_api_key = "valid-key"
                mock_settings.daytona_api_url = "http://localhost:50001"
                mock_settings.forge_source = "https://github.com/codespin-io/forge-engine"
                mock_settings.github_token = None
                mock_settings.sandbox_timeout_minutes = 30
                mock_settings.docker_image_uri = "ubuntu:22.04"
                
                manager = SandboxManager()
                # Verify _sessions dict is initialized as empty
                assert hasattr(manager, "_sessions")
                assert isinstance(manager._sessions, dict)
                assert len(manager._sessions) == 0
