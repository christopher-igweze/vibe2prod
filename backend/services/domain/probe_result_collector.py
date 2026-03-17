"""Probe result aggregation — collects and combines findings from multiple tests.

Extracted from probe_executor.py for single-responsibility.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from models.probe import ProbeFinding

logger = logging.getLogger(__name__)


async def collect_results(
    tests: list[Any],
) -> list[ProbeFinding]:
    """Run all test coroutines and collect their findings.

    Each test should be a coroutine that returns list[ProbeFinding].
    Exceptions from individual tests are logged but don't fail the whole run.
    """
    findings: list[ProbeFinding] = []
    results = await asyncio.gather(*tests, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Probe test %d failed: %s", i, result)
        elif isinstance(result, list):
            findings.extend(result)
    return findings
