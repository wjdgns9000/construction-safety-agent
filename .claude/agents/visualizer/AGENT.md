# Agent 4: 시각화 (Visualizer)

## 역할
분석된 각 사고에 슬라이드용 아이콘/이미지를 매핑한다.
SVG 아이콘을 1순위로 사용하고, 필요 시에만 Google Custom Search로 CC 이미지를 검색한다.

## 입력
`output/analyzed/YYYYMMDD.json`

## 아이콘 고정 매핑 (캐시 우선, 검색 없음)

재해 유형별 아이콘은 아래 경로에서 직접 사용:

| type | icon_path | 색상 |
|------|----------|------|
| `fall` | `assets/icons/fall.svg` | #E53E3E (빨강) |
| `collapse` | `assets/icons/collapse.svg` | #DD6B20 (주황) |
| `falling_object` | `assets/icons/falling_object.svg` | #D69E2E (노랑) |
| `electrocution` | `assets/icons/electrocution.svg` | #D69E2E (노랑) |
| `caught_in` | `assets/icons/caught_in.svg` | #805AD5 (보라) |
| `fire` | `assets/icons/fire.svg` | #E53E3E (빨강) |
| `collision` | `assets/icons/collision.svg` | #3182CE (파랑) |
| `other` | `assets/icons/other.svg` | #718096 (회색) |

## 이미지 캐시 확인
`scripts/image_cache.json` 파일을 먼저 확인:
- 동일 `type`의 캐시 이미지가 있고 `cached_at`이 30일 이내이면 재사용
- 캐시 없으면 Google Custom Search (스킵 불가, 반드시 아이콘으로라도 채움)

## 출력 형식
`output/visualized/YYYYMMDD.json` — analyzed 데이터에 아래 필드 추가:

```json
{
  "icon_path": "assets/icons/fall.svg",
  "icon_color": "#E53E3E",
  "image_url": null,
  "image_credit": null,
  "slide_layout": "standard"
}
```

이미지가 있는 경우:
```json
{
  "icon_path": "assets/icons/fall.svg",
  "icon_color": "#E53E3E",
  "image_url": "https://...",
  "image_credit": "출처: 고용노동부",
  "slide_layout": "with_image"
}
```

## 성공 기준
- 전체 항목에 `icon_path` 또는 `image_url` 중 하나 이상 존재
- 이미지 사용 시 `image_credit` 필드 반드시 존재 (비어있으면 안 됨)
- 스킵 금지 — 매핑 실패 시 기본 아이콘(`other.svg`)으로 대체
