#==============================================================================================
# DESCRIPTION : Gmail connector for FastMCP server.
#               Supports reading, sending, and searching emails.
#==============================================================================================

import os
import pickle
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# ─────────────────────────────────────────────────────────
# Absolute paths — same pattern as gdrive.py
# ─────────────────────────────────────────────────────────
MCP_DIR = os.getenv(
    "MCP_FILES_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

GCP_OAUTH_FILE    = os.path.join(MCP_DIR, "gcp-oauth-keys.json")   # ← same file as gdrive.py
GMAIL_TOKEN_FILE  = os.path.join(MCP_DIR, "gmail_token.pickle")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# ─────────────────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────────────────
def get_gmail_service():
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        with open(GMAIL_TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GCP_OAUTH_FILE):
                raise FileNotFoundError(f"gcp-oauth-keys.json not found at: {GCP_OAUTH_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(GCP_OAUTH_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return build('gmail', 'v1', credentials=creds)


# ─────────────────────────────────────────────────────────
# Run this file directly once to generate token
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔄 Generating Gmail token...")
    get_gmail_service()
    print("✅ Gmail token saved!")
    print("✅ Now run server.py")


# ─────────────────────────────────────────────────────────
# Register tools
# ─────────────────────────────────────────────────────────
def register_gmail_tools(mcp):

    @mcp.tool()
    def read_emails(max_results: int = 5) -> list:
        """Read latest emails from Gmail inbox"""
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me', labelIds=['INBOX'], maxResults=max_results
        ).execute()

        emails = []
        for msg in results.get('messages', []):
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender  = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date    = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

            body = ""
            payload = txt['payload']
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(
                            part['body']['data'] + '=='
                        ).decode('utf-8')
                        break
            elif 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(
                    payload['body']['data'] + '=='
                ).decode('utf-8')

            emails.append({
                'subject': subject,
                'from': sender,
                'date': date,
                'body': body[:500]
            })
        return emails


    @mcp.tool()
    def send_email(to: str, subject: str, body: str) -> dict:
        """Send an email via Gmail"""
        service = get_gmail_service()
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId='me', body={'raw': raw}
        ).execute()
        return {"status": "sent", "message_id": result['id']}


    @mcp.tool()
    def search_emails(query: str, max_results: int = 5) -> list:
        """Search Gmail by keyword, sender, subject, etc."""
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_results
        ).execute()

        emails = []
        for msg in results.get('messages', []):
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender  = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date    = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            emails.append({'subject': subject, 'from': sender, 'date': date})
        return emails