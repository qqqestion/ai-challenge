"""
Stub tools for GitHub MCP server.

These are mock implementations that return example data.
In the future, these will be replaced with real GitHub API calls.
"""

import logging
from typing import Any

logger = logging.getLogger("github-mcp-server.tools")


async def get_user(username: str) -> dict[str, Any]:
    """
    Get GitHub user information.

    Args:
        username: GitHub username

    Returns:
        User information (stub data)
    """
    logger.debug(f"get_user() called with username={username}")
    return {
        "_stub": True,
        "_note": "This is mock data. Real GitHub API integration coming soon.",
        "login": username,
        "id": 12345678,
        "name": f"Mock User {username}",
        "email": f"{username}@example.com",
        "bio": "This is a mock GitHub user profile",
        "public_repos": 42,
        "followers": 100,
        "following": 50,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2024-12-16T00:00:00Z",
        "html_url": f"https://github.com/{username}",
    }


async def get_user_repos(username: str, limit: int = 10) -> dict[str, Any]:
    """
    Get list of user's repositories.

    Args:
        username: GitHub username
        limit: Maximum number of repositories to return

    Returns:
        List of repositories (stub data)
    """
    logger.debug(f"get_user_repos() called with username={username}, limit={limit}")
    repos = [
        {
            "id": i,
            "name": f"repo-{i}",
            "full_name": f"{username}/repo-{i}",
            "description": f"Mock repository #{i} description",
            "html_url": f"https://github.com/{username}/repo-{i}",
            "stars": 10 * i,
            "forks": 5 * i,
            "language": ["Python", "JavaScript", "Go", "Rust"][i % 4],
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-12-16T00:00:00Z",
            "open_issues": i * 2,
        }
        for i in range(1, min(limit, 10) + 1)
    ]

    return {
        "_stub": True,
        "_note": "This is mock data. Real GitHub API integration coming soon.",
        "username": username,
        "total_count": len(repos),
        "repositories": repos,
    }


async def get_repo_info(owner: str, repo: str) -> dict[str, Any]:
    """
    Get detailed information about a repository.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        Repository information (stub data)
    """
    logger.debug(f"get_repo_info() called with owner={owner}, repo={repo}")
    return {
        "_stub": True,
        "_note": "This is mock data. Real GitHub API integration coming soon.",
        "id": 987654321,
        "name": repo,
        "full_name": f"{owner}/{repo}",
        "owner": {
            "login": owner,
            "id": 12345678,
            "html_url": f"https://github.com/{owner}",
        },
        "description": f"Mock description for {repo}",
        "html_url": f"https://github.com/{owner}/{repo}",
        "stars": 1234,
        "watchers": 567,
        "forks": 89,
        "open_issues": 15,
        "language": "Python",
        "license": "MIT",
        "default_branch": "main",
        "created_at": "2022-01-01T00:00:00Z",
        "updated_at": "2024-12-16T00:00:00Z",
        "pushed_at": "2024-12-15T10:30:00Z",
        "size": 5678,
        "topics": ["python", "bot", "telegram", "ai"],
    }


async def search_repos(query: str, limit: int = 10) -> dict[str, Any]:
    """
    Search for repositories by query.

    Args:
        query: Search query
        limit: Maximum number of results to return

    Returns:
        Search results (stub data)
    """
    logger.debug(f"search_repos() called with query={query}, limit={limit}")
    results = [
        {
            "id": i,
            "name": f"{query}-project-{i}",
            "full_name": f"user{i}/{query}-project-{i}",
            "description": f"Mock search result for '{query}' - project #{i}",
            "html_url": f"https://github.com/user{i}/{query}-project-{i}",
            "stars": 100 - i * 10,
            "language": ["Python", "JavaScript", "TypeScript", "Go"][i % 4],
            "updated_at": "2024-12-16T00:00:00Z",
        }
        for i in range(1, min(limit, 10) + 1)
    ]

    return {
        "_stub": True,
        "_note": "This is mock data. Real GitHub API integration coming soon.",
        "query": query,
        "total_count": len(results),
        "items": results,
    }


async def get_repo_issues(
    owner: str, repo: str, state: str = "open", limit: int = 10
) -> dict[str, Any]:
    """
    Get issues for a repository.

    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state (open, closed, all)
        limit: Maximum number of issues to return

    Returns:
        List of issues (stub data)
    """
    logger.debug(f"get_repo_issues() called with owner={owner}, repo={repo}, state={state}, limit={limit}")
    issues = [
        {
            "id": i,
            "number": i,
            "title": f"Mock Issue #{i}: Something needs attention",
            "body": f"This is a mock issue body for issue #{i}",
            "state": state if state != "all" else ("open" if i % 2 == 0 else "closed"),
            "html_url": f"https://github.com/{owner}/{repo}/issues/{i}",
            "user": {
                "login": f"user{i}",
                "html_url": f"https://github.com/user{i}",
            },
            "labels": [
                {"name": "bug", "color": "d73a4a"},
                {"name": "enhancement", "color": "a2eeef"},
            ][: i % 3],
            "comments": i * 2,
            "created_at": "2024-11-01T00:00:00Z",
            "updated_at": "2024-12-16T00:00:00Z",
        }
        for i in range(1, min(limit, 10) + 1)
    ]

    return {
        "_stub": True,
        "_note": "This is mock data. Real GitHub API integration coming soon.",
        "owner": owner,
        "repo": repo,
        "state": state,
        "total_count": len(issues),
        "issues": issues,
    }

