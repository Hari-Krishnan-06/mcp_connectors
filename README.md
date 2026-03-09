mcp_connectors
Overview
mcp_connectors is a Python-based MCP (Model Context Protocol) server that integrates multiple third-party service connectors into a unified interface. It enables seamless interaction with popular platforms like Google Drive, Gmail, GitHub, LinkedIn, and YouTube through a single server entry point.

Project Structure
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

Connectors

Google Drive – List, search, and fetch files
Gmail – Read, search, and send emails
GitHub – List repos, browse files, get commits
LinkedIn – Fetch profile details and post updates
YouTube – Search videos and get channel stats


Setup & Installation

Clone the repo and install dependencies via pip install -r requirements.txt
Configure OAuth/API keys for each service
Run the server with python server.py


License
MIT License
