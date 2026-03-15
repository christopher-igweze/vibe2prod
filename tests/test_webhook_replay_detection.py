"""Tests for webhook delivery replay detection with TTL-based cache.

These tests verify that the webhook replay detection properly handles
duplicate deliveries using an OrderedDict with TTL-based expiration.

Test Location: tests/test_webhook_replay_detection.py
Project: backend/api/routes/webhook.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import time
from collections import OrderedDict

# Import using relative path based on project structure
try:
    from backend.api.routes import webhook
except ImportError:
    try:
        from api.routes import webhook
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.routes import webhook
        else:
            raise ImportError("Could not import webhook module from any known path")


class TestCleanupExpiredEntries:
    """Test suite for _cleanup_expired_entries function."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clear the cache before and after each test."""
        webhook._seen_deliveries.clear()
        yield
        webhook._seen_deliveries.clear()

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_entries(self):
        """Test that cleanup removes entries that have exceeded their TTL."""
        # Setup: create OrderedDict with some expired and some valid entries
        now = int(time.time())
        
        # Add entries: one expired (100 seconds ago, TTL 60), one valid (30 seconds ago, TTL 60)
        webhook._seen_deliveries["expired-delivery"] = (now - 100, 60)  # expired
        webhook._seen_deliveries["valid-delivery"] = (now - 30, 60)  # still valid
        
        # Act
        removed_count = await webhook._cleanup_expired_entries()
        
        # Assert
        assert removed_count == 1
        assert "valid-delivery" in webhook._seen_deliveries
        assert "expired-delivery" not in webhook._seen_deliveries

    @pytest.mark.asyncio
    async def test_cleanup_returns_zero_when_no_expired(self):
        """Test that cleanup returns 0 when no entries are expired."""
        now = int(time.time())
        
        # Add only valid entries
        webhook._seen_deliveries["delivery-1"] = (now - 10, 60)
        webhook._seen_deliveries["delivery-2"] = (now - 20, 60)
        
        removed_count = await webhook._cleanup_expired_entries()
        
        assert removed_count == 0
        assert len(webhook._seen_deliveries) == 2

    @pytest.mark.asyncio
    async def test_cleanup_handles_empty_cache(self):
        """Test that cleanup handles empty cache gracefully."""
        removed_count = await webhook._cleanup_expired_entries()
        
        assert removed_count == 0

    @pytest.mark.asyncio
    async def test_cleanup_removes_all_expired(self):
        """Test that cleanup removes multiple expired entries."""
        now = int(time.time())
        
        # All expired
        webhook._seen_deliveries["expired-1"] = (now - 200, 60)
        webhook._seen_deliveries["expired-2"] = (now - 300, 60)
        webhook._seen_deliveries["expired-3"] = (now - 400, 60)
        
        removed_count = await webhook._cleanup_expired_entries()
        
        assert removed_count == 3
        assert len(webhook._seen_deliveries) == 0


class TestRegisterDelivery:
    """Test suite for _register_delivery function."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clear the cache and cleanup task before and after each test."""
        webhook._seen_deliveries.clear()
        webhook._cleanup_task = None
        yield
        webhook._seen_deliveries.clear()
        webhook._cleanup_task = None

    @pytest.mark.asyncio
    async def test_register_new_delivery_returns_true(self):
        """Test that registering a new delivery returns True."""
        with patch.object(webhook, '_start_cleanup_task'):
            result = await webhook._register_delivery("new-delivery-123")
        
        assert result is True
        assert "new-delivery-123" in webhook._seen_deliveries

    @pytest.mark.asyncio
    async def test_register_duplicate_within_ttl_returns_false(self):
        """Test that registering a duplicate within TTL window returns False."""
        now = int(time.time())
        webhook._seen_deliveries["duplicate-delivery"] = (now - 30, 60)
        
        with patch.object(webhook, '_start_cleanup_task'):
            result = await webhook._register_delivery("duplicate-delivery")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_register_duplicate_outside_ttl_returns_true(self):
        """Test that a delivery ID outside its TTL window can be registered again."""
        # Entry exists but is expired
        now = int(time.time())
        webhook._seen_deliveries["expired-dup"] = (now - 100, 60)  # expired
        
        with patch.object(webhook, '_start_cleanup_task'):
            result = await webhook._register_delivery("expired-dup")
        
        # Should return True because the old entry is now expired
        assert result is True
        assert "expired-dup" in webhook._seen_deliveries
        # TTL should be updated
        seen_ts, ttl = webhook._seen_deliveries["expired-dup"]
        assert seen_ts == now  # timestamp updated

    @pytest.mark.asyncio
    async def test_register_stores_timestamp_and_ttl(self):
        """Test that _register_delivery stores both timestamp and TTL."""
        with patch.object(webhook, '_start_cleanup_task'):
            await webhook._register_delivery("test-delivery")
        
        assert "test-delivery" in webhook._seen_deliveries
        seen_ts, ttl = webhook._seen_deliveries["test-delivery"]
        assert isinstance(seen_ts, int)
        assert isinstance(ttl, int)
        assert ttl >= 60  # TTL should be at least 60 seconds


