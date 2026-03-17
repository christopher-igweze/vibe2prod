"""GitHub API helpers — backward-compatible facade.

Re-exports from split sub-modules:
  - github_repository_ops: Repo info, metadata, listing, parsing
  - github_file_ops: Profile fetching, OAuth token exchange
  - github_commit_ops: Commit operations, SHA lookup, PR creation
"""

from __future__ import annotations

# Re-export from github_repository_ops
from services.github_repository_ops import (  # noqa: F401
    RepoInfo,
    GitHubRepo,
    GitHubBranch,
    RepoPagination,
    parse_repo_url,
    get_repo_info,
    list_user_repos,
    list_repo_branches,
    verify_token,
    _handle_github_network_error,
    _parse_link_header,
)

# Re-export from github_file_ops
from services.github_file_ops import (  # noqa: F401
    fetch_github_profile,
    exchange_code_for_access_token,
)

# Re-export from github_commit_ops
from services.github_commit_ops import (  # noqa: F401
    get_head_sha,
    create_pull_request,
)
