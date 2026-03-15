"""Tests for database health check functionality.

These tests verify that the check_database_health function properly handles
database connectivity and returns appropriate boolean values.

Test Location: tests/test_database_health_check.py
Project: services/supabase_client.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# Import using relative path based on project structure
try:
    from services import supabase_client as db
except ImportError:
    try:
        from supabase_client import check_database_health
    except ImportError:
        import sys
        from pathlib import Path
        # Add services to path if needed
        services_path = Path(__file__).parent.parent / "services"
        if services_path.exists():
            sys.path.insert(0, str(services_path.parent))
            from services.supabase_client import check_database_health
        else:
            raise ImportError("Could not import check_database_health from any known path")


class TestCheckDatabaseHealth:
    """Test suite for check_database_health function."""

    @pytest.mark.asyncio
    async def test_check_database_health_returns_true_when_database_available(self):
        """Test that check_database_health returns True when database is reachable."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock the table().select().limit().execute() chain
            mock_execute = MagicMock()
            mock_execute.data = [{"id": "some-uuid"}]
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = mock_execute
            mock_client_instance.table.return_value = mock_table
            
            result = await db.check_database_health()
            
            # Should return True when database is reachable
            assert result is True

    @pytest.mark.asyncio
    async def test_check_database_health_returns_false_on_connection_error(self):
        """Test that check_database_health returns False when connection fails."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            result = await db.check_database_health()
            
            # Should return False on connection error, not raise
            assert result is False

    @pytest.mark.asyncio
    async def test_check_database_health_returns_false_on_timeout(self):
        """Test that check_database_health returns False on timeout."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Simulate timeout error during query execution
            mock_client_instance.table.side_effect = TimeoutError("Request timed out")
            
            result = await db.check_database_health()
            
            # Should return False on timeout, not raise
            assert result is False

    @pytest.mark.asyncio
    async def test_check_database_health_returns_false_on_query_error(self):
        """Test that check_database_health returns False when query execution fails."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock the table chain that raises an exception
            mock_table = MagicMock()
            mock_table.select.side_effect = Exception("Query failed")
            mock_client_instance.table.return_value = mock_table
            
            result = await db.check_database_health()
            
            # Should return False on query error, not raise
            assert result is False

    @pytest.mark.asyncio
    async def test_check_database_health_returns_false_on_execute_error(self):
        """Test that check_database_health returns False when execute raises an exception."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock the table chain where execute() raises
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_select.limit = MagicMock(return_value=mock_select)
            mock_select.execute.side_effect = Exception("Database error")
            mock_table.select.return_value = mock_select
            mock_client_instance.table.return_value = mock_table
            
            result = await db.check_database_health()
            
            # Should return False when execute raises, not raise
            assert result is False
