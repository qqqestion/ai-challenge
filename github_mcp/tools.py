"""
GitHub API integration tools.

Provides real GitHub API calls using httpx and personal access token.
"""

import logging
import os
from dataclasses import asdict, dataclass
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
BINARY_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".zip",
    ".tar",
    ".gz",
    ".xz",
    ".bz2",
    ".7z",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".class",
    ".o",
    ".so",
    ".dylib",
    ".dll",
)
LOCK_FILE_SUFFIXES = (
    ".lock",
    ".lock.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
)
DEFAULT_MAX_FILE_SIZE = 200_000  # 200 KB safety limit for text content


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


def _is_binary_filename(filename: str) -> bool:
    """Return True if filename looks like binary/asset file."""
    lower = filename.lower()
    return lower.endswith(BINARY_EXTENSIONS)


def _is_lock_file(filename: str) -> bool:
    """Return True if filename is a lock/metadata file."""
    lower = filename.lower()
    return any(lower.endswith(suffix) for suffix in LOCK_FILE_SUFFIXES)


async def _fetch_file_content(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    ref: str,
    max_file_size: int,
) -> tuple[str | None, str | None]:
    """Fetch raw file content for a specific ref with safety checks.

    Returns:
        Tuple (content, error). Error is None on success.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    headers = get_headers()
    headers["Accept"] = "application/vnd.github.v3.raw"

    try:
        response = await client.get(
            url,
            headers=headers,
            params={"ref": ref},
            timeout=15.0,
        )
        response.raise_for_status()

        content_bytes = response.content
        if len(content_bytes) > max_file_size:
            return None, "too_large"

        try:
            return content_bytes.decode("utf-8"), None
        except UnicodeDecodeError:
            return None, "binary_or_non_utf8"

    except httpx.HTTPStatusError as exc:
        logger.error(
            "HTTP error fetching content %s at %s: %s",
            path,
            ref,
            exc.response.status_code,
        )
        if exc.response.status_code == 404:
            return None, "not_found"
        if exc.response.status_code in (401, 403):
            return None, "forbidden"
        return None, f"http_error_{exc.response.status_code}"
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Unexpected error fetching %s: %s", path, exc, exc_info=True)
        return None, "unexpected_error"


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


async def get_pull_request_files(
    owner: str,
    repo: str,
    pull_number: int,
    include_contents: bool = True,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> dict[str, Any]:
    """
    Get PR metadata, changed files, patches, and optionally full file contents.

    Args:
        owner: Repository owner
        repo: Repository name
        pull_number: Pull request number
        include_contents: Whether to fetch full file content for text files
        max_file_size: Max allowed size (bytes) for content fetch

    Returns:
        Dictionary with pull request info and file details.
    """
    pr_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pull_number}"
    files_url = f"{pr_url}/files"

    async with httpx.AsyncClient() as client:
        try:
            pr_response = await client.get(pr_url, headers=get_headers(), timeout=15.0)
            pr_response.raise_for_status()
            pr_data = pr_response.json()
            head_sha = pr_data.get("head", {}).get("sha")
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.error(
                "HTTP error fetching PR %s/%s#%s: %s",
                owner,
                repo,
                pull_number,
                status,
            )
            if status in (401, 403):
                return {"error": "access_forbidden"}
            if status == 404:
                return {"error": "pull_request_not_found"}
            return {"error": f"http_error_{status}"}
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error fetching PR %s/%s#%s: %s", owner, repo, pull_number, exc)
            return {"error": "unexpected_error"}

        files: list[dict[str, Any]] = []
        page = 1
        while True:
            try:
                resp = await client.get(
                    files_url,
                    headers=get_headers(),
                    params={"per_page": 100, "page": page},
                    timeout=15.0,
                )
                resp.raise_for_status()
                batch = resp.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                logger.error(
                    "HTTP error fetching PR files %s/%s#%s page %s: %s",
                    owner,
                    repo,
                    pull_number,
                    page,
                    status,
                )
                return {"error": f"http_error_{status}"}
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Error fetching PR files page %s: %s", page, exc)
                return {"error": "unexpected_error"}

            if not batch:
                break

            for file_data in batch:
                filename = file_data.get("filename", "")
                file_entry: dict[str, Any] = {
                    "filename": filename,
                    "status": file_data.get("status"),
                    "additions": file_data.get("additions"),
                    "deletions": file_data.get("deletions"),
                    "changes": file_data.get("changes"),
                    "patch": file_data.get("patch"),
                    "sha": file_data.get("sha"),
                    "blob_url": file_data.get("blob_url"),
                    "raw_url": file_data.get("raw_url"),
                    "skip_reason": None,
                }

                if _is_binary_filename(filename):
                    file_entry["skip_reason"] = "binary_file"
                elif _is_lock_file(filename):
                    file_entry["skip_reason"] = "lock_file"
                elif file_entry["patch"] is None:
                    file_entry["skip_reason"] = "patch_not_available"

                if include_contents and not file_entry["skip_reason"] and head_sha:
                    content, error = await _fetch_file_content(
                        client=client,
                        owner=owner,
                        repo=repo,
                        path=filename,
                        ref=head_sha,
                        max_file_size=max_file_size,
                    )
                    if error:
                        file_entry["skip_reason"] = error
                    else:
                        file_entry["content"] = content

                files.append(file_entry)

            if "next" not in resp.links:
                break
            page += 1

    return {
        "pull_request": {
            "number": pull_number,
            "title": pr_data.get("title"),
            "author": pr_data.get("user", {}).get("login"),
            "state": pr_data.get("state"),
            "url": pr_data.get("html_url"),
            "head": {
                "ref": pr_data.get("head", {}).get("ref"),
                "sha": pr_data.get("head", {}).get("sha"),
                "label": pr_data.get("head", {}).get("label"),
            },
            "base": {
                "ref": pr_data.get("base", {}).get("ref"),
                "sha": pr_data.get("base", {}).get("sha"),
                "label": pr_data.get("base", {}).get("label"),
            },
            "files": files,
        }
    }
