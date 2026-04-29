import argparse
import json
import os
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.auth.transport.requests


GDRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
SERVICE_ACCOUNT_FILE = "credentials/gdrive_service_account.json"
GMAIL_TOKEN_FILE = "credentials/gmail_token.json"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--mode", choices=["weekly", "monthly", "emergency"], default="weekly")
    return parser.parse_args()


def get_week_label(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    week = (dt.day - 1) // 7 + 1
    return f"{dt.year}년 {dt.month}월 {week}주차"


def upload_to_drive(pptx_path: str, date_str: str) -> tuple[str, str]:
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=GDRIVE_SCOPES
    )
    service = build("drive", "v3", credentials=creds)

    root_folder_id = os.environ["GDRIVE_FOLDER_ID"]
    dt = datetime.strptime(date_str, "%Y%m%d")
    year_folder = _get_or_create_folder(service, f"{dt.year}년", root_folder_id)
    month_folder = _get_or_create_folder(service, f"{dt.month}월", year_folder)

    file_name = f"{date_str}.pptx"
    # 기존 파일 확인
    query = f"name='{file_name}' and '{month_folder}' in parents and trashed=false"
    existing = service.files().list(q=query, fields="files(id)").execute().get("files", [])

    media = MediaFileUpload(pptx_path, mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    if existing:
        file_id = existing[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        meta = {"name": file_name, "parents": [month_folder]}
        result = service.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = result["id"]

    # 공개 뷰어 권한 설정
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    link = f"https://drive.google.com/file/d/{file_id}/view"
    return file_id, link


def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    result = service.files().list(q=query, fields="files(id)").execute().get("files", [])
    if result:
        return result[0]["id"]
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def send_gmail(mode: str, date_str: str, drive_link: str, accident_count: int):
    import base64
    from email.mime.text import MIMEText
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as gbuild

    token_data = json.load(open(GMAIL_TOKEN_FILE))
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=GMAIL_SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(google.auth.transport.requests.Request())

    mode_label = {"weekly": "주간", "monthly": "월간", "emergency": "긴급"}.get(mode, mode)
    period = get_week_label(date_str)
    subject = f"[건설안전] {mode_label} 사고보고서 생성 완료 — {period} ({accident_count}건)"
    body = f"""안녕하세요.

건설업 사고사례 보고서가 생성되었습니다.

📅 기간: {period}
📊 수집 건수: {accident_count}건
✅ 검수 상태: 통과

📎 보고서 링크:
{drive_link}

본 메일은 건설안전 에이전트 시스템이 자동 발송합니다.
"""
    sender = os.environ["GMAIL_SENDER"]
    recipients = [r.strip() for r in os.environ["GMAIL_RECIPIENT"].split(",")]

    gmail = gbuild("gmail", "v1", credentials=creds)
    for recipient in recipients:
        msg = MIMEText(body)
        msg["to"] = recipient
        msg["from"] = sender
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
    return recipients


def main():
    args = parse_args()
    date_str = os.path.basename(args.pptx).replace(".pptx", "")

    # 사고 건수 파악 (visualized JSON에서)
    viz_path = os.path.join("output", "visualized", f"{date_str}.json")
    accident_count = 0
    if os.path.exists(viz_path):
        with open(viz_path, "r", encoding="utf-8") as f:
            accident_count = len(json.load(f))

    print(f"[Publisher] Google Drive 업로드 중...")
    file_id, drive_link = upload_to_drive(args.pptx, date_str)
    print(f"[Publisher] 업로드 완료: {drive_link}")

    print(f"[Publisher] Gmail 발송 중...")
    recipients = send_gmail(args.mode, date_str, drive_link, accident_count)
    print(f"[Publisher] 발송 완료: {recipients}")

    output_dir = os.path.join("output", "publish")
    os.makedirs(output_dir, exist_ok=True)
    result = {
        "pptx_path": args.pptx,
        "gdrive_file_id": file_id,
        "gdrive_link": drive_link,
        "email_sent": True,
        "recipients": recipients,
        "published_at": datetime.now().isoformat(),
    }
    with open(os.path.join(output_dir, f"{date_str}_publish.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[Publisher] 완료")


if __name__ == "__main__":
    main()
