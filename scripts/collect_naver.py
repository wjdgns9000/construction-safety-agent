"""
Naver 뉴스 검색 API로 건설 사고 뉴스 수집.

API 키 발급: https://developers.naver.com/apps/#/register
  - 애플리케이션 등록 → 검색 API 선택
  - Client ID / Client Secret 발급 (무료, 하루 25,000건)

환경변수:
  NAVER_CLIENT_ID
  NAVER_CLIENT_SECRET
"""
import argparse
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests

API_URL = "https://openapi.naver.com/v1/search/news.json"
QUERIES = ["건설 추락 사고", "건설 붕괴 사고", "건설 감전 사고", "건설현장 안전사고"]
MAX_RETRIES = 3
RETRY_DELAY = 5


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["weekly", "monthly", "emergency"], default="weekly")
    parser.add_argument("--date", default=datetime.today().strftime("%Y%m%d"))
    return parser.parse_args()


def get_cutoff(mode: str, date_str: str) -> datetime:
    base = datetime.strptime(date_str, "%Y%m%d")
    if mode == "weekly":
        return base - timedelta(days=30)
    elif mode == "monthly":
        return base - timedelta(days=60)
    else:
        return base - timedelta(days=7)


def fetch_news(query: str, client_id: str, client_secret: str) -> list:
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": 100, "sort": "date"}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"[Naver] API 실패 ({query}): {e}")
                return []
    return []


def main():
    args = parse_args()
    client_id = os.environ.get("NAVER_CLIENT_ID", "")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("[Naver] API 키 없음 — 건너뜀 (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 미설정)")
        return

    output_dir = os.path.join("output", "raw")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{args.date}.json")
    cutoff = get_cutoff(args.mode, args.date)

    existing = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing_ids = {r["board_no"] for r in existing}

    new_items = []
    for query in QUERIES:
        items = fetch_news(query, client_id, client_secret)
        for item in items:
            try:
                pub_dt = parsedate_to_datetime(item.get("pubDate", "")).replace(tzinfo=None)
            except Exception:
                pub_dt = datetime.now()
            if pub_dt < cutoff:
                continue
            link = item.get("link") or item.get("originallink", "")
            board_no = f"NAVER_{uuid.uuid5(uuid.NAMESPACE_URL, link)}"
            if board_no in existing_ids:
                continue
            title = re.sub(r"<[^>]+>", "", item.get("title", ""))
            desc  = re.sub(r"<[^>]+>", "", item.get("description", ""))
            if not any(k in title + desc for k in ["건설", "공사", "현장", "작업자", "근로자"]):
                continue
            new_items.append({
                "board_no": board_no,
                "accident_date": pub_dt.strftime("%Y-%m-%d"),
                "location": "",
                "business": "건설업",
                "contents": desc,
                "keyword": title,
                "source": "NAVER_NEWS",
                "source_url": link,
                "collected_at": datetime.now().isoformat(),
            })
            existing_ids.add(board_no)

    merged = existing + new_items
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[Naver] 저장 완료: {output_path} (신규 {len(new_items)}건 추가, 총 {len(merged)}건)")


if __name__ == "__main__":
    main()
