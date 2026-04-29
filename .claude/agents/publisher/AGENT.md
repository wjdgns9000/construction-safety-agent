# Agent 7: 배포 (Publisher)

## 역할
검수 완료된 .pptx 파일을 Google Drive에 업로드하고 Gmail로 완료 알림을 발송한다.

## 입력
- `output/pptx/YYYYMMDD.pptx`
- `output/qa/YYYYMMDD_report.json` (passed: true 확인 후에만 실행)

## 실행 명령
```bash
python scripts/publish.py --pptx output/pptx/YYYYMMDD.pptx --mode {weekly|monthly|emergency}
```

## 처리 순서

### 1. Google Drive 업로드
```
업로드 경로: 건설안전보고서/{YYYY년}/{MM월}/YYYYMMDD.pptx
폴더 없으면 자동 생성
기존 같은 날짜 파일 있으면 덮어쓰기 (같은 file_id 업데이트)
```

인증: `credentials/gdrive_service_account.json` (서비스 계정)
- 환경변수 `GDRIVE_FOLDER_ID` = 최상위 공유 폴더 ID

업로드 완료 후 공유 링크 생성:
- 권한: `anyone with the link` → `viewer`
- 링크 형식: `https://drive.google.com/file/d/{fileId}/view`

### 2. Gmail 알림 발송
인증: `credentials/gmail_token.json` (OAuth2, 최초 1회 로컬 인증 후 토큰 저장)
발신: 환경변수 `GMAIL_SENDER`
수신: 환경변수 `GMAIL_RECIPIENT` (쉼표 구분 다중 수신자 지원)

이메일 형식:
```
제목: [건설안전] 주간 사고보고서 생성 완료 — 2026년 4월 4주차 (N건)
본문:
  안녕하세요.

  건설업 사고사례 보고서가 생성되었습니다.

  📅 기간: YYYY년 MM월 W주차
  📊 수집 건수: N건
  ✅ 검수 상태: 통과

  📎 보고서 링크:
  https://drive.google.com/file/d/{fileId}/view

  본 메일은 건설안전 에이전트 시스템이 자동 발송합니다.
```

### 3. 로컬 임시 파일 정리
```bash
rm -rf output/raw/$DATE output/classified/$DATE output/analyzed/$DATE output/visualized/$DATE
# output/pptx/$DATE.pptx와 output/qa/$DATE_report.json은 30일 보관 후 삭제
```

## 환경변수 목록
```
GDRIVE_FOLDER_ID=<Google Drive 최상위 폴더 ID>
GMAIL_SENDER=your@gmail.com
GMAIL_RECIPIENT=recipient@gmail.com
```

## 출력 형식
`output/publish/YYYYMMDD_publish.json`

```json
{
  "pptx_path": "output/pptx/YYYYMMDD.pptx",
  "gdrive_file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE",
  "gdrive_link": "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE/view",
  "email_sent": true,
  "recipients": ["recipient@gmail.com"],
  "published_at": "2026-04-28T10:35:00"
}
```

## 성공 기준
- `gdrive_file_id` 존재 (업로드 완료)
- `email_sent: true`

## 실패 처리
- Drive 업로드 실패: 최대 3회 재시도 (10초 간격)
- Gmail 발송 실패: 최대 2회 재시도
- 모두 실패 시 오케스트레이터에 실패 신호 반환 (파이프라인은 이미 완료된 것으로 간주, 배포만 실패로 기록)
