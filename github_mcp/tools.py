"""
GitHub API integration tools.

Provides real GitHub API calls using httpx and personal access token.
"""

import logging
import os
from dataclasses import dataclass, asdict
from typing import Any

import httpx
from dotenv import load_dotenv

logger = logging.getLogger("github-mcp-server.tools")

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_TOKEN")

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


def get_headers() -> dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


@dataclass
class UserInfo:
    """Minimal user information from GitHub."""

    login: str
    id: int
    name: str | None
    bio: str | None
    public_repos: int
    followers: int
    following: int
    html_url: str
    avatar_url: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RepositoryInfo:
    """Minimal repository information from GitHub."""

    name: str
    full_name: str
    description: str | None
    html_url: str
    stargazers_count: int
    forks_count: int
    language: str | None
    open_issues_count: int
    created_at: str
    updated_at: str
    default_branch: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class UserReposResponse:
    """Response for user repositories list."""

    username: str
    total_count: int
    repositories: list[RepositoryInfo]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "username": self.username,
            "total_count": self.total_count,
            "repositories": [repo.to_dict() for repo in self.repositories],
        }

@dataclass
class CommitInfo:
    author_login: str
    message: str
    sha: str
    commit_date: str
    parents: list[str]


@dataclass
class ActorInfo:
    """Actor information from GitHub event."""

    login: str
    id: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RepoReference:
    """Repository reference from GitHub event."""

    id: int
    name: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EventInfo:
    """GitHub event information."""

    id: str
    type: str
    actor: ActorInfo
    repo: RepoReference
    payload: dict[str, Any]
    public: bool
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "actor": self.actor.to_dict(),
            "repo": self.repo.to_dict(),
            "payload": self.payload,
            "public": self.public,
            "created_at": self.created_at,
        }


@dataclass
class UserEventsResponse:
    """Response for user events list."""

    username: str
    total_count: int
    events: list[EventInfo]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "username": self.username,
            "total_count": self.total_count,
            "events": [event.to_dict() for event in self.events],
        }


@dataclass
class RepoEventsResponse:
    """Response for repository events list."""

    owner: str
    repo: str
    total_count: int
    events: list[EventInfo]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "owner": self.owner,
            "repo": self.repo,
            "total_count": self.total_count,
            "events": [event.to_dict() for event in self.events],
        }


async def get_user(username: str) -> dict[str, Any]:
    """
    Get information about a GitHub user.

    Args:
        username: GitHub username to look up

    Returns:
        User information dictionary
    """
    logger.debug(f"get_user() called with username={username}")

    url = f"{GITHUB_API_BASE}/users/{username}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers(), timeout=10.0)
            response.raise_for_status()

            data = response.json()

            user_info = UserInfo(
                login=data["login"],
                id=data["id"],
                name=data.get("name"),
                bio=data.get("bio"),
                public_repos=data["public_repos"],
                followers=data["followers"],
                following=data["following"],
                html_url=data["html_url"],
                avatar_url=data["avatar_url"],
                created_at=data["created_at"],
            )

            logger.info(f"Successfully fetched user: {username}")
            return user_info.to_dict()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching user {username}: {e.response.status_code}")
            if e.response.status_code == 404:
                return {"error": f"User '{username}' not found"}
            elif e.response.status_code == 403:
                return {"error": "Rate limit exceeded or access forbidden"}
            else:
                return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching user {username}: {e}")
            return {"error": str(e)}


async def get_user_repos(username: str, limit: int = 10) -> dict[str, Any]:
    """
    Get list of repositories for a GitHub user.

    Args:
        username: GitHub username
        limit: Maximum number of repositories to return (default: 10)

    Returns:
        User repositories information
    """
    logger.debug(f"get_user_repos() called with username={username}, limit={limit}")

    url = f"{GITHUB_API_BASE}/users/{username}/repos"
    params = {
        "per_page": min(limit, 100),
        "sort": "updated",
        "direction": "desc",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, headers=get_headers(), params=params, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()

            repositories = []
            for repo_data in data[:limit]:
                repo_info = RepositoryInfo(
                    name=repo_data["name"],
                    full_name=repo_data["full_name"],
                    description=repo_data.get("description"),
                    html_url=repo_data["html_url"],
                    stargazers_count=repo_data["stargazers_count"],
                    forks_count=repo_data["forks_count"],
                    language=repo_data.get("language"),
                    open_issues_count=repo_data["open_issues_count"],
                    created_at=repo_data["created_at"],
                    updated_at=repo_data["updated_at"],
                    default_branch=repo_data["default_branch"],
                )
                repositories.append(repo_info)

            result = UserReposResponse(
                username=username,
                total_count=len(repositories),
                repositories=repositories,
            )

            logger.info(
                f"Successfully fetched {len(repositories)} repositories for user: {username}"
            )
            return result.to_dict()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching repos for {username}: {e.response.status_code}"
            )
            if e.response.status_code == 404:
                return {"error": f"User '{username}' not found"}
            elif e.response.status_code == 403:
                return {"error": "Rate limit exceeded or access forbidden"}
            else:
                return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching repos for {username}: {e}")
            return {"error": str(e)}


