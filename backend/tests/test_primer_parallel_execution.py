"""Tests for primer endpoint parallel execution optimization.

These tests verify that the run_primer function uses asyncio.gather()
to execute independent sandbox exec() calls concurrently instead of sequentially.

Test Location: tests/test_primer_parallel_execution.py
Project: api/routes/primer.py
Framework: pytest
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import using relative path based on project structure
# The primer.py is in backend/api/routes/primer.py
# Tests are in backend/tests/
_backend_path = Path(__file__).parent.parent
if str(_backend_path) not in sys.path:
    sys.path.insert(0, str(_backend_path))

try:
    from api.routes.primer import run_primer, PrimerRequest
except ImportError:
    try:
        from routes.primer import run_primer, PrimerRequest
    except ImportError:
        # Try direct import
        sys.path.insert(0, str(_backend_path / "api"))
        from routes.primer import run_primer, PrimerRequest


class TestPrimerParallelExecution:
    """Test suite for parallel execution in run_primer endpoint."""

    @pytest.fixture
    def mock_sandbox_mgr(self):
        """Create a mock sandbox manager with exec returning valid results."""
        mock = MagicMock()
        mock.exec = AsyncMock(
            side_effect=lambda *args, **kwargs: f"result for {args[1] if len(args) > 1 else 'unknown'}"
        )
        mock.read_file = AsyncMock(return_value='{"name": "test"}')
        mock.provision = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_primer_imports_asyncio(self):
        """Test that the primer module imports asyncio."""
        # Read the source file to verify asyncio is imported
        source_file = Path(__file__).parent.parent / "api" / "routes" / "primer.py"
        if not source_file.exists():
            source_file = Path(__file__).parent.parent / "routes" / "primer.py"
        
        with open(source_file, 'r') as f:
            source = f.read()
        
        # Verify asyncio is imported
        assert "import asyncio" in source, "run_primer should import asyncio module"

    @pytest.mark.asyncio
    async def test_primer_uses_asyncio_gather(self):
        """Test that run_primer uses asyncio.gather for parallel exec calls."""
        # Read the source file to verify asyncio.gather is used
        source_file = Path(__file__).parent.parent / "api" / "routes" / "primer.py"
        if not source_file.exists():
            source_file = Path(__file__).parent.parent / "routes" / "primer.py"
        
        with open(source_file, 'r') as f:
            source = f.read()
        
        # Verify asyncio.gather is used in the function
        assert "asyncio.gather" in source, "run_primer should use asyncio.gather for parallel execution"

    @pytest.mark.asyncio
    async def test_primer_exec_calls_run_concurrently(self):
        """Test that the three sandbox exec calls run concurrently."""
        execution_times = []
        
        async def mock_exec(*args, **kwargs):
            # Record the start time
            start = time.time()
            
            # Simulate a small delay to make timing differences measurable
            await asyncio.sleep(0.1)
            
            execution_times.append((args[1] if len(args) > 1 else 'unknown', start, time.time()))
            return f"result for {args[1] if len(args) > 1 else 'unknown'}"
        
        # Add backend/api to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        with patch('sandbox.manager.SandboxManager') as mock_sb_class, \
             patch('services.supabase_client') as mock_db, \
             patch('services.github.get_repo_info') as mock_get_repo_info, \
             patch('services.github.get_head_sha') as mock_get_head_sha, \
             patch('services.github.parse_repo_url') as mock_parse_repo_url, \
             patch('services.http_client.shared_client'):
            
            # Setup mocks
            mock_sb = MagicMock()
            mock_sb.exec = mock_exec
            mock_sb.read_file = AsyncMock(return_value='{"name": "test"}')
            mock_sb.provision = AsyncMock()
            mock_sb_class.return_value = mock_sb
            
            mock_db.get_github_access_token = AsyncMock(return_value="token")
            mock_db.get_or_create_project = AsyncMock(return_value="project-id")
            mock_db.get_project_primer = AsyncMock(return_value=None)
            
            mock_repo_info = MagicMock()
            mock_repo_info.default_branch = "main"
            mock_repo_info.full_name = "owner/repo"
            mock_get_repo_info = AsyncMock(return_value=mock_repo_info)
            mock_get_head_sha = AsyncMock(return_value="sha123")
            mock_parse_repo_url = AsyncMock(return_value=("owner", "repo"))
            
            # Create request
            from fastapi import Request as FastAPIRequest
            
            # Mock the request object
            mock_request = MagicMock(spec=FastAPIRequest)
            mock_request.state.user_id = "user-123"
            
            # Create PrimerRequest
            from pydantic import HttpUrl
            request_body = PrimerRequest(repo_url=HttpUrl("https://github.com/owner/repo"))
            
            # Call the function
            await run_primer(request_body, mock_request)
            
            # Verify that exec was called 3 times
            assert mock_sb.exec.call_count == 3, f"Expected 3 exec calls, got {mock_sb.exec.call_count}"
            
            # If running concurrently, total time should be close to the longest single call
            # not the sum of all three calls
            # With 3 calls of 0.1s each:
            # - Sequential: ~0.3s
            # - Concurrent: ~0.1s
            if len(execution_times) >= 3:
                # Get the start of first call and end of last call
                first_start = min(e[1] for e in execution_times)
                last_end = max(e[2] for e in execution_times)
                total_time = last_end - first_start
                
                # With concurrent execution, should be close to 0.1s, not 0.3s
                # Allow some buffer for test overhead
                assert total_time < 0.25, f"Expected concurrent execution (< 0.25s), but took {total_time:.2f}s"

    @pytest.mark.asyncio
    async def test_primer_results_correctly_unpacked(self):
        """Test that the results from asyncio.gather are correctly unpacked to variables."""
        # Read the source file to verify proper unpacking
        source_file = Path(__file__).parent.parent / "api" / "routes" / "primer.py"
        if not source_file.exists():
            source_file = Path(__file__).parent.parent / "routes" / "primer.py"
        
        with open(source_file, 'r') as f:
            source = f.read()
        
        # Verify that variables are properly unpacked from asyncio.gather
        # Should have: tree, top_dirs, head = await asyncio.gather(...
        assert "tree, top_dirs, head" in source or "tree, top_dirs, head =" in source, \
            "run_primer should unpack tree, top_dirs, head from asyncio.gather result"
