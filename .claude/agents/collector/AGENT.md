# Agent 1: 수집 (Collector)

## 역할
KOSHA API와 Naver 뉴스 RSS에서 건설업 사고 데이터를 수집하고 중복을 제거하여 원시 JSON으로 저장한다.

## 실행 방법
오케스트레이터가 이 에이전트를 실행할 때 아래 스크립트를 호출한다:

```bash
python scripts/collect_kosha.py --mode {weekly|monthly|emergency} --date YYYYMMDD
python scripts/collect_naver.py --mode {weekly|monthly|emergency} --date YYYYMMDD
```

## 출력 형식
`output/raw/YYYYMMDD.json` — JSON Array

```json
[
  {
    "board_no": "20260413162017EK5XMP",
    "accident_date": "2026-01-00",
    "location": "경기도 하남시",
    "business": "건설업",
    "contents": "...",
    "keyword": "안전고리 설치작업 중 추락",
    "source": "KOSHA",
    "source_url": "https://...",
    "collected_at": "2026-04-28T08:00:00"
  }
]
```

## 성공 기준
- `output/raw/YYYYMMDD.json` 파일 존재
- 1건 이상 수집
- 각 항목에 `board_no`, `contents`, `keyword` 필드 존재

## 실패 처리
- API 호출 실패 시 최대 3회 재시도 (5초 간격)
- 3회 모두 실패 시 오케스트레이터에 실패 신호 반환
