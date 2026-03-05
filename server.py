import os
import json
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Google Drive imports
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

load_dotenv()

# -------------------------------
# GitHub configuration
# -------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO  = os.getenv("GITHUB_REPO")

BASE = "https://api.github.com"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# -------------------------------
# Google Drive configuration
# -------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

def get_drive_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            "gcp-oauth-keys.json", SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("drive", "v3", credentials=creds)
    return service

# -------------------------------
# YouTube configuration
# -------------------------------
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_BASE = "https://www.googleapis.com/youtube/v3"


# -------------------------------
# MCP server
# -------------------------------
mcp = FastMCP("github-drive-youtube-mcp")


# -------------------------------
# GitHub tools
# -------------------------------
@mcp.tool()
async def get_recent_commits(top: int = 5) -> str:
    """Get the most recent commits from the GitHub repository."""

    url = f"{BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/commits"

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS, params={"per_page": top})

    if r.status_code != 200:
        return json.dumps({"error": r.text})

    commits = r.json()

    result = [
        {
            "sha": c["sha"][:7],
            "message": c["commit"]["message"],
            "author": c["commit"]["author"]["name"],
            "date": c["commit"]["author"]["date"],
        }
        for c in commits
    ]

    return json.dumps(result, indent=2)


@mcp.tool()
async def list_repo_files() -> str:
    """List files and folders in the GitHub repository root."""

    url = f"{BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents"

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=HEADERS)

    if r.status_code != 200:
        return json.dumps({"error": r.text})

    files = r.json()

    result = [
        {
            "name": f["name"],
            "type": f["type"],
            "path": f["path"],
        }
        for f in files
    ]

    return json.dumps(result, indent=2)


# -------------------------------
# Google Drive tools
# -------------------------------
@mcp.tool()
async def list_drive_files() -> str:
    """List files from Google Drive."""

    service = get_drive_service()

    results = service.files().list(
        pageSize=10,
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    return json.dumps(files, indent=2)


# -------------------------------
# YouTube tools
# -------------------------------
@mcp.tool()
async def search_youtube_videos(query: str, max_results: int = 5) -> str:
    """Search for YouTube videos by keyword."""

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{YOUTUBE_BASE}/search", params={
            "part": "snippet",
            "q": query,
            "maxResults": max_results,
            "type": "video",
            "key": YOUTUBE_API_KEY
        })

    if r.status_code != 200:
        return json.dumps({"error": r.text})

    items = r.json().get("items", [])

    return json.dumps([{
        "title": i["snippet"]["title"],
        "videoId": i["id"]["videoId"],
        "url": f"https://www.youtube.com/watch?v={i['id']['videoId']}",
        "channel": i["snippet"]["channelTitle"],
        "description": i["snippet"]["description"][:150]
    } for i in items], indent=2)


@mcp.tool()
async def get_video_details(video_id: str) -> str:
    """Get detailed info and stats of a YouTube video by its ID."""

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{YOUTUBE_BASE}/videos", params={
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY
        })

    if r.status_code != 200:
        return json.dumps({"error": r.text})

    items = r.json().get("items", [])

    if not items:
        return json.dumps({"error": "Video not found"})

    v = items[0]

    return json.dumps({
        "title": v["snippet"]["title"],
        "channel": v["snippet"]["channelTitle"],
        "publishedAt": v["snippet"]["publishedAt"],
        "duration": v["contentDetails"]["duration"],
        "views": v["statistics"].get("viewCount"),
        "likes": v["statistics"].get("likeCount"),
        "comments": v["statistics"].get("commentCount"),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "description": v["snippet"]["description"][:300]
    }, indent=2)


@mcp.tool()
async def get_channel_details(channel_id: str) -> str:
    """Get details and stats of a YouTube channel by its ID."""

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{YOUTUBE_BASE}/channels", params={
            "part": "snippet,statistics",
            "id": channel_id,
            "key": YOUTUBE_API_KEY
        })

    if r.status_code != 200:
        return json.dumps({"error": r.text})

    items = r.json().get("items", [])

    if not items:
        return json.dumps({"error": "Channel not found"})

    c = items[0]

    return json.dumps({
        "name": c["snippet"]["title"],
        "description": c["snippet"]["description"][:200],
        "subscribers": c["statistics"].get("subscriberCount"),
        "totalVideos": c["statistics"].get("videoCount"),
        "totalViews": c["statistics"].get("viewCount"),
    }, indent=2)


# -------------------------------
# Run MCP server
# -------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")