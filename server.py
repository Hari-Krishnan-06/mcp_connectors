#==============================================================================================
# DESCRIPTION : FastMCP server for GitHub, Google Drive, YouTube, Gmail and LinkedIn APIs.
#               Tools are modularized inside the connectors/ package.
#==============================================================================================

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from connectors import register_github_tools, register_gdrive_tools, register_youtube_tools, register_gmail_tools, register_linkedin_tools  # ← ADD register_linkedin_tools

# ─────────────────────────────────────────────────────────
# Initialize MCP server
# ─────────────────────────────────────────────────────────
mcp = FastMCP("github-drive-youtube-mcp")

# ─────────────────────────────────────────────────────────
# Register all tool modules
# ─────────────────────────────────────────────────────────
register_github_tools(mcp)
register_gdrive_tools(mcp)
register_youtube_tools(mcp)
register_gmail_tools(mcp)
register_linkedin_tools(mcp)  # ← ADD THIS

# ─────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")