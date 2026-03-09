#==============================================================================================
# DESCRIPTION : Google Drive MCP tools and OAuth authentication logic
#==============================================================================================

import os
import json
import asyncio
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

GCP_OAUTH_FILE   = os.path.join(MCP_DIR, "gcp-oauth-keys.json")
DRIVE_TOKEN_FILE = os.path.join(MCP_DIR, "token.json")

# ─────────────────────────────────────────────────────────
# Google Drive configuration
# ─────────────────────────────────────────────────────────
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]


def get_drive_service():
    """Returns an authenticated Google Drive service using absolute paths."""
    creds = None

    if os.path.exists(DRIVE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(DRIVE_TOKEN_FILE, DRIVE_SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(DRIVE_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"Drive token refresh failed: {e}. Re-authenticating...")
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(GCP_OAUTH_FILE):
            raise FileNotFoundError(f"gcp-oauth-keys.json not found at: {GCP_OAUTH_FILE}")
        flow  = InstalledAppFlow.from_client_secrets_file(GCP_OAUTH_FILE, DRIVE_SCOPES)
        creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
        with open(DRIVE_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def register_gdrive_tools(mcp: FastMCP):

    @mcp.tool()
    async def list_drive_files(max_files: int = 10) -> str:
        """List files from your Google Drive."""
        try:
            loop    = asyncio.get_event_loop()
            service = await loop.run_in_executor(None, get_drive_service)

            results = service.files().list(
                pageSize=max_files,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()

            files = results.get("files", [])
            if not files:
                return json.dumps({"message": "No files found in Google Drive."})

            return json.dumps(files, indent=2)

        except FileNotFoundError as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": f"Google Drive error: {str(e)}"})