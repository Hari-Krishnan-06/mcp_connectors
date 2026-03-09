# mcp_connectors

## Overview
mcp_connectors is a Python-based MCP (Model Context Protocol) server that integrates multiple third-party service connectors into a unified interface. It enables seamless interaction with popular platforms like Google Drive, Gmail, GitHub, LinkedIn, and YouTube through a single server entry point.

---

## Project Structure

mcp_connectors/
│
├── server.py                  # Main MCP server entry point
├── .gitignore
└── connectors/
    ├── __init__.py            # Connector package initializer
    ├── gdrive.py              # Google Drive connector
    ├── gmail.py               # Gmail connector
    ├── github.py              # GitHub connector
    ├── linkedin.py            # LinkedIn connector
    └── youtube.py             # YouTube connector

---

## Connectors

### Google Drive (gdrive.py)
- List, search, and fetch files from Google Drive.

### Gmail (gmail.py)
- Read, search, and send emails via Gmail.

### GitHub (github.py)
- List repositories, browse files, and retrieve commit history.

### LinkedIn (linkedin.py)
- Fetch profile details, profile pictures, and post updates.

### YouTube (youtube.py)
- Search videos, retrieve video/channel details, and access your own channel stats.

---

## Setup & Installation

1. Clone the repository:
   git clone https://github.com/<your-username>/mcp_connectors.git
   cd mcp_connectors

2. Install dependencies:
   pip install -r requirements.txt

3. Configure credentials:
   - Set up OAuth or API keys for each service you intend to use.
   - Store credentials securely (e.g., environment variables or a .env file).

4. Run the MCP server:
   python server.py

---

## Requirements
See requirements.txt for the full list of dependencies.

---

## Notes
- Make sure to never commit API keys or credentials to version control.
- The .gitignore file is already configured to exclude common sensitive files.

---

## License
MIT License
