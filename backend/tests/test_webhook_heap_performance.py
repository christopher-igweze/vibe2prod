"""Tests for webhook replay check heap-based performance improvements.

These tests verify that the _register_delivery function uses an efficient
heap-based expiration tracking system instead of O(n) dictionary iteration.

Test Location: backend/tests/test_webhook_heap_performance.py
Project: backend/api/routes/webhook.py
Framework: pytest
"""

import asyncio
import heapq
import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from api.routes.webhook import (
        _register_delivery,
        _cleanup_expired_entries,
        _expiration_heap,
        _seen_deliveries,
        _deliveries_lock,
        _cleanup_task,
        _MAX_HEAP_ENTRIES,
    )
except ImportError:
    try:
        from routes.webhook import (
            _register_delivery,
            _cleanup_expired_entries,
            _expiration_heap,
            _seen_deliveries,
            _deliveries_lock,
            _cleanup_task,
            _MAX_HEAP_ENTRIES,
        )
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        from api.routes.webhook import (
            _register_delivery,
            _cleanup_expired_entries,
            _expiration_heap,
            _seen_deliveries,
            _deliveries_lock,
            _cleanup_task,
            _MAX_HEAP_ENTRIES,
        )


class TestHeapBasedExpirationTracking:
    """Test suite for heap-based expiration tracking in webhook replay check."""

    def setup_method(self):
        """Reset module-level state before each test."""
        # Reset the module-level state
        import api.routes.webhook as webhook_module
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        webhook_module._cleanup_task = None

    @pytest.mark.asyncio
    async def test_heap_populated_on_delivery_registration(self):
        """Test that delivery registration adds entry to the expiration heap."""
        import api.routes.webhook as webhook_module
        
        # Reset state
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        
        # Mock settings to avoid dependency
        with patch('api.routes.webhook.settings') as mock_settings:
            mock_settings.webhook_replay_window_seconds = 120
            mock_settings.github_webhook_secret = "test_secret"
            
            # Register a delivery
            result = await _register_delivery("test-delivery-id")
            
            # Should succeed
            assert result is True
            
            # Heap should have one entry
            assert len(webhook_module._expiration_heap) == 1
            
            # Heap entry should be (expiration_time, delivery_id)
            exp_time, delivery_id = webhook_module._expiration_heap[0]
            assert delivery_id == "test-delivery-id"
            # Expiration should be roughly now + ttl
            expected_exp = int(time.time()) + 120
            assert abs(exp_time - expected_exp) <= 1

    @pytest.mark.asyncio
    async def test_heap_respects_max_size_limit(self):
        """Test that heap size is bounded to prevent memory issues."""
        import api.routes.webhook as webhook_module
        
        # Reset state
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        
        with patch('api.routes.webhook.settings') as mock_settings:
            mock_settings.webhook_replay_window_seconds = 120
            mock_settings.github_webhook_secret = "test_secret"
            
            # Register more deliveries than MAX_HEAP_ENTRIES
            for i in range(_MAX_HEAP_ENTRIES + 100):
                await _register_delivery(f"delivery-{i}")
            
            # Heap should be bounded
            assert len(webhook_module._expiration_heap) <= _MAX_HEAP_ENTRIES

    @pytest.mark.asyncio
    async def test_cleanup_uses_heap_for_efficient_expiration(self):
        """Test that cleanup efficiently uses heap to find expired entries."""
        import api.routes.webhook as webhook_module
        
        # Reset state
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        
        with patch('api.routes.webhook.settings') as mock_settings:
            mock_settings.webhook_replay_window_seconds = 120
            mock_settings.github_webhook_secret = "test_secret"
            
            # Register deliveries with known expiration times
            now_ts = int(time.time())
            
            # Create entries: one expired, one not
            webhook_module._seen_deliveries["expired-delivery"] = (now_ts - 200, 120)
            webhook_module._seen_deliveries["valid-delivery"] = (now_ts, 120)
            
            # Push to heap
            heapq.heappush(webhook_module._expiration_heap, (now_ts - 80, "expired-delivery"))  # expired
            heapq.heappush(webhook_module._expiration_heap, (now_ts + 120, "valid-delivery"))  # not expired
            
            # Run cleanup
            removed = await _cleanup_expired_entries()
            
            # Should have removed the expired entry
            assert removed >= 1
            assert "expired-delivery" not in webhook_module._seen_deliveries
            assert "valid-delivery" in webhook_module._seen_deliveries

    @pytest.mark.asyncio
    async def test_duplicate_delivery_returns_false(self):
        """Test that duplicate deliveries within TTL window return False."""
        import api.routes.webhook as webhook_module
        
        # Reset state
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        
        with patch('api.routes.webhook.settings') as mock_settings:
            mock_settings.webhook_replay_window_seconds = 120
            mock_settings.github_webhook_secret = "test_secret"
            
            # Register first delivery
            result1 = await _register_delivery("duplicate-test")
            assert result1 is True
            
            # Register duplicate
            result2 = await _register_delivery("duplicate-test")
            assert result2 is False

    @pytest.mark.asyncio
    async def test_expired_entry_allows_re_registration(self):
        """Test that expired entries can be re-registered."""
        import api.routes.webhook as webhook_module
        
        # Reset state
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        
        with patch('api.routes.webhook.settings') as mock_settings:
            mock_settings.webhook_replay_window_seconds = 1  # Short TTL for testing
            mock_settings.github_webhook_secret = "test_secret"
            
            # Register delivery
            result1 = await _register_delivery("expire-test")
            assert result1 is True
            
            # Wait for expiration
            await asyncio.sleep(1.5)
            
            # Manually add expired entry to cache and heap for testing
            now_ts = int(time.time())
            webhook_module._seen_deliveries["expire-test"] = (now_ts - 100, 1)
            heapq.heappush(webhook_module._expiration_heap, (now_ts - 99, "expire-test"))
            
            # Run cleanup to remove expired
            await _cleanup_expired_entries()
            
            # Should be able to register again
            result2 = await _register_delivery("expire-test")
            assert result2 is True

    @pytest.mark.asyncio
    async def test_lazy_cleanup_task_initialization(self):
        """Test that cleanup task is lazily initialized on first delivery registration."""
        import api.routes.webhook as webhook_module
        
        # Reset state
        webhook_module._seen_deliveries.clear()
        webhook_module._expiration_heap.clear()
        webhook_module._cleanup_task = None
        
        with patch('api.routes.webhook.settings') as mock_settings:
            mock_settings.webhook_replay_window_seconds = 120
            mock_settings.github_webhook_secret = "test_secret"
            
            # Cleanup task should be None initially
            assert webhook_module._cleanup_task is None
            
            # Register a delivery
            await _register_delivery("lazy-init-test")
            
            # Cleanup task should now be set
            assert webhook_module._cleanup_task is not None
