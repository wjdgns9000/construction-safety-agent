import argparse
import json
import os
import time
import uuid
from datetime import datetime, timedelta

import requests

API_URL = "https://apis.data.go.kr/B552468/disaster_api02/getdisaster_api02"
API_KEY = os.environ.get("KOSHA_API_KEY", "4661693ceadc6fd88f4ad91bb7167f7088d7e1f2f219f80334298b5d9a2a2203")
MAX_RETRIES = 3
RETRY_DELAY = 5


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["weekly", "monthly", "emergency"], default="weekly")
    parser.add_argument("--date", default=datetime.today().strftime("%Y%m%d"))
    return parser.parse_args()


def get_date_range(mode: str, date_str: str):
    base = datetime.strptime(date_str, "%Y%m%d")
    if mode == "weekly":
        # KOSHA는 사고 발생 후 2~4주 뒤에 등록 → 30일 범위로 검색
        start = base - timedelta(days=30)
    elif mode == "monthly":
        start = base.replace(day=1) - timedelta(days=30)
    else:
        start = base - timedelta(days=7)
    return start.strftime("%Y%m%d"), base.strftime("%Y%m%d")


def fetch_page(start_date: str, end_date: str, page: int, size: int = 100):
    params = {
        "serviceKey": API_KEY,
        "pageNo": page,
        "numOfRows": size,
        "startDate": start_date,
        "endDate": end_date,
        "bizType": "건설업",
        "type": "json",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
            # KOSHA API returns EUC-KR; force UTF-8 interpretation first, fallback to euc-kr
            try:
                resp.encoding = "utf-8"
                data = resp.json()
            except (UnicodeDecodeError, json.JSONDecodeError):
                resp.encoding = "euc-kr"
                data = resp.json()
            return data
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"KOSHA API 호출 실패 ({MAX_RETRIES}회): {e}")


def collect(mode: str, date_str: str):
    start_date, end_date = get_date_range(mode, date_str)
    print(f"[KOSHA] 수집 기간: {start_date} ~ {end_date}")

    results = []
    page = 1
    while True:
        data = fetch_page(start_date, end_date, page)
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]
        if not items:
            break
        for item in items:
            # 건설업 필터 (API 필터가 부정확할 수 있으므로 재확인)
            biz = item.get("bizType", "") or item.get("BIZ_TYPE", "")
            if "건설" not in biz:
                continue
            results.append({
                "board_no": item.get("boardNo") or item.get("BOARD_NO") or str(uuid.uuid4()),
                "accident_date": item.get("accdntDt") or item.get("ACCDNT_DT", ""),
                "location": item.get("occrPlace") or item.get("OCCR_PLACE", ""),
                "business": "건설업",
                "contents": item.get("accdntDtlCn") or item.get("ACCDNT_DTL_CN", ""),
                "keyword": item.get("accdntNm") or item.get("ACCDNT_NM", ""),
                "source": "KOSHA",
                "source_url": f"https://www.kosha.or.kr/kosha/data/accidentCaseBoard.do?boardNo={item.get('boardNo', '')}",
                "collected_at": datetime.now().isoformat(),
            })
        total = (
            data.get("response", {})
            .get("body", {})
            .get("totalCount", 0)
        )
        if page * 100 >= int(total):
            break
        page += 1

    return results


def dedup(items: list, existing: list) -> list:
    existing_ids = {r["board_no"] for r in existing}
    return [r for r in items if r["board_no"] not in existing_ids]


def main():
    args = parse_args()
    output_dir = os.path.join("output", "raw")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{args.date}.json")

    existing = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

    new_items = collect(args.mode, args.date)
    merged = existing + dedup(new_items, existing)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    if not merged:
        print("[KOSHA] 수집 결과 0건 — Naver 수집으로 계속 진행")
    else:
        print(f"[KOSHA] 저장 완료: {output_path} ({len(merged)}건)")


if __name__ == "__main__":
    main()
