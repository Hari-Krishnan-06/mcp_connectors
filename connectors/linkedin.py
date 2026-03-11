#==============================================================================================
# DESCRIPTION : LinkedIn connector for FastMCP.
#               Auto-generates access token on first run if not found in .env,
#               then registers MCP tools for use with server.py.
#==============================================================================================

import os
import requests
import webbrowser
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from mcp.server.fastmcp import FastMCP

LINKEDIN_API  = "https://api.linkedin.com/v2"
LINKEDIN_OIDC = "https://api.linkedin.com/v2/userinfo"
REDIRECT_URI  = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
SCOPES        = "openid profile email w_member_social"  # 'email' scope enables email field
ENV_FILE      = Path(__file__).resolve().parents[1] / ".env"


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def get_headers():
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("❌ LINKEDIN_ACCESS_TOKEN is empty. Please re-run the OAuth flow.")
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _save_token_to_env(token: str):
    """Append or update LINKEDIN_ACCESS_TOKEN in the .env file."""
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith("LINKEDIN_ACCESS_TOKEN="):
                new_lines.append(f"LINKEDIN_ACCESS_TOKEN={token}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"LINKEDIN_ACCESS_TOKEN={token}")
        ENV_FILE.write_text("\n".join(new_lines) + "\n")
    else:
        with open(ENV_FILE, "a") as f:
            f.write(f"\nLINKEDIN_ACCESS_TOKEN={token}\n")

    os.environ["LINKEDIN_ACCESS_TOKEN"] = token
    print(f"✅ Token saved to {ENV_FILE} and loaded into environment.")


def _fetch_token_via_browser() -> str:
    """Open browser for OAuth, capture code via local /callback server, return access token."""
    client_id     = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "❌ LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env "
            "before running server.py for the first time."
        )

    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(SCOPES, safe='')}"
    )

    received_token = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)

            if parsed.path != "/callback":
                self.send_response(204)
                self.end_headers()
                return

            params = urllib.parse.parse_qs(parsed.query)

            if "error" in params:
                error       = params["error"][0]
                description = params.get("error_description", ["Unknown error"])[0]
                print(f"❌ LinkedIn OAuth error: {error} — {description}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(
                    f"<h2>OAuth Error: {error}</h2><p>{description}</p>".encode()
                )
                received_token["error"] = error
                return

            code = params.get("code", [None])[0]
            if not code:
                print("❌ No code received from LinkedIn.")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h2>Error: no authorization code received.</h2>")
                return

            print("🔄 Exchanging authorization code for access token...")
            r = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type":    "authorization_code",
                    "code":          code,
                    "redirect_uri":  REDIRECT_URI,
                    "client_id":     client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            resp_json = r.json()
            token = resp_json.get("access_token", "")

            if not token:
                error_msg = resp_json.get("error_description", str(resp_json))
                print(f"❌ Token exchange failed: {error_msg}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"<h2>Token exchange failed:</h2><p>{error_msg}</p>".encode())
                return

            received_token["value"] = token

            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<h2>&#x2705; LinkedIn connected!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
            )

        def log_message(self, *args):
            pass

    print("🌐 Opening LinkedIn login in your browser...")
    webbrowser.open(auth_url)
    print(f"⏳ Waiting for LinkedIn OAuth callback on {REDIRECT_URI} ...")

    server = HTTPServer(("localhost", 8000), Handler)
    while not received_token:
        server.handle_request()
    server.server_close()

    if "error" in received_token:
        raise RuntimeError(f"❌ LinkedIn OAuth was denied: {received_token['error']}")

    token = received_token.get("value", "")
    if not token:
        raise RuntimeError("❌ Failed to retrieve LinkedIn access token.")

    os.environ["LINKEDIN_ACCESS_TOKEN"] = token
    _save_token_to_env(token)
    print("🎉 LinkedIn token acquired and saved. Continuing server startup...\n")
    return token


def _ensure_token():
    """Check for token in env; if missing, trigger browser OAuth flow."""
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        print("\n⚠️  LINKEDIN_ACCESS_TOKEN not found in .env.")
        print("🔐 Starting one-time LinkedIn OAuth flow...\n")
        _fetch_token_via_browser()


# ─────────────────────────────────────────────────────────
# MCP TOOL REGISTRATION
# ─────────────────────────────────────────────────────────

def register_linkedin_tools(mcp: FastMCP):

    _ensure_token()

    def _get_profile_raw() -> dict:
        """Internal: fetch profile via OpenID Connect userinfo endpoint."""
        r = requests.get(LINKEDIN_OIDC, headers=get_headers())
        r.raise_for_status()
        return r.json()

    @mcp.tool()
    def get_linkedin_profile() -> dict:
        """Get your LinkedIn profile information."""
        data = _get_profile_raw()
        return {
            "id":             data.get("sub"),
            "first_name":     data.get("given_name"),
            "last_name":      data.get("family_name"),
            "name":           data.get("name"),
            "picture":        data.get("picture"),
            "email":          data.get("email"),           # ✅ ADDED: email address
            "email_verified": data.get("email_verified"),  # ✅ ADDED: email verification status
            "locale":         data.get("locale"),          # ✅ ADDED: language/region
        }

    @mcp.tool()
    def post_linkedin_update(text: str) -> dict:
        """Post a text update to your LinkedIn feed.

        Args:
            text: The content to post on LinkedIn (plain text)
        """
        profile = _get_profile_raw()
        person_urn = f"urn:li:person:{profile['sub']}"

        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }
        r = requests.post(f"{LINKEDIN_API}/ugcPosts", json=payload, headers=get_headers())
        r.raise_for_status()
        return {"status": "posted", "post_id": r.headers.get("x-restli-id")}

    @mcp.tool()
    def get_linkedin_profile_picture() -> dict:
        """Get your LinkedIn profile picture URL."""
        data = _get_profile_raw()
        return {
            "name":    data.get("name", ""),
            "picture": data.get("picture"),
        }