async def get_repo_info(owner: str, repo: str) -> dict[str, Any]:
    """
    Get detailed information about a specific repository.

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name

    Returns:
        Repository information dictionary
    """
    logger.debug(f"get_repo_info() called with owner={owner}, repo={repo}")

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers(), timeout=10.0)
            response.raise_for_status()

            data = response.json()

            repo_info = RepositoryInfo(
                name=data["name"],
                full_name=data["full_name"],
                description=data.get("description"),
                html_url=data["html_url"],
                stargazers_count=data["stargazers_count"],
                forks_count=data["forks_count"],
                language=data.get("language"),
                open_issues_count=data["open_issues_count"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                default_branch=data["default_branch"],
            )

            logger.info(f"Successfully fetched repo: {owner}/{repo}")
            return repo_info.to_dict()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching repo {owner}/{repo}: {e.response.status_code}"
            )
            if e.response.status_code == 404:
                return {"error": f"Repository '{owner}/{repo}' not found"}
            elif e.response.status_code == 403:
                return {"error": "Rate limit exceeded or access forbidden"}
            else:
                return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching repo {owner}/{repo}: {e}")
            return {"error": str(e)}


async def get_user_events(username: str, limit: int = 30) -> dict[str, Any]:
    """
    Get list of events for a GitHub user.

    Args:
        username: GitHub username
        limit: Maximum number of events to return (default: 30, max: 100)

    Returns:
        User events information
    """
    logger.debug(f"get_user_events() called with username={username}, limit={limit}")

    url = f"{GITHUB_API_BASE}/users/{username}/events"
    params = {
        "per_page": min(limit, 100),
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, headers=get_headers(), params=params, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()

            events = []
            for event_data in data[:limit]:
                actor_info = ActorInfo(
                    login=event_data["actor"]["login"],
                    id=event_data["actor"]["id"],
                )

                repo_ref = RepoReference(
                    id=event_data["repo"]["id"],
                    name=event_data["repo"]["name"],
                    url=event_data["repo"]["url"],
                )

                event_info = EventInfo(
                    id=event_data["id"],
                    type=event_data["type"],
                    actor=actor_info,
                    repo=repo_ref,
                    payload=event_data.get("payload", {}),
                    public=event_data["public"],
                    created_at=event_data["created_at"],
                )
                events.append(event_info)

            result = UserEventsResponse(
                username=username,
                total_count=len(events),
                events=events,
            )

            logger.info(
                f"Successfully fetched {len(events)} events for user: {username}"
            )
            return result.to_dict()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching events for {username}: {e.response.status_code}"
            )
            if e.response.status_code == 404:
                return {"error": f"User '{username}' not found"}
            elif e.response.status_code == 403:
                return {"error": "Rate limit exceeded or access forbidden"}
            else:
                return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching events for {username}: {e}")
            return {"error": str(e)}


async def get_repo_events(owner: str, repo: str, limit: int = 30) -> dict[str, Any]:
    """
    Get list of events for a GitHub repository.

    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        limit: Maximum number of events to return (default: 30, max: 100)

    Returns:
        Repository events information
    """
    logger.debug(
        f"get_repo_events() called with owner={owner}, repo={repo}, limit={limit}"
    )

    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/events"
    params = {
        "per_page": min(limit, 100),
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, headers=get_headers(), params=params, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()

            events = []
            for event_data in data[:limit]:
                actor_info = ActorInfo(
                    login=event_data["actor"]["login"],
                    id=event_data["actor"]["id"],
                )

                repo_ref = RepoReference(
                    id=event_data["repo"]["id"],
                    name=event_data["repo"]["name"],
                    url=event_data["repo"]["url"],
                )

                event_info = EventInfo(
                    id=event_data["id"],
                    type=event_data["type"],
                    actor=actor_info,
                    repo=repo_ref,
                    payload=event_data.get("payload", {}),
                    public=event_data["public"],
                    created_at=event_data["created_at"],
                )
                events.append(event_info)

            result = RepoEventsResponse(
                owner=owner,
                repo=repo,
                total_count=len(events),
                events=events,
            )

            logger.info(
                f"Successfully fetched {len(events)} events for repo: {owner}/{repo}"
            )
            return result.to_dict()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching events for {owner}/{repo}: {e.response.status_code}"
            )
            if e.response.status_code == 404:
                return {"error": f"Repository '{owner}/{repo}' not found"}
            elif e.response.status_code == 403:
                return {"error": "Rate limit exceeded or access forbidden"}
            else:
                return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching events for {owner}/{repo}: {e}")
            return {"error": str(e)}
