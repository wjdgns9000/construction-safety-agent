"""
Gmail OAuth2 최초 인증 — 로컬에서 1회만 실행.
실행 후 credentials/gmail_token.json 이 생성됨.

사전 준비:
  1. Google Cloud Console → OAuth 2.0 클라이언트 ID (데스크톱 앱) 생성
  2. credentials/gmail_oauth_client.json 으로 저장
  3. python scripts/setup_gmail.py
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_FILE = "credentials/gmail_oauth_client.json"
TOKEN_FILE  = "credentials/gmail_token.json"

if not os.path.exists(CLIENT_FILE):
    print(f"[Error] {CLIENT_FILE} 파일이 없습니다.")
    print("Google Cloud Console에서 OAuth 클라이언트 ID(데스크톱 앱)를 다운로드하세요.")
    raise SystemExit(1)

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
creds = flow.run_local_server(port=0)

os.makedirs("credentials", exist_ok=True)
token_data = {
    "token":         creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri":     creds.token_uri,
    "client_id":     creds.client_id,
    "client_secret": creds.client_secret,
    "scopes":        list(creds.scopes),
}
with open(TOKEN_FILE, "w") as f:
    json.dump(token_data, f, indent=2)

print(f"[OK] Gmail 인증 완료: {TOKEN_FILE}")
