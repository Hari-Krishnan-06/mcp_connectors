#==============================================================================================
# DESCRIPTION : YouTube MCP tools (API key for public data, OAuth for own channel)
#==============================================================================================

import os
import json
import asyncio
import httpx
from mcp.server.fastmcp import FastMCP

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ─────────────────────────────────────────────────────────
# Absolute paths — fixes "file not found" in Claude Desktop
# ─────────────────────────────────────────────────────────
MCP_DIR = os.getenv(
    "MCP_FILES_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

GCP_OAUTH_FILE = os.path.join(MCP_DIR, "gcp-oauth-keys.json")
YT_TOKEN_FILE  = os.path.join(MCP_DIR, "youtube_token.json")

# ─────────────────────────────────────────────────────────
# YouTube configuration
# ─────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_BASE    = "https://www.googleapis.com/youtube/v3"
YOUTUBE_SCOPES  = ["https://www.googleapis.com/auth/youtube.readonly"]


def get_youtube_oauth_service():
    """Returns an authenticated YouTube service using absolute paths."""
    creds = None

    if os.path.exists(YT_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(YT_TOKEN_FILE, YOUTUBE_SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(YT_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"YouTube token refresh failed: {e}. Re-authenticating...")
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(GCP_OAUTH_FILE):
            raise FileNotFoundError(f"gcp-oauth-keys.json not found at: {GCP_OAUTH_FILE}")
        flow  = InstalledAppFlow.from_client_secrets_file(GCP_OAUTH_FILE, YOUTUBE_SCOPES)
        creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
        with open(YT_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def register_youtube_tools(mcp: FastMCP):

    @mcp.tool()
    async def search_youtube_videos(query: str, max_results: int = 5) -> str:
        """Search for YouTube videos by keyword."""

        if not YOUTUBE_API_KEY:
            return json.dumps({"error": "YOUTUBE_API_KEY missing in claude_desktop.json"})

        async with httpx.AsyncClient() as client:
            r = await client.get(f"{YOUTUBE_BASE}/search", params={
                "part": "snippet", "q": query,
                "maxResults": max_results, "type": "video",
                "key": YOUTUBE_API_KEY
            })

        if r.status_code != 200:
            return json.dumps({"error": r.text})

        return json.dumps([{
            "title":       i["snippet"]["title"],
            "videoId":     i["id"]["videoId"],
            "url":         f"https://www.youtube.com/watch?v={i['id']['videoId']}",
            "channel":     i["snippet"]["channelTitle"],
            "description": i["snippet"]["description"][:150]
        } for i in r.json().get("items", [])], indent=2)


    @mcp.tool()
    async def get_video_details(video_id: str) -> str:
        """Get detailed info and stats of a YouTube video by its ID."""

        if not YOUTUBE_API_KEY:
            return json.dumps({"error": "YOUTUBE_API_KEY missing in claude_desktop.json"})

        async with httpx.AsyncClient() as client:
            r = await client.get(f"{YOUTUBE_BASE}/videos", params={
                "part": "snippet,statistics,contentDetails",
                "id": video_id, "key": YOUTUBE_API_KEY
            })

        if r.status_code != 200:
            return json.dumps({"error": r.text})

        items = r.json().get("items", [])
        if not items:
            return json.dumps({"error": "Video not found"})

        v = items[0]
        return json.dumps({
            "title":       v["snippet"]["title"],
            "channel":     v["snippet"]["channelTitle"],
            "publishedAt": v["snippet"]["publishedAt"],
            "duration":    v["contentDetails"]["duration"],
            "views":       v["statistics"].get("viewCount"),
            "likes":       v["statistics"].get("likeCount"),
            "comments":    v["statistics"].get("commentCount"),
            "url":         f"https://www.youtube.com/watch?v={video_id}",
            "description": v["snippet"]["description"][:300]
        }, indent=2)


    @mcp.tool()
    async def get_channel_details(channel_id: str) -> str:
        """Get details and stats of a YouTube channel by its ID."""

        if not YOUTUBE_API_KEY:
            return json.dumps({"error": "YOUTUBE_API_KEY missing in claude_desktop.json"})

        async with httpx.AsyncClient() as client:
            r = await client.get(f"{YOUTUBE_BASE}/channels", params={
                "part": "snippet,statistics",
                "id": channel_id, "key": YOUTUBE_API_KEY
            })

        if r.status_code != 200:
            return json.dumps({"error": r.text})

        items = r.json().get("items", [])
        if not items:
            return json.dumps({"error": "Channel not found"})

        c = items[0]
        return json.dumps({
            "name":        c["snippet"]["title"],
            "description": c["snippet"]["description"][:200],
            "subscribers": c["statistics"].get("subscriberCount"),
            "totalVideos": c["statistics"].get("videoCount"),
            "totalViews":  c["statistics"].get("viewCount"),
        }, indent=2)


    @mcp.tool()
    async def get_my_channel() -> str:
        """Get YOUR OWN YouTube channel name and stats using OAuth."""
        try:
            loop    = asyncio.get_event_loop()
            youtube = await loop.run_in_executor(None, get_youtube_oauth_service)

            req      = youtube.channels().list(part="snippet,statistics", mine=True)
            response = await loop.run_in_executor(None, req.execute)

            items = response.get("items", [])
            if not items:
                return json.dumps({"error": "No YouTube channel found for this account."})

            c = items[0]
            return json.dumps({
                "channelId":   c["id"],
                "name":        c["snippet"]["title"],
                "description": c["snippet"]["description"][:300],
                "subscribers": c["statistics"].get("subscriberCount"),
                "totalVideos": c["statistics"].get("videoCount"),
                "totalViews":  c["statistics"].get("viewCount"),
            }, indent=2)

        except FileNotFoundError as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": f"YouTube OAuth error: {str(e)}"})