class TestOrderedDictMaintenance:
    """Test suite for OrderedDict order maintenance (FIFO behavior)."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clear the cache and cleanup task before and after each test."""
        webhook._seen_deliveries.clear()
        webhook._cleanup_task = None
        yield
        webhook._seen_deliveries.clear()
        webhook._cleanup_task = None

    @pytest.mark.asyncio
    async def test_move_to_end_on_duplicate(self):
        """Test that accessing a delivery moves it to the end of OrderedDict."""
        with patch.object(webhook, '_start_cleanup_task'):
            # Register two deliveries
            await webhook._register_delivery("delivery-a")
            await webhook._register_delivery("delivery-b")
            
            # Verify order
            keys = list(webhook._seen_deliveries.keys())
            assert keys == ["delivery-a", "delivery-b"]
            
            # Re-register delivery-a (not duplicate within TTL, but should move to end)
            await webhook._register_delivery("delivery-a")
            
            # Check new order - delivery-a should be at end
            keys = list(webhook._seen_deliveries.keys())
            assert keys == ["delivery-b", "delivery-a"]

    @pytest.mark.asyncio
    async def test_multiple_registrations_maintain_order(self):
        """Test that multiple registrations maintain proper ordering."""
        with patch.object(webhook, '_start_cleanup_task'):
            await webhook._register_delivery("first")
            await webhook._register_delivery("second")
            await webhook._register_delivery("third")
            
            keys = list(webhook._seen_deliveries.keys())
            assert keys == ["first", "second", "third"]


class TestPeriodicCleanup:
    """Test suite for _periodic_cleanup background task."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clear the cache and cleanup task before and after each test."""
        webhook._seen_deliveries.clear()
        webhook._cleanup_task = None
        yield
        webhook._seen_deliveries.clear()
        if webhook._cleanup_task and not webhook._cleanup_task.done():
            webhook._cleanup_task.cancel()
        webhook._cleanup_task = None

    @pytest.mark.asyncio
    async def test_periodic_cleanup_runs_and_removes_expired(self):
        """Test that periodic cleanup removes expired entries."""
        now = int(time.time())
        # Add expired entry
        webhook._seen_deliveries["old-delivery"] = (now - 200, 60)
        
        # Manually run periodic cleanup once
        cleanup_task = asyncio.create_task(webhook._periodic_cleanup())
        await asyncio.sleep(0.1)  # Let it run one iteration
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
        assert "old-delivery" not in webhook._seen_deliveries

    @pytest.mark.asyncio
    async def test_start_cleanup_task_creates_task(self):
        """Test that _start_cleanup_task creates a cleanup task."""
        assert webhook._cleanup_task is None or webhook._cleanup_task.done()
        
        webhook._start_cleanup_task()
        
        assert webhook._cleanup_task is not None
        assert not webhook._cleanup_task.done()
        
        # Cleanup
        webhook._cleanup_task.cancel()
        try:
            await webhook._cleanup_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_cleanup_task_does_not_duplicate(self):
        """Test that _start_cleanup_task doesn't create duplicate tasks."""
        webhook._start_cleanup_task()
        first_task = webhook._cleanup_task
        
        webhook._start_cleanup_task()
        
        # Should be the same task (not recreated)
        assert webhook._cleanup_task is first_task
        
        # Cleanup
        webhook._cleanup_task.cancel()
        try:
            await webhook._cleanup_task
        except asyncio.CancelledError:
            pass
