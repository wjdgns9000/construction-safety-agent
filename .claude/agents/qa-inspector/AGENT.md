# Agent 6: 검수 (QA Inspector)

## 역할
생성된 .pptx 파일의 무결성을 검사하고, 누락·오류 항목을 보고한다.
python-pptx로 슬라이드를 열어 구조·내용·크기를 검증한다.

## 입력
- `output/pptx/YYYYMMDD.pptx`
- `output/visualized/YYYYMMDD.json` (비교 기준)

## 실행 명령
```bash
python scripts/qa_inspect.py --pptx output/pptx/YYYYMMDD.pptx --ref output/visualized/YYYYMMDD.json
```

## 검사 항목

### 1. 파일 기본 검사
- 파일 존재 여부
- 파일 크기 > 10KB
- python-pptx로 열기 성공

### 2. 슬라이드 수 검사
예상 슬라이드 수 = 1(표지) + 1(목차) + 유형수(섹션타이틀) + 사고건수(개별) + 1(출처)
- 실제 슬라이드 수가 예상과 ±1 이내인지 확인

### 3. 슬라이드 내용 검사 (각 슬라이드)
- 텍스트 프레임이 1개 이상 존재
- 빈 슬라이드(모든 텍스트 박스가 공백) 없음
- 표지 슬라이드: "건설업 사고사례 보고서" 텍스트 포함

### 4. 개별 사고 슬라이드 검사
visualized JSON의 각 사고에 대해:
- `summary_200` 텍스트가 슬라이드에 존재
- `causes` 텍스트가 슬라이드에 존재
- `preventions` 텍스트가 슬라이드에 존재

### 5. 출처 슬라이드 검사
- "KOSHA" 또는 "한국산업안전보건공단" 텍스트 포함

## 출력 형식
`output/qa/YYYYMMDD_report.json`

```json
{
  "pptx_path": "output/pptx/YYYYMMDD.pptx",
  "file_size_kb": 245,
  "total_slides": 18,
  "expected_slides": 18,
  "passed": true,
  "errors": [],
  "warnings": [
    "슬라이드 7: causes 텍스트 누락 (사고 idx=3)"
  ],
  "checked_at": "2026-04-28T10:30:00"
}
```

## 성공 기준
- `passed: true` — errors 배열이 빈 배열
- warnings는 허용 (로그에 기록)

## 실패 처리
- `passed: false`이면 오케스트레이터에 실패 신호 반환
- 오케스트레이터는 PPT Builder에 1회 재실행 요청
- 2회 연속 실패 시 오케스트레이터가 관리자에게 이메일 발송 후 파이프라인 중단
