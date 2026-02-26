#!/usr/bin/env python3
"""Clear all legacy Tier 1 scan data from Supabase.

Run once to wipe scan_reports, report_artifacts, findings,
action_items, and fix_attempts before switching to FORGE.

Usage:
    cd backend && PYTHONPATH=. python scripts/clear_legacy_scans.py
"""

from __future__ import annotations

import os
import sys

# Allow running from backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

TABLES = [
    "fix_attempts",
    "action_items",
    "findings",
    "report_artifacts",
    "scan_reports",
]


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        sys.exit(1)

    client = create_client(url, key)

    print("Clearing legacy scan data from Supabase...")
    print(f"  Target: {url}")
    print(f"  Tables: {', '.join(TABLES)}")
    print()

    for table in TABLES:
        try:
            # Delete all rows — neq filter on id ensures RPC-level delete works
            result = client.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            count = len(result.data) if result.data else 0
            print(f"  {table}: deleted {count} rows")
        except Exception as e:
            print(f"  {table}: ERROR — {e}")

    print()
    print("Done. All legacy scan data cleared.")


if __name__ == "__main__":
    main()
