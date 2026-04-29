# Agent 2: 분류 (Classifier)

## 역할
원시 사고 데이터를 읽어 재해 유형 분류, 신뢰도 점수 산정, 목차 순서를 결정한다.
LLM이 유형 분류와 신뢰도 판단을 수행하고, 코드가 필드 유효성 검증을 담당한다.

## 입력
`output/raw/YYYYMMDD.json`

## 처리 규칙

### 재해 유형 분류 (LLM 판단)
`keyword`와 `contents` 필드를 보고 아래 유형 중 하나로 분류:

| 코드 | 유형 | 키워드 예시 |
|------|------|-----------|
| `fall` | 추락 | 추락, 떨어짐, 낙상 |
| `collapse` | 붕괴·도괴 | 붕괴, 무너짐, 도괴 |
| `falling_object` | 낙하물 | 낙하, 날림, 비래 |
| `electrocution` | 감전 | 감전, 전기, 누전 |
| `caught_in` | 끼임·협착 | 끼임, 협착, 말림 |
| `fire` | 화재·폭발 | 화재, 폭발, 발화 |
| `collision` | 충돌·접촉 | 충돌, 접촉, 부딪힘 |
| `other` | 기타 | 위에 해당 없음 |

### 신뢰도 점수 (LLM 판단)
- KOSHA 공식 데이터: 기본 80점 이상
- 필수 필드(날짜·장소·경위) 모두 있으면 +10
- 뉴스 단독 데이터: 기본 60점
- 60점 미만: `flagged: true` 처리

### 목차 순서 (코드 처리)
유형별로 그룹화 후 건수 내림차순으로 `toc_order` 번호 부여

## 출력 형식
`output/classified/YYYYMMDD.json` — 원시 데이터에 아래 필드 추가:

```json
{
  "type": "fall",
  "type_label": "추락",
  "confidence_score": 85,
  "flagged": false,
  "toc_order": 1
}
```

## 성공 기준
- 전체 항목에 `type`, `confidence_score`, `toc_order` 필드 존재
- 60점 미만 항목은 `flagged: true` 설정

## 프롬프트 가이드 (LLM 분류 시)
각 사고를 분류할 때 아래 형식으로 JSON만 출력:
```json
{"type": "fall", "type_label": "추락", "confidence_score": 85, "flagged": false}
```
설명 없이 JSON만 출력할 것. 판단 근거는 출력하지 않는다.
