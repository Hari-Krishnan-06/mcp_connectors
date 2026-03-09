#==============================================================================================
# DESCRIPTION : GitHub MCP tools - Full Account Access
#==============================================================================================

import os
import json
import httpx
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────────────────
# GitHub configuration
# ─────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")  # Your GitHub username

BASE    = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def register_github_tools(mcp: FastMCP):

    # ─────────────────────────────────────────────────────────
    # NEW: List ALL repos in your GitHub account
    # ─────────────────────────────────────────────────────────
    @mcp.tool()
    async def list_all_repos(repo_type: str = "all") -> str:
        """List all repositories in your GitHub account.
        repo_type: 'all', 'public', 'private', 'forks', 'sources'
        """
        if not GITHUB_TOKEN or not GITHUB_OWNER:
            return json.dumps({"error": "GitHub env vars missing: GITHUB_TOKEN, GITHUB_OWNER"})

        url = f"{BASE}/users/{GITHUB_OWNER}/repos"
        all_repos = []
        page = 1

        async with httpx.AsyncClient() as client:
            while True:
                r = await client.get(url, headers=HEADERS, params={
                    "type": repo_type,
                    "per_page": 100,
                    "page": page
                })

                if r.status_code == 401:
                    return json.dumps({"error": "GitHub token is invalid or expired."})
                if r.status_code != 200:
                    return json.dumps({"error": r.text})

                repos = r.json()
                if not repos:
                    break

                all_repos.extend([{
                    "name":        repo["name"],
                    "full_name":   repo["full_name"],
                    "description": repo["description"],
                    "private":     repo["private"],
                    "language":    repo["language"],
                    "stars":       repo["stargazers_count"],
                    "updated_at":  repo["updated_at"],
                    "url":         repo["html_url"],
                } for repo in repos])
                page += 1

        return json.dumps(all_repos, indent=2)


    # ─────────────────────────────────────────────────────────
    # NEW: Get commits from ANY repo
    # ─────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_repo_commits(repo: str, top: int = 5) -> str:
        """Get recent commits from any repository in your account.
        
        Args:
            repo: Repository name (e.g., 'my-project')
            top: Number of commits to fetch (default 5)
        """
        if not GITHUB_TOKEN or not GITHUB_OWNER:
            return json.dumps({"error": "GitHub env vars missing."})

        url = f"{BASE}/repos/{GITHUB_OWNER}/{repo}/commits"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=HEADERS, params={"per_page": top})

        if r.status_code == 401:
            return json.dumps({"error": "GitHub token is invalid or expired."})
        if r.status_code == 404:
            return json.dumps({"error": f"Repo '{GITHUB_OWNER}/{repo}' not found."})
        if r.status_code != 200:
            return json.dumps({"error": r.text})

        return json.dumps([{
            "sha":     c["sha"][:7],
            "message": c["commit"]["message"],
            "author":  c["commit"]["author"]["name"],
            "date":    c["commit"]["author"]["date"],
        } for c in r.json()], indent=2)


    # ─────────────────────────────────────────────────────────
    # NEW: List files from ANY repo
    # ─────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_repo_files(repo: str, path: str = "") -> str:
        """List files and folders from any repository in your account.
        
        Args:
            repo: Repository name (e.g., 'my-project')
            path: Subfolder path to explore (default: root)
        """
        if not GITHUB_TOKEN or not GITHUB_OWNER:
            return json.dumps({"error": "GitHub env vars missing."})

        url = f"{BASE}/repos/{GITHUB_OWNER}/{repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=HEADERS)

        if r.status_code == 401:
            return json.dumps({"error": "GitHub token is invalid or expired."})
        if r.status_code == 404:
            return json.dumps({"error": f"Repo or path not found."})
        if r.status_code != 200:
            return json.dumps({"error": r.text})

        return json.dumps([{
            "name": f["name"],
            "type": f["type"],
            "path": f["path"]
        } for f in r.json()], indent=2)


    # ─────────────────────────────────────────────────────────
    # NEW: Search across all your repos
    # ─────────────────────────────────────────────────────────
    @mcp.tool()
    async def search_my_repos(query: str) -> str:
        """Search for repositories in your GitHub account by name or topic.
        
        Args:
            query: Search keyword (e.g., 'python', 'api', 'react')
        """
        if not GITHUB_TOKEN or not GITHUB_OWNER:
            return json.dumps({"error": "GitHub env vars missing."})

        url = f"{BASE}/search/repositories"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=HEADERS, params={
                "q": f"{query} user:{GITHUB_OWNER}",
                "per_page": 20
            })

        if r.status_code != 200:
            return json.dumps({"error": r.text})

        return json.dumps([{
            "name":        repo["name"],
            "description": repo["description"],
            "language":    repo["language"],
            "stars":       repo["stargazers_count"],
            "url":         repo["html_url"],
        } for repo in r.json().get("items", [])], indent=2)


    # ─────────────────────────────────────────────────────────
    # EXISTING: Keep old tools for backward compatibility
    # ─────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_recent_commits(top: int = 5) -> str:
        """Get recent commits from the default configured repository."""
        GITHUB_REPO = os.getenv("GITHUB_REPO")
        if not GITHUB_TOKEN or not GITHUB_OWNER or not GITHUB_REPO:
            return json.dumps({"error": "Set GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO in env vars."})

        url = f"{BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=HEADERS, params={"per_page": top})

        if r.status_code == 401:
            return json.dumps({"error": "GitHub token is invalid or expired."})
        if r.status_code == 404:
            return json.dumps({"error": f"Repo '{GITHUB_OWNER}/{GITHUB_REPO}' not found."})
        if r.status_code != 200:
            return json.dumps({"error": r.text})

        return json.dumps([{
            "sha":     c["sha"][:7],
            "message": c["commit"]["message"],
            "author":  c["commit"]["author"]["name"],
            "date":    c["commit"]["author"]["date"],
        } for c in r.json()], indent=2)


    @mcp.tool()
    async def list_repo_files(owner: str = "", repo: str = "") -> str:
        """List files and folders in a GitHub repository root."""
        GITHUB_REPO = os.getenv("GITHUB_REPO")
        _owner = owner or GITHUB_OWNER
        _repo  = repo  or GITHUB_REPO

        if not _owner or not _repo:
            return json.dumps({"error": "Provide owner/repo or set GITHUB_OWNER, GITHUB_REPO in env."})

        url = f"{BASE}/repos/{_owner}/{_repo}/contents"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=HEADERS)

        if r.status_code == 401:
            return json.dumps({"error": "GitHub token is invalid or expired."})
        if r.status_code == 404:
            return json.dumps({"error": f"Repo '{_owner}/{_repo}' not found."})
        if r.status_code != 200:
            return json.dumps({"error": r.text})

        return json.dumps([{
            "name": f["name"],
            "type": f["type"],
            "path": f["path"]
        } for f in r.json()], indent=2)
