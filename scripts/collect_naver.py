import argparse
import json
import os
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import requests

RSS_URL = "https://search.naver.com/rss.naver"
QUERIES = ["건설 추락 사고", "건설 붕괴 사고", "건설 감전 사고", "건설 안전사고"]
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
        return base - timedelta(days=7)
    elif mode == "monthly":
        return base.replace(day=1)
    else:
        return base - timedelta(days=1)


def fetch_rss(query: str) -> list:
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"query": query}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(RSS_URL, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"[Naver] RSS 실패 ({query}): {e}")
                return ""
    return ""


def parse_items(xml_text: str, cutoff: datetime) -> list:
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results = []
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        pubdate_el = item.find("pubDate")

        title = title_el.text if title_el is not None else ""
        link = link_el.text if link_el is not None else ""
        description = desc_el.text if desc_el is not None else ""
        pub_date_str = pubdate_el.text if pubdate_el is not None else ""

        # 날짜 파싱
        try:
            pub_dt = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
        except Exception:
            pub_dt = datetime.now()

        if pub_dt < cutoff:
            continue

        # HTML 태그 제거
        import re
        clean_title = re.sub(r"<[^>]+>", "", title or "")
        clean_desc = re.sub(r"<[^>]+>", "", description or "")

        # 건설 관련 키워드 필터
        text = clean_title + clean_desc
        if not any(k in text for k in ["건설", "공사", "현장", "작업자", "근로자"]):
            continue

        results.append({
            "board_no": f"NAVER_{uuid.uuid5(uuid.NAMESPACE_URL, link)}",
            "accident_date": pub_dt.strftime("%Y-%m-%d"),
            "location": "",
            "business": "건설업",
            "contents": clean_desc,
            "keyword": clean_title,
            "source": "NAVER_NEWS",
            "source_url": link,
            "collected_at": datetime.now().isoformat(),
        })
    return results


def main():
    args = parse_args()
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
        xml_text = fetch_rss(query)
        items = parse_items(xml_text, cutoff)
        for item in items:
            if item["board_no"] not in existing_ids:
                new_items.append(item)
                existing_ids.add(item["board_no"])

    merged = existing + new_items
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[Naver] 저장 완료: {output_path} (신규 {len(new_items)}건 추가, 총 {len(merged)}건)")


if __name__ == "__main__":
    main()
