import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import claude_key, db, quotas, repo_connections
from app.auth import AuthError, api_tokens
from app.auth.deps import CurrentViewer

router = APIRouter(prefix="/account", tags=["account"])


class ClaudeKeyStatus(BaseModel):
    provider: str
    # The last characters of the key, e.g. "…a1b2"; the key itself is never returned.
    hint: str
    updated_at: float


class ConnectClaudeRequest(BaseModel):
    api_key: str


# How far back the account page adds up AI tokens.
AI_USAGE_DAYS = 30


class AIUsage(BaseModel):
    """AI tokens over the last AI_USAGE_DAYS days, from scans still in history."""

    days: int
    scans: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int


def ai_usage(owner_id: str | None) -> AIUsage:
    totals = db.ai_token_totals(since=time.time() - AI_USAGE_DAYS * 86400, owner_id=owner_id)
    return AIUsage(days=AI_USAGE_DAYS, **totals)


class UsageResponse(BaseModel):
    scans_paused: bool
    # False for admins, and without accounts: no quota applies to them.
    quotas_apply: bool
    # Scans started in the last 24 hours, including deleted ones.
    scans_today: int
    daily_scan_quota: int | None
    active_scans: int
    concurrent_scan_quota: int | None
    # Everyone's, without accounts.
    ai_usage: AIUsage


def _signed_in_user(viewer) -> dict:
    if viewer.user is None or not claude_key.available():
        raise HTTPException(status_code=404, detail="Saving a Claude key isn't available on this server")
    return viewer.user


@router.get("/claude", response_model=ClaudeKeyStatus | None)
def read_claude_key(viewer: CurrentViewer) -> ClaudeKeyStatus | None:
    status = claude_key.status(_signed_in_user(viewer)["id"])
    return ClaudeKeyStatus(**status) if status else None


@router.put("/claude", response_model=ClaudeKeyStatus)
def connect_claude(req: ConnectClaudeRequest, viewer: CurrentViewer) -> ClaudeKeyStatus:
    """Check the key with Anthropic, then save it encrypted, replacing any earlier one."""
    try:
        return ClaudeKeyStatus(**claude_key.connect(_signed_in_user(viewer), req.api_key))
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/claude", status_code=204)
def disconnect_claude(viewer: CurrentViewer) -> None:
    claude_key.disconnect(_signed_in_user(viewer))


@router.get("/usage", response_model=UsageResponse)
def read_usage(viewer: CurrentViewer) -> UsageResponse:
    usage = quotas.usage(viewer)
    return UsageResponse(
        scans_paused=usage.limits.paused,
        quotas_apply=usage.applies,
        scans_today=usage.scans_today,
        daily_scan_quota=usage.limits.daily,
        active_scans=usage.active_scans,
        concurrent_scan_quota=usage.limits.concurrent,
        ai_usage=ai_usage(viewer.user_id),
    )


# Personal API tokens (app/auth/api_tokens.py), for scripts and CI.


class ApiToken(BaseModel):
    id: str
    name: str
    # The token's first characters, e.g. "sst_a1B2c3", to tell tokens apart; never the token.
    prefix: str
    scopes: list[str]
    created_at: float
    expires_at: float | None
    last_used_at: float | None


class CreateTokenRequest(BaseModel):
    name: str = Field(max_length=200)
    # None: until it's revoked.
    expires_in_days: int | None = Field(default=90, ge=1, le=366)


class CreatedToken(ApiToken):
    # Shown this once; only its hash is kept.
    token: str


def _token_owner(viewer) -> dict:
    if viewer.user is None:
        raise HTTPException(status_code=404, detail="API tokens need accounts to be turned on on this server")
    return viewer.user


@router.get("/tokens", response_model=list[ApiToken])
def list_tokens(viewer: CurrentViewer) -> list[ApiToken]:
    return [ApiToken(**api_tokens.public_token(row)) for row in db.list_api_tokens(_token_owner(viewer)["id"])]


@router.post("/tokens", response_model=CreatedToken, status_code=201)
def create_token(req: CreateTokenRequest, viewer: CurrentViewer) -> CreatedToken:
    try:
        token, listed = api_tokens.create(_token_owner(viewer), name=req.name, expires_in_days=req.expires_in_days)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CreatedToken(token=token, **listed)


@router.delete("/tokens/{token_id}", status_code=204)
def revoke_token(token_id: str, viewer: CurrentViewer) -> None:
    owner = _token_owner(viewer)
    try:
        api_tokens.revoke(owner, owner, token_id)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


# Code host connections, to scan private repositories (app/repo_connections.py).


class RepoConnection(BaseModel):
    provider: str
    account_name: str
    connected_at: float


class GitHubConnectionStatus(BaseModel):
    # False until the server has a GitHub App set up (and accounts, SECRET_KEY, PUBLIC_URL).
    available: bool
    # Where to choose which repositories the app may read.
    manage_url: str | None
    connection: RepoConnection | None


class ConnectionsResponse(BaseModel):
    github: GitHubConnectionStatus


class StartConnectionResponse(BaseModel):
    url: str


class CompleteConnectionRequest(BaseModel):
    code: str = Field(min_length=1, max_length=512)
    state: str = Field(min_length=1, max_length=4096)


def _connecting_user(viewer) -> dict:
    if viewer.user is None or not repo_connections.available():
        raise HTTPException(status_code=404, detail="Connecting GitHub isn't available on this server")
    return viewer.user


@router.get("/connections", response_model=ConnectionsResponse)
def read_connections(viewer: CurrentViewer) -> ConnectionsResponse:
    connections = {row["provider"]: row for row in repo_connections.status(viewer.user["id"])} if viewer.user else {}
    github = connections.get(repo_connections.GITHUB)
    return ConnectionsResponse(
        github=GitHubConnectionStatus(
            available=repo_connections.available(),
            manage_url=repo_connections.manage_url(),
            connection=RepoConnection(**github) if github else None,
        )
    )


@router.get("/connections/github/start", response_model=StartConnectionResponse)
def start_github_connection(viewer: CurrentViewer) -> StartConnectionResponse:
    """GitHub's page to authorize the app; it sends the browser back to the callback."""
    return StartConnectionResponse(url=repo_connections.start_url(_connecting_user(viewer)["id"]))


@router.post("/connections/github/callback", response_model=RepoConnection)
def complete_github_connection(req: CompleteConnectionRequest, viewer: CurrentViewer) -> RepoConnection:
    try:
        return RepoConnection(**repo_connections.complete(_connecting_user(viewer), code=req.code, state=req.state))
    except repo_connections.ConnectionFailedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class GitHubRepository(BaseModel):
    full_name: str
    url: str
    private: bool
    description: str | None


class RepositoriesResponse(BaseModel):
    repositories: list[GitHubRepository]
    # True when there were more than the list holds (repo_connections.MAX_LISTED_REPOSITORIES).
    truncated: bool


@router.get("/connections/github/repositories", response_model=RepositoriesResponse)
def list_github_repositories(viewer: CurrentViewer) -> RepositoriesResponse:
    """The repositories the user's connection reads, to pick one to scan."""
    try:
        found, truncated = repo_connections.repositories(_connecting_user(viewer)["id"])
    except repo_connections.NoAccessError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RepositoriesResponse(repositories=[GitHubRepository(**repo) for repo in found], truncated=truncated)


@router.delete("/connections/github", status_code=204)
def disconnect_github(viewer: CurrentViewer) -> None:
    """Delete the GitHub tokens: private repositories can't be scanned until connecting again."""
    repo_connections.disconnect(_connecting_user(viewer))
