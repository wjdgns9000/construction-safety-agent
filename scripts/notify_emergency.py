"""GitHub Actions 긴급 알림 — Gmail App Password 방식 (OAuth 불필요)"""
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from datetime import datetime


def main():
    raw_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if not raw_path or not os.path.exists(raw_path):
        print("[Notify] raw 파일 없음 — 알림 생략")
        return

    with open(raw_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        print("[Notify] 수집 0건 — 알림 생략")
        return

    sender   = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["GMAIL_RECIPIENT"]

    subject = f"[건설안전 긴급] 사고 데이터 {len(items)}건 수집 — 보고서 생성 필요"
    body = f"""긴급 사고 데이터가 수집되었습니다.

수집 건수: {len(items)}건
수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}
파일 경로: {raw_path}

보고서 생성 방법 (로컬에서 실행):
  claude --print "emergency 모드로 파이프라인 실행. 날짜: {os.path.basename(raw_path).replace('.json', '')}"

본 메일은 GitHub Actions 긴급 감시 워크플로우가 자동 발송합니다.
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

    print(f"[Notify] 긴급 알림 발송 완료 → {recipient}")


if __name__ == "__main__":
    main()
