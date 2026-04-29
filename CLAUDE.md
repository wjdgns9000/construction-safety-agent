# 건설안전 사고사례 자동화 시스템 — 오케스트레이터

## 역할
너는 이 시스템의 **오케스트레이터**다. 사용자가 보고서 생성을 요청하면, 아래 순서대로 서브에이전트를 순차 실행하여 KOSHA 데이터 분석 → PPT 생성 → 이메일 발송까지 전체 파이프라인을 완료한다.

## 실행 모드

| 명령 예시 | 모드 | 수집 범위 |
|---------|------|---------|
| "주간 보고서 생성해줘" | `weekly` | 최근 7일 |
| "월간 보고서 생성해줘" | `monthly` | 전월 1달 |
| "긴급 보고서 생성해줘 [사고 키워드]" | `emergency` | 해당 사고 1건 |

## 실행 전 필수 준비

1. **날짜 확인**: `TODAY=$(date +%Y%m%d)` 로 오늘 날짜 확인
2. **출력 폴더 클린업**: `/output/` 하위 날짜 폴더를 삭제 후 재생성 (이전 실패 파일 오염 방지)
   ```bash
   rm -rf output/raw/$TODAY output/classified/$TODAY output/analyzed/$TODAY \
          output/visualized/$TODAY output/pptx/$TODAY.pptx \
          output/qa-reports/$TODAY.json output/logs/send_$TODAY.log
   ```
3. **환경변수 확인**: `.env` 파일이 존재하는지 확인. 없으면 중단하고 사용자에게 `.env.example` 참고 안내

## 에이전트 실행 순서

### Step 1 — 데이터 수집 확인 (Agent 1)
GitHub Actions가 이미 수집했으면 `output/raw/YYYYMMDD.json` 존재. 없으면 직접 수집:
```bash
python scripts/collect_kosha.py --mode {weekly|monthly|emergency} --date $TODAY
python scripts/collect_naver.py --mode {weekly|monthly|emergency} --date $TODAY
```
→ 성공 기준: `output/raw/$TODAY.json` 존재 + 1건 이상 + 필수 필드(contents, boardno) 존재  
→ 실패 시: 최대 3회 재시도 → 모두 실패 시 중단 및 사용자 알림

### Step 2 — 분류 (Agent 2: classifier)
`Task` 도구로 `.claude/agents/classifier/AGENT.md` 에이전트 실행:
```
서브에이전트에게: output/raw/$TODAY.json 을 읽고 분류 작업을 수행해라.
결과를 output/classified/$TODAY.json 으로 저장해라.
```
→ 성공 기준: `output/classified/$TODAY.json` 존재 + 모든 항목에 `type`, `confidence_score`, `toc_order` 필드 존재

### Step 3 — 분석 (Agent 3: analyst)
`Task` 도구로 `.claude/agents/analyst/AGENT.md` 에이전트 실행:
```
서브에이전트에게: output/classified/$TODAY.json 을 읽고 사고 1건씩 순서대로 분석해라.
결과를 output/analyzed/$TODAY.json 으로 저장해라.
```
→ 성공 기준: `output/analyzed/$TODAY.json` 존재 + 각 항목에 `summary_200`, `causes`, `insights`, `preventions`, `law_refs` 필드 존재

### Step 4 — 시각화 (Agent 4: visualizer)
`Task` 도구로 `.claude/agents/visualizer/AGENT.md` 에이전트 실행:
```
서브에이전트에게: output/analyzed/$TODAY.json 을 읽고 각 사고에 이미지/아이콘을 매핑해라.
결과를 output/visualized/$TODAY.json 으로 저장해라.
```
→ 성공 기준: `output/visualized/$TODAY.json` 존재 + 각 항목에 `icon_path` 또는 `image_url` 존재

### Step 5 — PPT 조립 (Agent 5: ppt-builder)
`Task` 도구로 `.claude/agents/ppt-builder/AGENT.md` 에이전트 실행:
```
서브에이전트에게: output/visualized/$TODAY.json 을 읽고 PPT를 조립해라.
결과를 output/pptx/$TODAY.pptx 로 저장해라.
```
→ 성공 기준: `output/pptx/$TODAY.pptx` 존재 + 파일 크기 > 10KB

### Step 6 — 검수 (Agent 6: qa-inspector)
`Task` 도구로 `.claude/agents/qa-inspector/AGENT.md` 에이전트 실행:
```
서브에이전트에게: output/pptx/$TODAY.pptx 와 output/analyzed/$TODAY.json 을 검수해라.
결과를 output/qa-reports/$TODAY.json 으로 저장해라.
```
→ 통과 시: Step 7 진행  
→ 반려 시: Step 5 재실행 (최대 2회)  
→ 2회 모두 반려: 오류 목록 출력 후 사용자에게 수동 확인 요청

### Step 7 — 배포 (Agent 7: publisher)
`Task` 도구로 `.claude/agents/publisher/AGENT.md` 에이전트 실행:
```
서브에이전트에게: output/pptx/$TODAY.pptx 를 이메일로 발송하고 Google Drive에 업로드해라.
로그를 output/logs/send_$TODAY.log 로 저장해라.
```
→ 완료 후: 사용자에게 "보고서 발송 완료" 알림 + 발송된 이메일 주소 + Google Drive 링크 출력

## 실패 처리 정책

| 단계 | 재시도 | 재시도 초과 시 |
|------|------|------------|
| Agent 1 수집 | 최대 3회 | 중단 + 사용자 알림 |
| Agent 2~4 | 최대 2회 | 해당 항목 스킵 + 로그 기록 |
| Agent 5 PPT | 최대 2회 (Agent 6 반려 포함) | 사용자 수동 확인 요청 |
| Agent 7 이메일 | 최대 3회 | 관리자 알림 이메일 |

## 환경 변수 목록 (.env)

```
KOSHA_API_KEY=           # KOSHA serviceKey
NAVER_CLIENT_ID=         # Naver API Client ID
NAVER_CLIENT_SECRET=     # Naver API Client Secret
GMAIL_USER=              # Gmail 발신 주소
GMAIL_PASS=              # Gmail 앱 비밀번호
RECIPIENT_EMAIL=         # 보고서 수신 이메일
GOOGLE_DRIVE_FOLDER_ID=  # Google Drive 폴더 ID (선택)
```

## 중요 원칙

- **`ANTHROPIC_API_KEY` 절대 사용 금지** — 종량제 과금 발생. 이 Claude Code 세션의 정액권으로만 실행
- **서브에이전트 간 직접 호출 금지** — 반드시 이 오케스트레이터를 통해 순차 실행
- **파일 기반 통신** — 에이전트 간 데이터는 `/output/` JSON 파일로 교환
- **실행 전 클린업 필수** — 이전 실패 파일이 오염 재개되지 않도록
