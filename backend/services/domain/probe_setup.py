"""Probe configuration and setup — test patterns and payloads.

Extracted from probe_executor.py for single-responsibility.
"""

from __future__ import annotations

# SQL error patterns that indicate injection vulnerability
SQL_ERROR_PATTERNS = [
    "you have an error in your sql syntax",
    "warning: mysql",
    "unclosed quotation mark",
    "quoted string not properly terminated",
    "pg_query",
    "pg_exec",
    "syntax error at or near",
    "microsoft ole db provider for sql server",
    "ora-01756",
    "ora-00933",
    "sqlite3.operationalerror",
    "mongodb.*error",
    "unterminated string",
]

# XSS test payloads
XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "';alert(1)//",
    "<svg onload=alert(1)>",
]

# Sensitive file paths to probe
SENSITIVE_PATHS = [
    "/.env",
    "/.git/config",
    "/debug",
    "/admin",
    "/wp-admin",
    "/phpinfo.php",
    "/.DS_Store",
    "/server-status",
    "/elmah.axd",
    "/wp-config.php.bak",
]

# Open redirect parameter names
REDIRECT_PARAMS = ["redirect", "url", "next", "return", "returnTo", "goto", "continue"]

# Common admin/login paths
AUTH_PATHS = [
    "/admin",
    "/admin/login",
    "/login",
    "/wp-login.php",
    "/administrator",
    "/dashboard",
    "/api/admin",
    "/console",
]
